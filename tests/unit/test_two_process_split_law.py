"""Rule 1: the cop and the thief are two processes, and neither files a series.

Appendix ה table 7 rule 1 and §2.4.2 require the cop's code and the thief's code
to run in two completely separate processes under separate config directories,
and name the sanction plainly: ``כישלון מוחלט``, total failure, *even where the
game works technically*. Our league driver played both roles from a single
process. Separate config directories, yes; separate processes, no.

najamjad (2026-08-18) publish a match specification that refuses an unsplit peer
outright, and they are right to - they have declined series over it. We read
§2.4.2 properly only because they said so, and the finding is worth more than
the match: it was a submission risk sitting unverified in our own open list.

Two properties are load-bearing here and both are cheap to state and expensive
to discover late:

**The halves partition the series.** Every window belongs to exactly one
process. A gap loses a sub-game nobody played; an overlap has both of our
processes dialling the same window, which the opponent sees as two peers
claiming one game.

**A half never files.** Three rows presented as a match is precisely the
contradictory report rules 33-35 void for BOTH teams - and it would look
entirely well-formed. So a locked run stops at its rows, and the only place a
six-row result exists is :mod:`merge_series`, joining two finished halves off
disk with no shared live state between the processes at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import merge_series  # noqa: E402
from _series_windows import BOTH, is_split, role_at, split_notice, windows_for  # noqa: E402


def row(number: int) -> dict:
    """A settled row, trimmed to the one field the merge orders and checks."""
    return {"sub_game_number": number, "result": "capture"}


@pytest.mark.parametrize("start", ["police", "thief"])
def test_the_two_halves_partition_the_series_exactly(start) -> None:
    """No window is played twice and none is played by nobody."""
    police = windows_for(6, start, "police")
    thief = windows_for(6, start, "thief")
    assert sorted(police + thief) == [1, 2, 3, 4, 5, 6]
    assert not set(police) & set(thief)


@pytest.mark.parametrize("start", ["police", "thief"])
def test_each_half_only_ever_holds_its_own_role(start) -> None:
    """The whole point: a locked process is one role, for the whole series."""
    for locked in ("police", "thief"):
        assert {role_at(n, start) for n in windows_for(6, start, locked)} == {locked}


def test_unsplit_is_still_available_and_plays_everything() -> None:
    """The single-process path stays, for rehearsals against ourselves."""
    assert windows_for(6, "police", BOTH) == [1, 2, 3, 4, 5, 6]
    assert not is_split(BOTH)
    assert is_split("police") and is_split("thief")


def test_a_locked_half_is_told_it_must_not_file() -> None:
    """Silence here would let someone mail three rows as a series."""
    notice = split_notice([1, 3, 5], "results/x_police", 0)
    assert "files NOTHING" in notice
    assert "merge_series.py" in notice


def test_the_notice_carries_the_number_the_opponent_declared() -> None:
    """games_played is theirs to state; rule 38 disqualifies whoever invents one."""
    assert "games_played = 4" in split_notice([2, 4, 6], "results/x_thief", 4)


def test_the_merge_orders_the_rows_it_was_handed_out_of_order(tmp_path, monkeypatch) -> None:
    """Halves finish in whatever order they finish; the report is always sorted."""
    monkeypatch.setattr(merge_series, "load_rows",
                        lambda path: [row(2), row(4), row(6)] if "thief" in str(path)
                        else [row(1), row(3), row(5)])
    merged = merge_series.gather([str(tmp_path / "a_thief"), str(tmp_path / "b_police")])
    assert [r["sub_game_number"] for r in merged] == [1, 2, 3, 4, 5, 6]


def test_the_merge_refuses_two_halves_that_claim_the_same_window(monkeypatch) -> None:
    """Both processes dialling one window is a bug we must not paper over."""
    monkeypatch.setattr(merge_series, "load_rows", lambda path: [row(1), row(2)])
    with pytest.raises(SystemExit) as refusal:
        merge_series.gather(["a", "b"])
    assert "both halves" in str(refusal.value)


def test_the_merge_refuses_an_incomplete_series(monkeypatch) -> None:
    """A missing window would file a shorter series than the one played."""
    monkeypatch.setattr(merge_series, "load_rows",
                        lambda path: [row(1), row(3)] if "police" in str(path) else [])
    with pytest.raises(SystemExit) as refusal:
        merge_series.gather(["x_police", "y_thief"])
    assert "incomplete" in str(refusal.value)


def test_the_merge_accepts_exactly_the_complete_pair(monkeypatch) -> None:
    """The one case that must pass: three and three, disjoint, covering 1..6."""
    monkeypatch.setattr(merge_series, "load_rows",
                        lambda path: [row(n) for n in ([1, 3, 5] if "police" in str(path)
                                                       else [2, 4, 6])])
    assert len(merge_series.gather(["x_police", "y_thief"])) == 6
