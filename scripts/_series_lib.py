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

from _series_box import SwappableHandler  # noqa: E402,F401

from police_thief.constants import ROLE_POLICE, ROLE_THIEF  # noqa: E402
from police_thief.infra.email.report_blocks import now_iso, opponent_commit  # noqa: E402,F401
from police_thief.infra.mcp_client import PeerUnreachableError  # noqa: E402
from police_thief.infra.mcp_server import build_server  # noqa: E402
from police_thief.services.inbound import InboundHandler  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402
from police_thief.services.turn_reorder import HandshakeRejectedError  # noqa: E402,F401

#: Hard stop on a sub-game's turn exchange, so a wedged peer can never hang us.
SAFETY_CAP = 200

#: Fallback wait for an opponent's turn, used only when the config declares no
#: ``turn_timeout_seconds``. **Never hardcode this shorter than the deadline we
#: ourselves declare.** It was 60.0, while ``config/police/game.toml`` declares
#: ``turn_timeout_seconds = 180`` - so our driver abandoned a sub-game after 60
#: seconds against a peer that was still inside the budget BOTH sides had
#: signed. nis-yar1 (2026-08-17) stated a 180-second deadline in writing, their
#: thief did not deliver its opening turn inside 60, and we scored a technical
#: loss against an opponent doing nothing wrong - then spent the rest of the
#: series refusing their greetings, because they were still playing sub-game 1
#: while we had moved to 2. A timeout shorter than the declared one does not
#: protect us; it manufactures the failure it is meant to survive.
TURN_WAIT_TIMEOUT = 180.0
NEGOTIATE_WAIT_TIMEOUT = 180.0
POLL_INTERVAL = 0.2

#: How long to keep re-offering terms to an opponent that has not started yet.
#: Matches ``services.peer_boot.DEFAULT_WAIT_SECONDS``: two teams start their
#: processes by hand, minutes apart, and neither should have to go first.
OPENING_WAIT_SECONDS = 120.0

#: Floor on the patience for an opponent's FIRST turn/greeting/audit across a
#: sequential g0N->g0(N+1) boundary, INDEPENDENT of ``--wait``. A one-driver
#: opponent answers our negotiate the instant its endpoint is up, but its first
#: real turn can be a whole opposite-role sub-game away while its driver crosses
#: the boundary. uoh-ay26 (G010) declared a 1200s boundary window on their side
#: for exactly this; if we wait less we time out a peer doing nothing wrong and
#: turn a compliant handoff into a technical loss. This was the g03 hang on
#: 2026-08-22: ``greeting_wait`` was ``max(180, --wait)``, ``--wait`` defaulted
#: to ``OPENING_WAIT_SECONDS`` (120), so the first-turn window collapsed to 180s
#: while their driver was still legitimately on g02. Coupling boundary patience
#: to ``--wait`` was the bug - ``--wait`` governs a different thing (re-offering
#: terms before kickoff). A generous ceiling is safe: a peer that is genuinely
#: gone still becomes a contained technical loss, only later.
FIRST_TURN_BOUNDARY_SECONDS = 1200.0

#: How often a long boundary wait prints a still-alive line, so an operator does
#: not mistake a healthy 1200s wait for a hang and kill it (2026-08-22: the wait
#: was silent but for incidental HTTP logs, and was interrupted by hand twice).
WAIT_HEARTBEAT_SECONDS = 30.0

#: How long a turn or audit delivery keeps retrying a peer that has gone quiet,
#: on top of the contract's three tries. Sized against the opponent's own
#: ``TURN_WAIT_TIMEOUT``: long enough to ride out a tunnel reconnecting, short
#: enough that our message still lands before THEY declare us timed out.
TURN_PATIENCE_SECONDS = 40.0

#: What :func:`spoken_refusal` reports when a peer says no and names no cause.
#: Named because :func:`negotiate_patiently` has to tell that answer apart from
#: a stated one, and matching the literal in two files is how they drift apart.
NO_REASON_GIVEN = "no reason given"

