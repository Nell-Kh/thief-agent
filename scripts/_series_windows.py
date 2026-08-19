"""Which sub-games this process plays - the rule-1 split, expressed as a filter.

Appendix ה table 7 rule 1 and §2.4.2 require the cop's code and the thief's code
to run in **two completely separate processes**, under separate config
directories, and the sanction named is ``כישלון מוחלט`` - total failure - even
where the game works technically. Our league driver played both roles from one
process: separate config directories, one process. najamjad (2026-08-18) refuse
to play an unsplit peer and were right to; we read §2.4.2 properly after they
said so.

The split is a filter rather than a fork. One process is told which windows are
its own and simply does not dial the others; the opponent's other process is
playing those, and our peer sees exactly the same wire either way. Two
instances, two ports, two tunnels, two artifact directories, and **no shared
live state between them at all** - which is the property the rule is actually
protecting. They never import each other and never exchange anything in memory;
the only join is :mod:`merge_series`, reading two files off disk once the series
is over.

Roles alternate from ``--start-role``, so the odd windows are the start role and
the even ones its complement. That is the whole calculation, and it lives here
because both the driver and the merge step have to agree about it exactly.
"""

from __future__ import annotations

from _series_lib import other_role

#: ``--play-windows`` value meaning "this process plays every window" (unsplit).
BOTH = "both"


def role_at(sub_game: int, start_role: str) -> str:
    """Our role in ``sub_game``, counting the first window as ``start_role``."""
    return start_role if sub_game % 2 == 1 else other_role(start_role)


def is_split(play_windows: str) -> bool:
    """Whether this process is role-locked, and so plays only half the series."""
    return play_windows != BOTH


def windows_for(rounds: int, start_role: str, play_windows: str) -> list[int]:
    """The sub-game numbers this process is responsible for.

    An unsplit process owns all of them; a role-locked one owns the three where
    it holds its own role. The complement is not skipped in the sense of being
    forfeited - the opponent is playing it against our other process, and our
    rows for it arrive from that process's own artifacts at merge time.
    """
    return [n for n in range(1, rounds + 1)
            if not is_split(play_windows) or role_at(n, start_role) == play_windows]


def split_notice(windows: list[int], artifacts: str, their_games: int) -> str:
    """What a role-locked process says instead of writing a result.

    Three rows are not a series. A locked process that filed a result would be
    presenting half a match as a whole one - and two teams whose reports
    disagree about the sub-games played is precisely the contradiction rules
    33-35 void for BOTH sides. So the locked run stops at its rows and names the
    command that joins them, and the only place a six-row result is ever built
    is from two complete halves.
    """
    return (f"\nwindows {windows} settled. Artifacts under {artifacts}\n"
            f"  the opponent declared games_played = {their_games} on the wire - "
            f"pass it to the merge, do not invent one\n"
            f"  rule-1 split: this process played half the series and files NOTHING - "
            f"three rows are not a report.\n"
            f"  when the other half finishes:\n"
            f"    uv run python scripts/merge_series.py {artifacts} <other-role-dir>")
