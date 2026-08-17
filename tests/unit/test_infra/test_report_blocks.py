"""Tests for the two report fields the driver used to leave empty or unknown.

Both were found by diffing our result report against an opponent's on
2026-08-17: theirs carried real instants and a real commit SHA where ours
carried ``""`` and ``"unknown"``. Neither field is inside the consensus hash,
so neither forked the settlement - which is exactly why nothing caught them.
"""

from __future__ import annotations

from datetime import datetime

from police_thief.infra.email.report_blocks import now_iso, opponent_commit


def test_a_row_timestamp_is_an_instant_not_an_empty_string() -> None:
    """Every row we filed before 2026-08-17 carried ``""`` for both stamps."""
    stamp = now_iso()
    parsed = datetime.fromisoformat(stamp)
    assert parsed.tzinfo is not None, "a report timestamp must carry its offset"
    assert stamp.endswith("+00:00"), f"reports are stamped in UTC, got {stamp}"


def test_the_opponents_commit_is_read_from_the_step_zero_record_it_revealed() -> None:
    """Rule #53's field, derived from the disclosure instead of filed as unknown."""
    disclosure = {
        "sender": "police",
        "records": [
            {"payload": {"type": "system_spec", "github_commit": "7d13ab17c0048238a8ac"}},
            {"payload": {"type": "turn", "step": 1}},
        ],
    }
    assert opponent_commit(disclosure) == "7d13ab17c0048238a8ac"


def test_a_disclosure_without_a_step_zero_record_reports_unknown_honestly() -> None:
    """Absent is absent - never a guess, and never a crash."""
    assert opponent_commit({"records": [{"payload": {"type": "turn"}}]}) == "unknown"
    assert opponent_commit({"records": []}) == "unknown"
    assert opponent_commit(None) == "unknown"
    assert opponent_commit({"records": [{"payload": {"type": "system_spec"}}]}) == "unknown"
