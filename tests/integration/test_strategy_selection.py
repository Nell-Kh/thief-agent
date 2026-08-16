"""The shipped `[strategy]` lines must still be the brains that actually win.

Two `package.module:Class` strings in the private TOMLs decide more of the
league score than any other line in the repository, and nothing checked them.
They were chosen from a research notebook measured under PERFECT INFORMATION -
the wrong condition, as `hybrid.py` itself documents: a cop twelve steps faster
with perfect knowledge is six steps *slower* once it must chase a belief
argmax. A brain improved later, or a config edited in a hurry, could silently
leave the weaker pick in place and nothing would fail.

So the choice is re-derived here, in the condition that pays: complete
:class:`MatchRuntime` matches under belief, from the contract's fixed start,
with the verbal layer pinned so no model call can perturb a move. The harness
is :mod:`scripts.brain_tournament`; this module is the gate on its verdict.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from brain_tournament import (  # noqa: E402
    COPS,
    THIEVES,
    configured,
    cop_score,
    matrix,
    thief_score,
)

#: The verdict this suite pins. Both are re-derived below rather than trusted -
#: if a new brain beats them, this constant is what a contributor must change,
#: deliberately, in one place.
#:
#: It read ("wall", "evade") while `seal` was absent from the harness's COPS
#: dict, which made the gate self-consistent and wrong: it re-derived a winner
#: from a field that excluded the only candidate able to beat it.
EXPECTED_BEST = ("box", "evade")

#: The cops that convert the PURSUIT-style archetypes under belief. Every
#: barrier cop does. Only ONE of them converts the elite evader (see
#: :data:`ELITE_CONVERTERS`), so this set is deliberately not "every thief".
BARRIER_COPS = {"region", "wall", "hybrid", "seal", "box"}

#: The archetypes every barrier cop is expected to convert.
CONVERTIBLE = ("blind", "enhanced")

#: The cops that convert OUR OWN elite evader under belief - round 5 of the
#: arms race, and until it existed this set was empty. A cop joining it is the
#: headline; a cop leaving it is the regression that loses league games.
ELITE_CONVERTERS = {"box"}


#: The shipped configuration directory, module-scoped so the matrix is too.
SHIPPED_CONFIG = REPO_ROOT / "config"


@pytest.fixture(scope="module")
def results() -> dict:
    """The full belief-mode matrix, played once for every test in this module."""
    return matrix(SHIPPED_CONFIG)


def best_cop(results: dict) -> str:
    """Most captures, then fewest steps to get them."""
    return max(COPS, key=lambda name: (cop_score(results, name)[0],
                                       -cop_score(results, name)[1]))


def best_thief(results: dict) -> str:
    """Most survivals, then longest mean life."""
    return max(THIEVES, key=lambda name: thief_score(results, name))


def test_every_brain_in_the_tree_still_plays_a_legal_match(results) -> None:
    """A brain that crashes or wedges must fail here, not in a counted series."""
    undecided = {pair: row for pair, row in results.items() if row[0] == "undecided"}
    assert not undecided, f"pairings that never settled: {undecided}"


def test_the_configured_cop_converts_every_thief_archetype(results) -> None:
    """The shipped cop must CONVERT every archetype - the property that pays.

    This asserted "the cop the matrix ranks first" while exactly one cop
    converted the elite evader, so ranking and conversion were the same fact.
    The emitter fit (``domain/emitter.py``) broke that tie: with the opponent
    located by model inversion instead of by the peak of a clamped plateau,
    `wall`, `hybrid` and `seal` all convert all three archetypes, and the
    ranking falls through to its speed tie-break - which scores nothing. A
    capture at 24 and a capture at 25 both pay 20/5.

    So the gate now pins what the rulebook pays for. Among full converters we
    ship `seal`, because its conversion is STRUCTURAL - cross the door, spend a
    stone on it, hunt a closed chamber - where `wall`'s now rests on the
    belief being precise. Speed is reported by the sibling tests, not ranked
    here.
    """
    police_spec, _thief_spec = configured(SHIPPED_CONFIG)
    shipped = next(name for name, spec in COPS.items() if spec == police_spec)
    unconverted = [
        thief for thief in CONVERTIBLE
        if results[(shipped, thief)][0] != "capture"
    ]
    assert not unconverted, (
        f"config/police/game.toml ships {shipped!r}, which fails to convert "
        f"{unconverted} under belief - fix the brain or change the TOML"
    )


def test_the_configured_thief_is_the_thief_that_survives_most(results) -> None:
    _police_spec, thief_spec = configured(SHIPPED_CONFIG)
    assert thief_spec == THIEVES[best_thief(results)], (
        f"config/thief/game.toml selects {thief_spec!r} but {best_thief(results)!r} "
        f"survives more under belief - update the TOML or this expectation"
    )


def test_the_barrier_cops_are_the_ones_that_convert(results) -> None:
    """Stones are what convert a thief; pure pursuit never has.

    A cop JOINING or LEAVING this set is the thing a contributor must notice,
    which is why it is named rather than derived from a ranking.
    """
    converters = {
        cop for cop in COPS
        if all(results[(cop, thief)][0] == "capture" for thief in CONVERTIBLE)
    }
    assert converters == BARRIER_COPS, (
        f"the cops converting {list(CONVERTIBLE)} are {sorted(converters)}, not "
        f"{sorted(BARRIER_COPS)} - update BARRIER_COPS deliberately"
    )
    assert best_thief(results) == EXPECTED_BEST[1]


def test_the_wall_cop_captures_every_pursuit_style_thief(results) -> None:
    """Its whole justification: a guaranteed capture, not a fast one."""
    for thief in ("blind", "enhanced"):
        outcome, winner, _steps = results[("wall", thief)]
        assert (outcome, winner) == ("capture", "police"), f"wall failed vs {thief}"


def test_the_wall_cop_captures_faster_than_the_hybrid_under_belief(results) -> None:
    """The perfect-information speed advantage does not survive belief.

    This is the trap `hybrid.py` warns about, held as a test so nobody
    re-reads the notebook's 1900-start numbers and swaps the cop back.
    """
    wall = [steps for thief in THIEVES
            if (row := results[("wall", thief)])[0] == "capture" for steps in [row[2]]]
    hybrid = [steps for thief in THIEVES
              if (row := results[("hybrid", thief)])[0] == "capture" for steps in [row[2]]]
    assert wall and hybrid
    assert max(wall) <= min(hybrid)


def test_exactly_the_round_five_cop_converts_the_elite_evader(results) -> None:
    """Round 5: the box cop is in front, and this is where a round-6 thief lands.

    The order of the race, so nobody re-reads a stale table: `wall` beat the
    evader, so `evade` was tuned and beat `wall`; `seal` was written and beat
    `evade`; the emitter fit (`domain/emitter.py`) let every barrier cop beat
    it again; then ``openness`` learned to count a placed stone as a wall and
    the thief walked past all of them; and then `box` kept seal's opening and
    replaced its endgame with a two-ply search, which boxes the evader inside
    the sealed chamber where the region hunt danced. Every step of that was
    measured here. A round-6 thief is exactly the change that breaks this test.
    """
    converters = {
        cop for cop in COPS
        if results[(cop, "evade")][:2] == ("capture", "police")
    }
    assert converters == ELITE_CONVERTERS, (
        f"the cops converting the elite evader are {sorted(converters)}, not "
        f"{sorted(ELITE_CONVERTERS)} - the race moved; update ELITE_CONVERTERS"
    )


def test_the_shipped_cop_converts_the_elite_evader(results) -> None:
    """The league choice must be an elite converter, or the choice is wrong."""
    police_spec, _thief_spec = configured(SHIPPED_CONFIG)
    shipped = next(name for name, spec in COPS.items() if spec == police_spec)
    assert shipped in ELITE_CONVERTERS, (
        f"config/police/game.toml ships {shipped!r}, which does not convert the "
        f"elite evader under belief - ship one of {sorted(ELITE_CONVERTERS)}"
    )
