"""The shipped cop against thieves built to break it - perfect information.

The tournament (``test_strategy_selection.py``) asks whether the cop converts
OUR thieves under belief. This file asks the harder question behind "as
strong as possible": does it convert thieves it was never tuned against, each
one written to attack an assumption of its plan? Played under PERFECT
INFORMATION - the thief's true cell, not a belief - because that is the
condition the search was designed in and the harder one for the cop's
opponents to exploit: a thief that beats the cop here would beat it anywhere.

Two conditions per adversary: the contract's fixed start (the league game),
and a spread of starts across the board (the plan must not be a property of
one corner). Round 5 measured 20 of 20 on every adversary; the spread here is
smaller so the file stays fast, and the fixed start is the one that counts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from police_thief.constants import ROLE_POLICE, ROLE_THIEF
from police_thief.domain.board import Board
from police_thief.domain.brain.base import BrainView, load_brain
from police_thief.domain.brain.search import captured
from police_thief.domain.rules import destination
from police_thief.shared.config import ConfigManager

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adversaries import ADVERSARIES, DoorCamper, SearchThief, Sticker  # noqa: E402

BOX = "police_thief.domain.brain.box:BoxPoliceBrain"

#: Starts far from the fixed one, in every quadrant, so a win is not corner-luck.
SPREAD = (((0, 6), (3, 3)), ((6, 6), (3, 3)), ((6, 0), (3, 3)),
          ((3, 0), (3, 6)), ((0, 3), (6, 3)), ((6, 6), (0, 0)))


@pytest.fixture(scope="module")
def contract():
    """The shipped contract."""
    return ConfigManager.load(ROLE_POLICE).contract


def play(cop, thief, contract, cop_at, thief_at) -> tuple[str, int]:
    """One perfect-information game, thief first, until capture or the threshold."""
    board, stones = Board(contract.board.grid_size, set()), contract.movement.max_barriers
    for step in range(contract.movement.survival_threshold):
        thief_at = destination(thief_at, thief.decide(
            BrainView(ROLE_THIEF, thief_at, cop_at, board, 0, step)).move)
        if thief_at == cop_at:
            return "capture", step + 1
        action = cop.decide(BrainView(ROLE_POLICE, cop_at, thief_at, board, stones, step))
        cop_at = destination(cop_at, action.move)
        if action.barrier is not None:
            board = Board(board.size, set(board.barriers) | {action.barrier})
            stones -= 1
        if captured(board, cop_at, thief_at):
            return "capture", step + 1
    return "survival", contract.movement.survival_threshold


@pytest.mark.parametrize("name", sorted(ADVERSARIES))
def test_the_box_cop_converts_every_adversary_from_the_fixed_start(name, contract) -> None:
    """The league condition: the contract's own start, against a thief we did not tune."""
    cop = load_brain(BOX, ROLE_POLICE, contract)
    thief = ADVERSARIES[name](ROLE_THIEF, contract)
    start = (tuple(contract.board.cop_start), tuple(contract.board.thief_start))
    outcome, steps = play(cop, thief, contract, *start)
    assert outcome == "capture", f"box failed to convert {name} from the fixed start"
    assert steps <= 30, f"box converts {name} at {steps} - too close to the threshold"


@pytest.mark.parametrize("name", ("doorcamper", "sticker"))
@pytest.mark.parametrize("start", SPREAD)
def test_the_box_cop_converts_the_cheap_adversaries_from_a_spread_of_starts(
    name, start, contract
) -> None:
    """The plan is not a property of one corner - six far starts, two adversaries."""
    cop = load_brain(BOX, ROLE_POLICE, contract)
    thief = {"doorcamper": DoorCamper, "sticker": Sticker}[name](ROLE_THIEF, contract)
    outcome, _steps = play(cop, thief, contract, *start)
    assert outcome == "capture", f"box failed to convert {name} from {start}"


def test_the_two_ply_search_thief_is_converted_from_a_far_start(contract) -> None:
    """The mirror image of the cop's own weapon, from the opposite corner."""
    cop = load_brain(BOX, ROLE_POLICE, contract)
    outcome, _steps = play(cop, SearchThief(ROLE_THIEF, contract), contract, (6, 6), (0, 0))
    assert outcome == "capture"
