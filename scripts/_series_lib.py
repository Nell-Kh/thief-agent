"""Shared machinery for the networked series drivers.

Both :mod:`friendly_series` (any real opponent) and :mod:`sparring_series` (the
class interop kit's sparring peer) drive the same protocol: serve one long-lived
FastMCP server, swap in a fresh :class:`InboundHandler` at every sub-game
boundary as the role alternates, alternate real ``receive_turn`` calls with the
opponent, then exchange audit disclosures. That machinery lives here once so the
two drivers differ only in the parts that are genuinely different - who the
opponent is, and which artifacts get written.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from police_thief.constants import ROLE_POLICE, ROLE_THIEF  # noqa: E402
from police_thief.infra.mcp_client import PeerUnreachableError  # noqa: E402
from police_thief.infra.mcp_server import build_server  # noqa: E402
from police_thief.services.inbound import InboundHandler  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402
from police_thief.services.turn_reorder import HandshakeRejectedError  # noqa: E402

#: Hard stop on a sub-game's turn exchange, so a wedged peer can never hang us.
SAFETY_CAP = 200
TURN_WAIT_TIMEOUT = 60.0
NEGOTIATE_WAIT_TIMEOUT = 180.0
POLL_INTERVAL = 0.2

#: How long to keep re-offering terms to an opponent that has not started yet.
#: Matches ``services.peer_boot.DEFAULT_WAIT_SECONDS``: two teams start their
#: processes by hand, minutes apart, and neither should have to go first.
OPENING_WAIT_SECONDS = 120.0

#: How long a turn or audit delivery keeps retrying a peer that has gone quiet,
#: on top of the contract's three tries. Sized against the opponent's own
#: ``TURN_WAIT_TIMEOUT``: long enough to ride out a tunnel reconnecting, short
#: enough that our message still lands before THEY declare us timed out.
TURN_PATIENCE_SECONDS = 40.0


def other_role(role: str) -> str:
    """The role the opponent plays when we play ``role``."""
    return ROLE_THIEF if role == ROLE_POLICE else ROLE_POLICE


def git_head() -> str:
    """This working tree's HEAD commit, or ``"uncommitted"`` when unavailable."""
    out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                         check=False, cwd=ROOT)
    return out.stdout.strip() or "uncommitted"


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

    def _active(self) -> InboundHandler:
        """The bound handler, or a clean retryable refusal while none is.

        An opponent that boots faster than us can greet in the window between
        our server binding and the first sub-game installing its handler.
        Crashing that call with ``AttributeError`` reads as a broken peer and
        burned a real kit-sparring run; a named not-ready error reads as
        "try again", which every driver's patient-negotiation loop already does.
        """
        if self.current is None:
            raise RuntimeError("peer is booting - no sub-game handler bound yet, retry")
        return self.current

    def negotiate(self, message: dict[str, Any]) -> dict[str, Any]:
        """Forward a handshake; promote the pending handler on a boundary race.

        A fast opponent greets sub-game n+1 the instant its audit of n is
        posted, while this side is still writing artifacts - the old handler
        then refuses with a sub-game mismatch, and the kit's driver treats a
        refusal as fatal (correctly: no amount of waiting fixes a mismatch).
        When the next sub-game's handler is already staged in ``pending``, the
        mismatch IS the signal to promote it and answer as the new sub-game.
        """
        try:
            return self._active().negotiate(message)
        except HandshakeRejectedError:
            if self.pending is None:
                raise
            self.current, self.pending = self.pending, None
            return self.current.negotiate(message)

    def receive_turn(self, message: dict[str, Any]) -> dict[str, Any]:
        """Forward a turn to the active handler."""
        return self._active().receive_turn(message)

    def submit_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Forward an audit disclosure to the active handler."""
        return self._active().submit_audit(payload)

    def receive_control(self, message: dict[str, Any]) -> dict[str, Any]:
        """Forward a control message to the active handler."""
        return self._active().receive_control(message)


def start_server(handler_box: SwappableHandler, port: int,
                 host: str = "127.0.0.1") -> threading.Thread:
    """Run our MCP server in a daemon thread on ``host:port``.

    ``127.0.0.1`` is right when a tunnel agent runs on this machine (it dials
    localhost itself); pass ``0.0.0.0`` to accept a direct remote connection.
    """
    server = build_server(handler_box)
    thread = threading.Thread(
        target=lambda: server.run(transport="http", host=host, port=port, show_banner=False),
        daemon=True,
    )
    thread.start()
    return thread


def negotiate_patiently(client, greeting: dict[str, Any],
                        wait_seconds: float = OPENING_WAIT_SECONDS,
                        clock: Callable[[], float] = time.monotonic,
                        announce: Callable[[str], None] = lambda _message: None) -> dict[str, Any]:
    """Offer terms, re-offering while the opponent is merely not up yet.

    :meth:`PeerClient.negotiate` carries the contract's *in-match* budget - three
    tries, five seconds apart - because a silence mid-game must become a
    technical loss quickly. That is the wrong clock for the opening handshake:
    the two peers are launched by two people who cannot start on the same
    second, and the driver used to die outright if the opponent was more than
    ~15s late. Note the asymmetry it left behind - we then waited a patient 180s
    for *their* greeting while giving our own call 15s.

    A refusal (contract or lock mismatch) is not a silence: it propagates at
    once, because no amount of waiting fixes a digest mismatch.
    """
    deadline = clock() + wait_seconds
    waited = False
    while True:
        try:
            return client.negotiate(greeting)
        except PeerUnreachableError:
            if clock() >= deadline:
                raise
            if not waited:
                announce("opponent not up yet - waiting for it to start...")
                waited = True


def wait_for(predicate: Callable[[], Any], timeout: float, what: str) -> Any:
    """Poll ``predicate`` until it returns non-None, or raise ``TimeoutError``."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value is not None:
            return value
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"timed out after {timeout}s waiting for {what}")


def play_networked(role: str, matchrt: MatchRuntime, client, handler: InboundHandler) -> None:
    """Alternate turns with a real remote opponent - the thief always moves first."""
    thief_is_us = role == ROLE_THIEF
    for _ in range(SAFETY_CAP):
        if matchrt.ended:
            return
        if thief_is_us:
            client.send_turn(matchrt.play_turn().to_wire())
            if matchrt.ended:
                return
        incoming = wait_for(handler.next_turn, TURN_WAIT_TIMEOUT,
                            f"opponent's turn (sub-game {matchrt.book.sub_game}, "
                            f"step {handler.next_step})")
        reply = matchrt.on_turn(incoming)
        if reply is not None:
            client.send_turn(reply.to_wire())
        if matchrt.ended:
            return
        if not thief_is_us:
            client.send_turn(matchrt.play_turn().to_wire())
    raise RuntimeError(f"sub-game {matchrt.book.sub_game}: safety cap ({SAFETY_CAP}) exceeded")


def score_for(contract, outcome_type: str, role: str) -> int:
    """Points ``role`` earns for ``outcome_type`` under the contract's table."""
    scoring = contract.scoring
    if outcome_type == "capture":
        return scoring.capture_cop if role == ROLE_POLICE else scoring.capture_thief
    if outcome_type == "survival":
        return scoring.survival_thief if role == ROLE_THIEF else scoring.survival_cop
    return scoring.technical_loss
