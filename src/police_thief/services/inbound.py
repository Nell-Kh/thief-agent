"""Inbound side of a peer: the three tools an opponent may call.

The wire follows ADR-7 and the reference implementation: ``negotiate`` opens a
match by exchanging locked terms, ``receive_turn`` delivers one turn message
(commit hash, hint, scent - never a cleartext position), and ``submit_audit``
hands over the full disclosure at game end. Everything is validated before it
is stored: in a zero-trust game, a peer never acts on a message it has not
checked.

Turn de-duplication and reordering is a separate concern, delegated to
:class:`~.turn_reorder.TurnReorderBuffer`.
"""

from __future__ import annotations

from typing import Any

from ..domain.negotiation import TermsRejectedError, validate_terms
from ..domain.turnmsg import TurnMessage
from .turn_reorder import HandshakeRejectedError, TurnReorderBuffer

__all__ = ["SERIES_CONSENSUS", "HandshakeRejectedError", "InboundHandler"]

#: ``result_claim`` marking a ``submit_audit`` call as the end-of-series
#: settlement claim rather than a game disclosure (uoh-ay26 §"Final series
#: consensus extension"). It carries ``records: []`` and a ``consensus_sha``.
SERIES_CONSENSUS = "series_consensus"


class InboundHandler:
    """Receives, validates and queues the opponent's calls."""

    def __init__(
        self, our_terms: dict[str, Any], our_extras: dict[str, Any], expect_role: str, reorder_window: int = 2
    ) -> None:
        """Bind the handler to our signed terms, declarations and the rival role."""
        self._our_terms = our_terms
        self._our_extras = our_extras
        self._expect_role = expect_role
        self._reorder = TurnReorderBuffer(reorder_window)
        self.opponent_terms: dict[str, Any] | None = None
        self.audit: dict[str, Any] | None = None
        #: The opponent's end-of-series settlement claim, kept apart from
        #: ``audit`` so neither envelope can ever overwrite the other.
        self.consensus: dict[str, Any] | None = None
        self.controls: list[dict[str, Any]] = []

    @property
    def expect_role(self) -> str:
        """The only role whose messages this peer accepts."""
        return self._expect_role

    @property
    def declared_sub_game(self) -> int:
        """The sub-game number this handler's pairing declaration names.

        Series drivers swap one handler per sub-game; at the boundary they need
        to ask an already-installed handler which sub-game it belongs to, so an
        early greeting promoted into it is reused instead of overwritten.
        """
        return int(self._our_extras.get("sub_game_number", 0))

    @property
    def reorder_window(self) -> int:
        """How many steps ahead of the next-expected step may arrive early."""
        return self._reorder.reorder_window

    @property
    def next_step(self) -> int:
        """The step number this peer is still waiting for.

        Read-only, and delegated like every other view onto the reorder buffer.
        The series drivers name it when a turn wait times out, so the operator
        is told *which* step went missing rather than just that one did.
        """
        return self._reorder.next_step

    @property
    def turns(self) -> list[TurnMessage]:
        """Turn messages accepted and ready for processing, in step order."""
        return self._reorder.turns

    @property
    def commitments(self) -> dict[int, str]:
        """Every step's accepted commit hash, keyed by step number."""
        return self._reorder.commitments

    @property
    def final_commit(self) -> str | None:
        """The commit hash of the message that closed out the mini-game, if any."""
        return self._reorder.final_commit

    @property
    def opponent_games_played(self) -> int | None:
        """The opponent's declared counted-game total, once negotiated.

        None both before negotiation and when the peer declared nothing -
        per the kit, an omitted declaration is silence, never a refusal.
        """
        if self.opponent_terms is None:
            return None
        declared = self.opponent_terms.get("counted_games_played")
        return int(declared) if isinstance(declared, int) else None

    def negotiate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Accept the opponent's terms, refusing any lock mismatch.

        Raises:
            HandshakeRejectedError: on a contract, scent-model or role
                mismatch - different physics means the race must not start.
        """
        try:
            terms = validate_terms(
                payload,
                our_terms=self._our_terms,
                our_extras=self._our_extras,
                expect_role=self._expect_role,
            )
        except TermsRejectedError as error:
            raise HandshakeRejectedError(str(error)) from error
        self.opponent_terms = terms
        return {"accepted": True, "terms": self._our_terms, **self._our_extras}

    def receive_turn(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Accept one turn message; receiving it makes it our turn.

        A second commitment for the same step is refused - once sealed, a move
        cannot be replaced.
        """
        message = TurnMessage.from_wire(payload)
        if message.sender != self._expect_role:
            raise HandshakeRejectedError(
                f"expected a turn from {self._expect_role!r}, got {message.sender!r}"
            )
        return self._reorder.accept(message)

    def receive_control(self, message: dict[str, Any]) -> dict[str, Any]:
        """Queue an out-of-band control message (enable/status/restart/quit).

        Controls are signalling, not game state: they are stored for the
        runtime to read and always acknowledged - a refusal, if one is owed,
        travels back as our own control push, never as a return value.
        """
        if isinstance(message, dict):
            self.controls.append(message)
        return {"ok": True}

    def next_control(self) -> dict[str, Any] | None:
        """Pop the oldest unread control message, if any."""
        if not self.controls:
            return None
        return self.controls.pop(0)

    def submit_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Accept the opponent's end-of-game disclosure for the mutual audit.

        ``submit_audit`` carries two different envelopes on the uoh-ay26 wire:
        the game disclosure, and the end-of-series ``series_consensus`` claim,
        which is defined to carry ``records: []`` and a ``consensus_sha``. They
        are told apart HERE rather than downstream, because the consensus
        envelope used to satisfy every check above and then land on
        ``self.audit`` - silently replacing a real, verified game disclosure
        with an empty record set, so the mutual audit had nothing left to
        verify and a settled sub-game turned into an unexplained failure.
        """
        if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
            raise HandshakeRejectedError("audit payload must carry a list of records")
        if payload.get("sender") != self._expect_role:
            raise HandshakeRejectedError(
                f"expected an audit from {self._expect_role!r}"
            )
        if payload.get("result_claim") == SERIES_CONSENSUS:
            # Their own rule, mirrored: "a consensus envelope containing game
            # records is malformed." Refusing it is how they learn we disagree
            # while there is still someone to tell.
            if payload.get("records"):
                raise HandshakeRejectedError(
                    "a series_consensus envelope must carry records: []"
                )
            self.consensus = payload
            return {"ok": True, "result_claim": SERIES_CONSENSUS,
                    "consensus_sha": str(payload.get("consensus_sha", ""))}
        self.audit = payload
        return {"ok": True, "records": len(payload.get("records", []))}

    def next_turn(self) -> TurnMessage | None:
        """Pop the oldest unprocessed turn message, if any."""
        return self._reorder.pop()
