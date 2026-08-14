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

#: The verdict this suite pins. Both are documented in the private TOMLs, and
#: both are re-derived below rather than trusted - if a new brain beats them,
#: this constant is what a contributor must change, deliberately, in one place.
EXPECTED_BEST = ("wall", "evade")


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


def test_the_configured_cop_is_the_cop_that_wins_most(results) -> None:
    police_spec, _thief_spec = configured(SHIPPED_CONFIG)
    assert police_spec == COPS[best_cop(results)], (
        f"config/police/game.toml selects {police_spec!r} but {best_cop(results)!r} "
        f"scores better under belief - update the TOML or this expectation"
    )


def test_the_configured_thief_is_the_thief_that_survives_most(results) -> None:
    _police_spec, thief_spec = configured(SHIPPED_CONFIG)
    assert thief_spec == THIEVES[best_thief(results)], (
        f"config/thief/game.toml selects {thief_spec!r} but {best_thief(results)!r} "
        f"survives more under belief - update the TOML or this expectation"
    )


def test_the_pinned_verdict_is_the_measured_verdict(results) -> None:
    """If a new brain wins, the change must be deliberate and named here."""
    assert (best_cop(results), best_thief(results)) == EXPECTED_BEST


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


def test_the_evade_thief_survives_every_cop_in_the_tree(results) -> None:
    """Including our own wall cop, which beats every other thief we have."""
    for cop in COPS:
        outcome, winner, _steps = results[(cop, "evade")]
        assert (outcome, winner) == ("survival", "thief"), f"evade died to {cop}"
