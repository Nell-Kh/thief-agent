"""Tests for the two-ply endgame search and the box cop built on it."""

from __future__ import annotations

import pytest

from police_thief.constants import MOVE_STAY, ROLE_POLICE, ROLE_THIEF
from police_thief.domain.board import Board
from police_thief.domain.brain.base import BrainView, load_brain
from police_thief.domain.brain.box import BoxPoliceBrain
from police_thief.domain.brain.seal import SealPoliceBrain
from police_thief.domain.brain.search import (
    CAPTURE,
    best_action,
    captured,
    cop_actions,
    evaluate,
    search,
)
from police_thief.domain.rules import destination, is_trapped
from police_thief.shared.config import ConfigManager

#: The seal cop's finished wall, door at (3, 3) already stoned.
SEALED_WALL = {(0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3)}


@pytest.fixture(scope="module")
def contract():
    """The shipped contract."""
    return ConfigManager.load(ROLE_POLICE).contract


def test_capture_is_recognised_in_all_three_forms() -> None:
    board = Board(7, set())
    assert captured(board, (2, 2), (2, 2))                       # overlap
    assert captured(Board(7, {(2, 2)}), (0, 0), (2, 2))          # stone on the thief
    boxed = Board(7, {(0, 1), (1, 0)})
    assert is_trapped(boxed, (0, 0)) and captured(boxed, (6, 6), (0, 0))  # no exit
    assert not captured(board, (0, 0), (3, 3))


def test_a_captured_position_evaluates_to_the_terminal_value() -> None:
    assert evaluate(Board(7, set()), (2, 2), (2, 2)) == CAPTURE
    assert evaluate(Board(7, set()), (0, 0), (3, 3)) > CAPTURE


def test_actions_are_steps_plus_stones_never_on_the_cops_own_cell() -> None:
    board = Board(7, set())
    actions = cop_actions(board, (3, 3), stones_left=1)
    steps = [a for a in actions if a[1] is None]
    stones = [a for a in actions if a[1] is not None]
    assert len(steps) == 4 and len(stones) == 4
    assert all(a[0] == MOVE_STAY for a in stones)
    assert (3, 3) not in {a[1] for a in stones}
    assert all(a[1] is None for a in cop_actions(board, (3, 3), stones_left=0))


def test_an_immediate_capture_is_taken_without_searching() -> None:
    """An adjacent thief is captured now - by stepping on it or stoning it."""
    board = Board(7, set())
    move, stone = best_action(board, (3, 3), (3, 4), stones_left=1, depth=2)
    after = Board(7, set(board.barriers) | {stone}) if stone else board
    assert captured(after, destination((3, 3), move), (3, 4))


def test_the_search_sees_a_forced_capture_two_plies_out() -> None:
    """A corner thief with the cop on its diagonal is dead in two cop moves.

    From (1,1) the cop is adjacent to both of the corner's exits, (0,1) and
    (1,0). One stone leaves one exit and the thief must take it or stay; either
    way the second cop action captures. Depth 1 cannot see that; depth 2 must.
    """
    board = Board(7, set())
    assert search(board, (1, 1), (0, 0), stones_left=2, depth=2) == CAPTURE


def test_the_box_cop_plays_the_seal_opening_until_the_chamber_closes(contract) -> None:
    box = BoxPoliceBrain(ROLE_POLICE, contract)
    seal = SealPoliceBrain(ROLE_POLICE, contract)
    view = BrainView(ROLE_POLICE, (0, 0), (3, 3), Board(7, set()), 14, 0)
    assert box.decide(view) == seal.decide(view)


def test_the_box_cop_boxes_the_evader_inside_the_sealed_chamber(contract) -> None:
    """The measurement that justifies round 5, held as a test.

    From the position the seal cop reaches at turn 20 - wall up, door stoned,
    cop (3,4), thief (5,5), seven stones - its inherited region hunt failed to
    capture in fifteen turns. The search boxes the evader in five.
    """
    thief = load_brain("police_thief.domain.brain.evade:EvadeThiefBrain", ROLE_THIEF, contract)
    cop = BoxPoliceBrain(ROLE_POLICE, contract)
    board, cop_at, thief_at, stones = Board(7, set(SEALED_WALL)), (3, 4), (5, 5), 7
    for step in range(15):
        thief_at = destination(thief_at, thief.decide(
            BrainView(ROLE_THIEF, thief_at, cop_at, board, 0, step)).move)
        if thief_at == cop_at:
            break
        action = cop.decide(BrainView(ROLE_POLICE, cop_at, thief_at, board, stones, step))
        cop_at = destination(cop_at, action.move)
        if action.barrier is not None:
            board, stones = Board(7, set(board.barriers) | {action.barrier}), stones - 1
        if captured(board, cop_at, thief_at):
            break
    else:
        raise AssertionError("the box cop did not capture inside the chamber in 15 turns")
    assert step + 1 <= 6, f"captured at turn {step + 1}; the measured figure is 5"


def test_the_search_owns_the_position_once_the_wall_stands(contract) -> None:
    """Hand-off is on the wall, not the door - and never on a doorway belief.

    Handing over before the wall is complete was measured catastrophic (0 of
    40 starts: a two-ply horizon never finishes a wall); handing over only once
    the door is stoned costs a step. A believed thief in the wall column is
    ambiguous and stays with the seal cop's adjacent-trap rule.
    """
    cop = BoxPoliceBrain(ROLE_POLICE, contract)
    open_door = Board(7, set(SEALED_WALL) - {(3, 3)})
    assert cop._search_owns(BrainView(ROLE_POLICE, (3, 4), (5, 5), open_door, 8, 15))
    assert cop._search_owns(BrainView(ROLE_POLICE, (3, 2), (5, 5), open_door, 8, 15))
    assert not cop._search_owns(BrainView(ROLE_POLICE, (3, 4), (2, 3), open_door, 8, 15))
    five_stones = Board(7, set(SEALED_WALL) - {(3, 3), (6, 3)})
    assert not cop._search_owns(BrainView(ROLE_POLICE, (5, 2), (5, 5), five_stones, 9, 13))