#: Pause between re-offers in :func:`negotiate_patiently`. The silence branch
#: used to `continue` with no pause at all: it was paced only by the ~10-15s
#: :class:`PeerClient` spends on its own backoff before raising, so a transport
#: that failed fast would have spun the CPU flat (measured: 7.2M calls in 3s
#: against an instant-failing stub). A refusal returns immediately and has no
#: such accidental pacing, so the pause is what makes re-offering affordable.
REOFFER_PAUSE_SECONDS = 2.0


def other_role(role: str) -> str:
    """The role the opponent plays when we play ``role``."""
    return ROLE_THIEF if role == ROLE_POLICE else ROLE_POLICE


def git_head() -> str:
    """This working tree's HEAD commit, or ``"uncommitted"`` when unavailable."""
    out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                         check=False, cwd=ROOT)
    return out.stdout.strip() or "uncommitted"



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
                        announce: Callable[[str], None] = lambda _message: None,
                        sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """Offer terms, re-offering while the opponent is merely not ready yet.

    :meth:`PeerClient.negotiate` carries the contract's *in-match* budget - three
    tries, five seconds apart - because a silence mid-game must become a
    technical loss quickly. That is the wrong clock for the opening handshake:
    the two peers are launched by two people who cannot start on the same
    second, and the driver used to die outright if the opponent was more than
    ~15s late. Note the asymmetry it left behind - we then waited a patient 180s
    for *their* greeting while giving our own call 15s.

    A refusal that NAMES a cause is not a silence: it propagates at once,
    because no amount of waiting fixes a digest mismatch (sharNamr, 2026-08-15,
    is why a spoken no is believed at all).

    A refusal that names NOTHING is a different animal, and telling the two
    apart is the whole point of this function. We answer an early greeting with
    "not started on this peer yet - retry when it does" and expect the opponent
    to wait; najamjad's peers answer ours with a bare ``{"ok": false}`` and we
    used to quit on the first one. That asymmetry cost sub-games 4, 5 and 6 on
    2026-08-16 - three technical losses taken in 0.00s each, with 120 seconds of
    patience sitting unused, against peers that were merely mid-sub-game on the
    other role. A peer with a real objection says what it is; a bare no is the
    same "not yet" we ourselves send, spoken in a different dialect. So it is
    re-offered until the budget runs out, and only then does it become the
    technical loss it would have been immediately.

    The budget is a ceiling on waiting, never on the verdict: a peer refusing
    for a real reason still fails here, one call in.
    """
    deadline = clock() + wait_seconds
    announced: set[str] = set()

    def once(note: str) -> None:
        """Say something to the operator the first time it becomes true."""
        if note not in announced:
            announce(note)
            announced.add(note)

    while True:
        try:
            reply = client.negotiate(greeting)
        except PeerUnreachableError:
            if clock() >= deadline:
                raise
            once("opponent not up yet - waiting for it to start...")
            sleep(REOFFER_PAUSE_SECONDS)
            continue
        refusal = spoken_refusal(reply)
        if not refusal:
            return reply
        if refusal != NO_REASON_GIVEN or clock() >= deadline:
            raise HandshakeRejectedError(f"opponent refused our greeting: {refusal}")
        once("opponent said no without a reason - treating it as 'not yet' and re-offering...")
        sleep(REOFFER_PAUSE_SECONDS)


def spoken_refusal(reply: Any) -> str:
    """The opponent's stated refusal inside a negotiate reply, or ``""``.

    On the kit wire ``negotiate`` is a mailbox - the reply is ``{"ok": true}``
    (queued) and any refusal is decided later, in silence. But a peer MAY speak
    its verdict in the reply (``accepted: false``, ``ok: false``, ``refused``,
    ``error``), and a client that ignores that plays a whole sub-game against
    nothing (sharNamr, 2026-08-15). A spoken no is a refusal, never a success.

    A bare no reports :data:`NO_REASON_GIVEN`, which :func:`negotiate_patiently`
    reads as "not yet" rather than "never" - so the sentinel is load-bearing,
    not a display string. Everything here still classifies; what to DO about a
    reasonless no is that function's decision, not this one's.
    """
    if not isinstance(reply, dict):
        return ""
    if reply.get("accepted") is False or reply.get("ok") is False:
        return str(
            reply.get("reason") or reply.get("error")
            or reply.get("refused") or NO_REASON_GIVEN
        )
    for key in ("refused", "error"):
        if reply.get(key):
            return str(reply[key])
    return ""


