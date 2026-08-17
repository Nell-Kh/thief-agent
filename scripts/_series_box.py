"""The one inbound handler our single door presents, and how it changes hands.

Split from ``_series_lib`` under the 150-code-line rule, along the seam the
code already had: everything here is about WHICH sub-game an arriving message
belongs to, and nothing here knows how a turn is played or a series scored.

We expose ONE endpoint and alternate roles inside it, while several opponents
run one fixed-role process per role against that endpoint. Every hard bug in
this file comes from that asymmetry: their two processes do not agree with each
other about which sub-game is current, so ours must be the side that sorts it
out - patiently, without ever accepting a message into the wrong game.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastmcp.exceptions import ToolError  # noqa: E402

from police_thief.services.inbound import InboundHandler  # noqa: E402
from police_thief.services.turn_reorder import HandshakeRejectedError  # noqa: E402


class SwappableHandler:
    """Holds the :class:`InboundHandler` currently active; the tools delegate to it.

    One process serves every sub-game's worth of negotiate/receive_turn/
    submit_audit/receive_control calls; the *object* backing those calls is
    replaced at each sub-game boundary, exactly as the kit's own driver swaps in
    a fresh peer. Duck-types the four methods :func:`build_server` binds.
    """

    def __init__(self) -> None:
        """Start with no handler bound; the first sub-game installs one."""
        self.current: InboundHandler | None = None
        self.pending: InboundHandler | None = None
        #: The handler PROMOTION displaced. A sub-game is not over when the
        #: opponent greets the next one: our disclosure has gone out, but
        #: THEIRS has not arrived, and it is addressed to the sub-game that
        #: just ended. Dropping the old handler at promotion routes that audit
        #: to a handler expecting the opposite role, which refuses it
        #: ("expected an audit from 'police'") - and the sub-game we had
        #: already WON dies waiting for evidence that was delivered and thrown
        #: away. nis-yar1, 2026-08-17, sub-game 1: captured at step 4, then
        #: lost to our own bookkeeping.
        self.previous: InboundHandler | None = None
        #: The opponent's OWN counted-game declaration, read off its greeting.
        #: Rule #38 disqualifies the group that made a false declaration, so a
        #: number we invent for them is a declaration we are not entitled to
        #: make; this is theirs, from a message they signed.
        self.opponent_games_played: int | None = None

    def _active(self) -> InboundHandler:
        """The bound handler, or a clean retryable refusal while none is.

        An opponent that boots faster than us can greet in the window between
        our server binding and the first sub-game installing its handler.
        Crashing that call with ``AttributeError`` reads as a broken peer and
        burned a real kit-sparring run; a named not-ready error reads as
        "try again", which every driver's patient-negotiation loop already does.
        """
        if self.current is None:
            raise ToolError("peer is booting - no sub-game handler bound yet, retry")
        return self.current

    def negotiate(self, message: dict[str, Any]) -> dict[str, Any]:
        """Forward a handshake; promote the pending handler on a boundary race.

        A fast opponent greets sub-game n+1 the instant its audit of n is
        posted, while this side is still writing artifacts - the old handler
        then refuses with a sub-game mismatch, and the kit's driver treats a
        refusal as fatal (correctly: no amount of waiting fixes a mismatch).
        When the next sub-game's handler is already staged in ``pending``, the
        mismatch IS the signal to promote it and answer as the new sub-game.

        With nothing staged, a greeting for a LATER sub-game is not a refusal
        at all - it is a peer that is early, and the honest answer is "not
        yet", which is retryable. najamjad (2026-08-16) run one process per
        role against our single door, so their cop opened sub-game 2 while
        their thief was still opening sub-game 1: a permanent refusal there
        kills a series over a race that resolves itself in seconds. A greeting
        for an EARLIER sub-game still refuses - that one really is unplayable,
        because the sub-game it names is already sealed and reported.

        The "not yet" is raised as FastMCP's ``ToolError``: it reaches the peer
        as the same retryable failure a bare exception would, but FastMCP
        treats it as an EXPECTED, client-facing error and does not dump a
        server-side traceback for it. Against a role-split opponent whose idle
        process polls us continuously, the traceback was the actual damage -
        hundreds of stack dumps buried three won sub-games in the operator's
        log (najamjad, 2026-08-16).

        Promotion is CONDITIONAL on ``pending`` naming the sub-game the
        greeting actually asks for. It used to fire on any staged handler at
        all - and a stale one (staged for sub-game n, then never consumed
        because the opponent arrived late and ``play_sub_game`` built its own)
        would then be swapped in for a LIVE handler mid-match. najamjad's thief
        greeted sub-game 3 during our sub-game 2 (2026-08-16); that promotion
        replaced the handler holding sub-game 2's turn buffer and killed a game
        that was otherwise being played correctly.
        """
        try:
            return self._active().negotiate(message)
        except HandshakeRejectedError:
            wanted = message.get("sub_game_number")
            pending = self.pending
            if pending is not None and (
                not isinstance(wanted, int) or pending.declared_sub_game == wanted
            ):
                self.previous, self.current, self.pending = (
                    self.current, pending, None)
                return self.current.negotiate(message)
            here = self._active().declared_sub_game
            if isinstance(wanted, int) and wanted > here:
                raise ToolError(
                    f"sub-game {wanted} has not started on this peer yet (we are "
                    f"playing {here}) - retry when it does"
                ) from None
            raise

    def _or_previous(self, call: str, argument: dict[str, Any]) -> dict[str, Any]:
        """Deliver to the active handler, falling back to the displaced one.

        Promotion moves ``current`` forward the moment the opponent greets the
        next sub-game - but the sub-game just ended is still owed ONE message:
        the opponent's audit disclosure. A role-split opponent sends it from
        its other process, so it can easily arrive after the greeting that
        promoted us, and the new handler refuses it on the sender's role.

        Refusing it is correct for the new sub-game and catastrophic for the
        old one, so try the displaced handler before giving up. Nothing is
        accepted loosely: both handlers still enforce their own role and shape,
        so a genuinely wrong message is refused by both and the error stands.
        """
        try:
            return getattr(self._active(), call)(argument)
        except HandshakeRejectedError:
            if self.previous is None:
                raise
            return getattr(self.previous, call)(argument)

    def receive_turn(self, message: dict[str, Any]) -> dict[str, Any]:
        """Forward a turn to the active handler, or the one it displaced."""
        return self._or_previous("receive_turn", message)

    def submit_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Forward an audit disclosure to the active handler, or its predecessor."""
        return self._or_previous("submit_audit", payload)

    def receive_control(self, message: dict[str, Any]) -> dict[str, Any]:
        """Forward a control message to the active handler."""
        return self._active().receive_control(message)

