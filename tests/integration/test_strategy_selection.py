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
EXPECTED_BEST = ("seal", "evade")

#: The cops that convert EVERY thief archetype under belief. Three since the
#: emitter fit; `seal` is the one shipped, for the reason its own test states.
FULL_CONVERTERS = {"wall", "hybrid", "seal"}


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
        thief for thief in THIEVES
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


def test_every_full_converter_is_named(results) -> None:
    """If the set of cops that convert everything changes, say so deliberately.

    Replaces a single-winner pin, which the emitter fit made meaningless: with
    three cops converting all three archetypes, "who is first" is decided by a
    speed tie-break worth zero points. What a contributor must notice is a cop
    JOINING or LEAVING this set.
    """
    converters = {
        cop for cop in COPS
        if all(results[(cop, thief)][0] == "capture" for thief in THIEVES)
    }
    assert converters == FULL_CONVERTERS, (
        f"the cops converting every archetype are {sorted(converters)}, not "
        f"{sorted(FULL_CONVERTERS)} - update FULL_CONVERTERS deliberately"
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


def test_the_barrier_cops_convert_the_elite_evader(results) -> None:
    """Who beats the evader, and what changed the answer.

    `seal` was written because `wall` oscillated two cells from the door
    forever - and we read that as needing commitment rather than information.
    Both were true. The emitter fit supplied the information (the transmitted
    trail clamps into a plateau, so the peak located nothing), and with it the
    barrier cops convert the evader too. The pure-pursuit cop still cannot:
    equal speed with no stones is the parity dance, exactly as README 5 says.
    """
    for cop in FULL_CONVERTERS:
        outcome, winner, _steps = results[(cop, "evade")]
        assert (outcome, winner) == ("capture", "police"), f"{cop} vs evade: {outcome}"
    outcome, winner, _steps = results[("blind", "evade")]
    assert (outcome, winner) == ("survival", "thief"), "pure pursuit should not convert"