def wait_for(predicate: Callable[[], Any], timeout: float, what: str,
             announce: Callable[[str], None] | None = None,
             heartbeat: float = WAIT_HEARTBEAT_SECONDS) -> Any:
    """Poll ``predicate`` until it returns non-None, or raise ``TimeoutError``.

    ``announce`` (when given) prints a still-waiting line every ``heartbeat``
    seconds. A boundary wait can legitimately run for many minutes while a
    sequential opponent finishes the other role's sub-game, and a silent poll
    is indistinguishable from a wedged process - so an operator watching a bare
    prompt reasonably kills it, which is exactly how the g03 wait died by hand
    on 2026-08-22. The heartbeat makes "still waiting, on purpose" visible.
    """
    start = time.monotonic()
    deadline = start + timeout
    next_beat = start + heartbeat
    while True:
        now = time.monotonic()
        if now >= deadline:
            break
        value = predicate()
        if value is not None:
            return value
        if announce is not None and now >= next_beat:
            announce(f"  still waiting for {what} - {now - start:.0f}s / {timeout:.0f}s "
                     f"(a sequential peer's boundary crossing can take this long)")
            next_beat = now + heartbeat
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"timed out after {timeout}s waiting for {what}")


def play_networked(role: str, matchrt: MatchRuntime, client, handler: InboundHandler,
                   turn_wait: float = TURN_WAIT_TIMEOUT,
                   first_turn_wait: float | None = None,
                   announce: Callable[[str], None] | None = None) -> None:
    """Alternate turns with a real remote opponent - the thief always moves first.

    ``turn_wait`` is how long we allow the opponent for one turn. It belongs to
    the CONTRACT, not to this file: a peer is entitled to every second of the
    deadline both sides declared, and a driver that gives up sooner turns a
    compliant opponent into a technical loss and then desynchronises the whole
    series behind it.

    ``first_turn_wait`` is the patience for the opponent's FIRST turn only, and
    exists for a peer whose one sequential driver plays g01..g06 in order: it
    answers our negotiate (its endpoint is up) before its driver has reached
    this sub-game, so its first turn can be many contract-turns away while it
    finishes the other role's game. G010 g03 took a technical_loss on exactly
    this - negotiated fine, then the fixed 180s first-turn deadline expired
    while their driver was still on g02. Every turn AFTER the first keeps the
    real ``turn_wait``, so a genuine mid-game stall still fails fast. Defaults
    to ``turn_wait`` when unset.
    """
    thief_is_us = role == ROLE_THIEF
    pending = first_turn_wait or turn_wait
    for _ in range(SAFETY_CAP):
        if matchrt.ended:
            return
        if thief_is_us:
            client.send_turn(matchrt.play_turn().to_wire())
            if matchrt.ended:
                return
        incoming = wait_for(handler.next_turn, pending,
                            f"opponent's turn (sub-game {matchrt.book.sub_game}, "
                            f"step {handler.next_step})",
                            announce=announce)
        pending = turn_wait
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


def peer_repos(raw: str) -> dict[str, str]:
    """Parse ``cop=URL,thief=URL`` into the report's github sub-block.

    Rulebook 9.3.3 lists both teams' repository links among the mandatory
    fields, but a report can only carry what the opponent declared - and no
    peer we have met declares them on the wire. Recording what they sent us in
    writing is the difference between a complete report and one missing a
    required field; an empty argument keeps the old empty mapping.
    """
    pairs = [chunk.split("=", 1) for chunk in raw.split(",") if "=" in chunk]
    return {key.strip(): value.strip() for key, value in pairs if value.strip()}


def inclusive_games(declared: int | None, counted: bool) -> int | None:
    """An opponent's pre-series declaration, advanced to include this series.

    A peer declares ``counted_games_played`` as the games it has ALREADY had
    counted; the report's field is ``games_played_including_this``. Filing
    the declaration raw made ours say ``0`` for an opponent whose own report
    says ``1`` for the same counted series - outside the consensus hash, so
    harmless to settlement, but two filings that should agree did not.
    ``None`` (they declared nothing) stays ``None``: no invented number.
    """
    if declared is None:
        return None
    return int(declared) + (1 if counted else 0)
