"""Tests for the seal cop: cross the finished wall's door and lock it.

Every scenario here reproduces a moment from the first live internet
rehearsal, where the wall cop lost all six sub-games to the doorway-camping
evader - the seal brain exists because of that night.
"""

from __future__ import annotations

import pytest

from police_thief.constants import MOVE_STAY, ROLE_POLICE
from police_thief.domain.board import Board
from police_thief.domain.brain.base import BrainView
from police_thief.domain.brain.seal import SealPoliceBrain
from police_thief.domain.brain.wall import DOOR, WALL_ROWS
from police_thief.shared.config import ConfigManager

#: The finished wall: all six stones down, only the door open.
WALL = {(row, 3) for row in WALL_ROWS}


@pytest.fixture(scope="module")
def cop() -> SealPoliceBrain:
    """The seal brain under the real contract."""
    return SealPoliceBrain(ROLE_POLICE, ConfigManager.load(ROLE_POLICE).contract)


def view(cop_at, target, barriers=WALL, left=7) -> BrainView:
    """A brain view over a board with the given stones already placed."""
    return BrainView(role=ROLE_POLICE, position=cop_at, target=target,
                     board=Board(7, set(barriers)), barriers_left=left, step=20)


def test_a_cop_across_the_wall_marches_to_the_door(cop: SealPoliceBrain) -> None:
    """Left half, believed thief right: close on the door, never oscillate."""
    action = cop.decide(view((5, 2), (3, 5)))
    assert action.barrier is None
    assert action.move in ("N", "E")  # both shrink the way to (3, 3)


def test_crossing_the_door_steps_onto_the_thief_side(cop: SealPoliceBrain) -> None:
    action = cop.decide(view(DOOR, (3, 5)))
    assert action.move == "E"


def test_the_door_is_sealed_the_moment_the_cop_is_through(cop: SealPoliceBrain) -> None:
    """Just crossed, thief deep in the same half: one stone locks the chamber."""
    action = cop.decide(view((3, 4), (5, 5)))
    assert action.move == MOVE_STAY
    assert action.barrier == DOOR


def test_a_doorway_thief_is_never_sealed_in_the_door(cop: SealPoliceBrain) -> None:
    """Belief in the doorway is ambiguous: no stone is gambled on that cell.

    A trap at the door with the wall standing is the corridor-bricking bet
    all over again (its miss leaves the left half unreachable), and the seal
    decision itself explicitly defers whenever the believed thief sits in
    the doorway column.
    """
    action = cop.decide(view((3, 4), DOOR))
    assert action.barrier != DOOR


def test_a_trap_that_would_brick_the_corridor_is_refused(cop: SealPoliceBrain) -> None:
    """The step-17 disaster: believed thief at (3, 2), truth one cell off.

    Trapping (3, 2) with the wall standing makes the doorway unreachable
    from the left forever; a one-cell belief error then costs the game, not
    a stone. The seal cop must walk instead.
    """
    action = cop.decide(view((4, 2), (3, 2)))
    assert action.barrier != (3, 2)


def test_an_open_field_trap_is_still_taken(cop: SealPoliceBrain) -> None:
    """Away from the wall a missed trap costs one stone - still worth it."""
    action = cop.decide(view((5, 5), (5, 6), barriers=set()))
    assert action.barrier == (5, 6)


def test_the_seal_waits_for_a_stone(cop: SealPoliceBrain) -> None:
    """Quota empty: crossing is still right, sealing is impossible."""
    action = cop.decide(view((3, 4), (5, 5), left=0))
    assert action.barrier is None
