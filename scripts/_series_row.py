"""Scoring one settled sub-game into its league row, and writing its artifacts.

Split from ``_series_subgame`` under the 150-line rule, along the seam the code
already had: everything up to the mutual audit is *conversation with an
opponent*, and everything here is *bookkeeping about a game that is over*.

Nothing in this file may guess. Every field is either measured (steps, tokens),
derived from a verification we performed (``audit``), or read out of something
the opponent signed (``github_commit``) - because the two fields we did invent,
an empty timestamp and an ``"unknown"`` commit, are exactly the two an opponent
caught us on (sharNamr, 2026-08-17).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from police_thief.infra.email.naming import (
    config_file_name,
    write_lifecycle_file,
)
from police_thief.infra.email.report_blocks import now_iso, opponent_commit
from police_thief.infra.email.reports import config_payload, log_payload

__all__ = ["ZEROED", "keep_opponent_disclosure", "now_iso", "score_row",
           "write_sub_game_files"]

#: Outcomes that credit nobody - a sanction, not a win for the other side.
ZEROED = ("timeout", "technical_loss", "tamper_forfeit")


def keep_opponent_disclosure(artifacts: Path, game_id: str, n: int,
                             verdict: str, disclosure: dict[str, Any]) -> None:
    """File the opponent's revealed records beside our own log.

    The only place THEIR positions exist on our side. A series lost with no
    opponent trace can be replayed but never explained - which is what 0-6
    against sharNamr (2026-08-17) cost us before this existed.
    """
    write_lifecycle_file(artifacts, f"opponent_{game_id}_g{n:02d}.json", {
        "game_id": game_id, "sub_game_number": n,
        "audit_verdict": verdict, "disclosure": disclosure})


def score_row(*, n: int, role: str, expect_role: str, us: str, opponent: str,
              outcome_type: str, passed: bool, steps: int, tokens: int,
              our_commit: str, their_disclosure: dict[str, Any],
              started_at: str, scores: tuple[int, int], game_id: str) -> dict[str, Any]:
    """One sub-game's league row, every field measured or derived.

    ``audit`` is earned, not asserted: ``passed`` is the verdict of actually
    re-hashing the opponent's every sealed record against the commitment it
    published and checking the trajectory against the signed contract. An
    opponent found their own copy of this field to be a hardcoded literal and
    asked, fairly, whether ours was real - it is, and this is where it is
    written down.
    """
    score_us, score_them = (0, 0) if not passed else scores
    zeroed = outcome_type in ZEROED
    tie = (not zeroed) and score_us == score_them
    winner = None if zeroed or tie else (us if score_us > score_them else opponent)
    log_name = f"log_{game_id}_g{n:02d}.json"
    return {
        "sub_game_number": n, "roles": {us: role, opponent: expect_role},
        "started_at": started_at, "ended_at": now_iso(),
        "result": "tamper_forfeit" if not passed else outcome_type,
        "winner_group": winner, "tie": tie, "steps": steps,
        "github_commit": {us: our_commit, opponent: opponent_commit(their_disclosure)},
        "tokens": {us: tokens, opponent: 0},
        "score": {us: score_us, opponent: score_them},
        "log_files": {us: log_name, opponent: log_name},
        "audit": {"log_verified": passed, "tampered": not passed},
    }


def write_sub_game_files(*, artifacts: Path, game_uid: str, game_id: str, n: int,
                         terms: dict[str, Any], links: dict[str, Any], recipient: str,
                         counted: bool, summary: dict[str, Any],
                         records: list[dict[str, Any]]) -> None:
    """The per-sub-game config and log, in the league's joined shape."""
    write_lifecycle_file(artifacts, config_file_name(game_id, n),
                         config_payload(game_uid, game_id, n, terms, links, recipient,
                                        counted=counted))
    write_lifecycle_file(artifacts, f"log_{game_id}_g{n:02d}.json",
                         log_payload(game_uid, game_id, n, links, summary,
                                     records, recipient, counted=counted))
