"""Fault containment for a networked series: one bad sub-game never zeroes the rest.

League series run between two students' laptops over public tunnels (ngrok,
Localtonet), so a mid-game silence, a timed-out turn, an equivocation, or an
unreadable reply is not exotic - it is Tuesday. Without containment a single
such hiccup propagates out of the sub-game and crashes the whole driver,
forfeiting every remaining sub-game with it. That is the worst outcome on the
board: the rulebook already scores an unfinished sub-game a technical loss
(nobody scores), but only if the series survives to play the next one.

This module names the failures that a sub-game may absorb locally and builds
the zeroed result row that stands in for the game that could not finish, so the
schedule always plays to its end.

Crash recovery - persisting the rows that DID settle - lives next door in
:mod:`series_checkpoint`, split out under the 150-line rule. Containment
protects the schedule; checkpointing protects evidence, and a series against a
real opponent cannot be replayed.
"""

from __future__ import annotations

from typing import Any

from ..infra.mcp_client import PeerUnreachableError
from ..infra.transport import TransportError
from .series_checkpoint import (
    CHECKPOINT_NAME,
    archive_previous_run,
    checkpoint_path,
    load_rows,
    save_rows,
)
from .turn_reorder import HandshakeRejectedError

#: Re-exported so a caller reasoning about a fragile series gets containment and
#: crash recovery from one import, even though they are now two modules.
__all__ = [
    "CHECKPOINT_NAME",
    "CONTAINED_FAILURES",
    "archive_previous_run",
    "checkpoint_path",
    "contained_failures",
    "containment_alarm",
    "failure_reason",
    "load_rows",
    "save_rows",
    "technical_loss_row",
]

#: Failures a sub-game absorbs as its own technical loss instead of crashing the
#: series. ``TimeoutError`` covers a stalled ``wait_for`` and the deadline
#: tracker's ``DeadlineExpiredError`` (its subclass); the RuntimeError family
#: covers an unreachable peer, a transport fault and a handshake refusal.
CONTAINED_FAILURES: tuple[type[Exception], ...] = (
    PeerUnreachableError,
    TransportError,
    HandshakeRejectedError,
    TimeoutError,
)


def failure_reason(error: BaseException) -> str:
    """A compact ``Type: message`` label for logs and the row's audit note."""
    return f"{type(error).__name__}: {error}"


def technical_loss_row(
    *,
    sub_game_number: int,
    us: str,
    opponent: str,
    role: str,
    expect_role: str,
    game_id: str,
    github_commit: str,
    reason: str,
) -> dict[str, Any]:
    """A properly-shaped zeroed result row for a sub-game that could not finish.

    Matches the shape the driver emits for a played sub-game so the result
    aggregate and the kit's checker read it without a special case. Nobody
    scores (rulebook technical loss); ``tampered`` stays false because a
    network failure is not a forgery, and ``log_verified`` is false because no
    disclosure was ever audited.
    """
    log_name = f"log_{game_id}_g{sub_game_number:02d}.json"
    return {
        "sub_game_number": sub_game_number,
        "roles": {us: role, opponent: expect_role},
        "started_at": "",
        "ended_at": "",
        "result": "technical_loss",
        "winner_group": None,
        "tie": False,
        "steps": 0,
        "github_commit": {us: github_commit, opponent: "unknown"},
        "tokens": {us: 0, opponent: 0},
        "score": {us: 0, opponent: 0},
        "log_files": {us: log_name, opponent: log_name},
        "audit": {"log_verified": False, "tampered": False, "reason": reason},
    }


def contained_failures(rows: list[dict[str, Any]]) -> list[str]:
    """The reasons of the rows that were absorbed as technical losses.

    A contained row is exactly the one :func:`technical_loss_row` builds, and
    the marker is its ``audit.reason`` note: a sub-game that really played
    records no reason, because nothing needed excusing.
    """
    return [
        str(reason)
        for row in rows
        if row.get("result") == "technical_loss"
        and (reason := (row.get("audit") or {}).get("reason"))
    ]


def containment_alarm(rows: list[dict[str, Any]]) -> str | None:
    """A loud operator warning when contained failures dominate the series.

    Containment is right per sub-game - one dead tunnel must not cost the other
    five - but it is the wrong lens on a whole series. A single opponent
    failing every single time is far less likely than a fault on our own side,
    and because each containment prints only a quiet line and then scores a
    normal-looking technical loss, a broken driver otherwise finishes with a
    tidy summary and no alarm at all. That is exactly how the ``next_step``
    crash produced a clean 2-2 series report while the opponent lay dead.

    Returns ``None`` when the series looks healthy. This warns only: it never
    raises, and it never touches a byte of any artifact, because the report
    must stay honest about what actually happened.
    """
    if not rows:
        return None
    reasons = contained_failures(rows)
    if len(reasons) * 2 <= len(rows):
        return None
    every = len(reasons) == len(rows)
    scope = "EVERY sub-game" if every else f"{len(reasons)} of {len(rows)} sub-games"
    distinct = sorted(set(reasons))
    lines = [
        "!" * 72,
        f"WARNING: {scope} ended as a CONTAINED technical loss.",
        "",
        "This almost certainly indicates a bug on OUR side, not the opponent's.",
        "An opponent who fails this consistently is far less likely than a fault",
        "in our own driver, config or network setup. Investigate before playing a",
        "counted series - the result below is honest, but it is probably our fault.",
        "",
        f"distinct failure reasons seen ({len(distinct)}):",
        *(f"  - {reason}" for reason in distinct),
        "!" * 72,
    ]
    return "\n".join(lines)
