"""Tests for the series-level containment alarm.

Per sub-game, absorbing a network fault as a technical loss is correct. Across a
whole series it is a symptom: an opponent that fails every single time is far
less likely than a fault on our own side. These tests pin the threshold and the
wording, because the alarm's whole job is to be impossible to read past.
"""

from __future__ import annotations

from typing import Any

from police_thief.services.series_guard import (
    contained_failures,
    containment_alarm,
    technical_loss_row,
)


def contained(n: int, reason: str) -> dict[str, Any]:
    """One contained technical-loss row, as the driver would record it."""
    return technical_loss_row(
        sub_game_number=n, us="yanell11", opponent="team-tbd", role="thief",
        expect_role="police", game_id="team-tbd-vs-yanell11",
        github_commit="abc1234", reason=reason,
    )


def played(n: int, result: str = "capture") -> dict[str, Any]:
    """A sub-game that really finished - note it records no audit reason."""
    return {
        "sub_game_number": n, "result": result, "winner_group": "yanell11",
        "audit": {"log_verified": True, "tampered": False},
    }


def test_a_healthy_series_raises_no_alarm() -> None:
    """Six real sub-games are exactly what we hope to see; stay silent."""
    assert containment_alarm([played(n) for n in range(1, 7)]) is None


def test_an_empty_series_raises_no_alarm() -> None:
    """Nothing played means nothing to diagnose."""
    assert containment_alarm([]) is None


def test_a_single_contained_failure_is_not_an_alarm() -> None:
    """One dead tunnel in six is the case containment exists for."""
    rows = [contained(1, "TimeoutError: no turn")] + [played(n) for n in range(2, 7)]
    assert containment_alarm(rows) is None


def test_an_exact_half_is_still_not_an_alarm() -> None:
    """The threshold is a strict majority, so 3 of 6 stays quiet."""
    rows = [contained(n, "TimeoutError: no turn") for n in (1, 2, 3)]
    rows += [played(n) for n in (4, 5, 6)]
    assert containment_alarm(rows) is None


def test_a_majority_of_contained_failures_raises_the_alarm() -> None:
    """Four of six is past the line and must say so, and blame our side."""
    rows = [contained(n, "TimeoutError: no turn") for n in (1, 2, 3, 4)]
    rows += [played(n) for n in (5, 6)]
    alarm = containment_alarm(rows)
    assert alarm is not None
    assert "4 of 6 sub-games" in alarm
    assert "OUR side" in alarm


def test_a_fully_contained_series_names_every_sub_game() -> None:
    """The `next_step` crash produced exactly this shape and printed no alarm."""
    rows = [contained(n, "PeerUnreachableError: opponent unreachable") for n in range(1, 7)]
    alarm = containment_alarm(rows)
    assert alarm is not None
    assert "EVERY sub-game" in alarm
    assert "PeerUnreachableError: opponent unreachable" in alarm


def test_distinct_reasons_are_deduplicated_and_counted() -> None:
    """Six failures with two causes should report two, not six."""
    rows = [contained(n, "TimeoutError: no turn") for n in (1, 2, 3)]
    rows += [contained(n, "TransportError: reset") for n in (4, 5, 6)]
    alarm = containment_alarm(rows)
    assert alarm is not None
    assert "distinct failure reasons seen (2):" in alarm
    assert "TimeoutError: no turn" in alarm
    assert "TransportError: reset" in alarm


def test_contained_failures_ignores_a_played_sub_game() -> None:
    """A real technical loss on the board carries no audit reason to report."""
    rows = [played(1), contained(2, "TimeoutError: no turn"), played(3, "technical_loss")]
    assert contained_failures(rows) == ["TimeoutError: no turn"]


def test_the_alarm_never_mutates_the_rows() -> None:
    """It is an operator warning only - the report must stay byte-honest."""
    rows = [contained(n, "TimeoutError: no turn") for n in range(1, 7)]
    before = [dict(row) for row in rows]
    containment_alarm(rows)
    assert rows == before
