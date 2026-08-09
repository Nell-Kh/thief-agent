"""Tests for the arms-race brains: the wall cop and the open-field thief."""

from __future__ import annotations

import pytest

from police_thief.constants import MOVE_STAY, ROLE_POLICE, ROLE_THIEF
from police_thief.domain.board import Board
from police_thief.domain.brain.base import BrainView
from police_thief.domain.brain.enhanced import EnhancedThiefBrain
from police_thief.domain.brain.evade import EvadeThiefBrain, openness, worst_case_region
from police_thief.domain.brain.region import RegionPoliceBrain
from police_thief.domain.brain.wall import DOOR, WALL_COLUMN, WallPoliceBrain, wall_progress
from police_thief.domain.state import GameState
from police_thief.sdk import SimulationSdk
from police_thief.services.runtime import LocalMatchRunner
from police_thief.shared.config import ConfigManager


@pytest.fixture(scope="module")
def config() -> ConfigManager:
    """The loaded configuration under test."""
    return ConfigManager.load(ROLE_POLICE)


def view(board: Board, role: str, at, target, barriers_left: int = 10) -> BrainView:
    """A brain view for one board position, for either role."""
    return BrainView(role=role, position=at, target=target, board=board,
                     barriers_left=barriers_left, step=1)


def play(config: ConfigManager, cop_cls, thief_cls, cop_at, thief_at) -> GameState:
    """Run a full local match and return its outcome."""
    runner = LocalMatchRunner(
        SimulationSdk(config),
        police_brain=cop_cls(ROLE_POLICE, config.contract),
        thief_brain=thief_cls(ROLE_THIEF, config.contract),
    )
    state = GameState(board=Board(config.contract.board.grid_size), cop=cop_at, thief=thief_at)
    while not state.finished:
        runner.play_turn(state)
    return state


# --- the wall cop -----------------------------------------------------------


def test_the_opening_stone_goes_on_the_wall_column(config: ConfigManager) -> None:
    cop = WallPoliceBrain(ROLE_POLICE, config.contract)
    board = Board(7)
    action = cop.decide(view(board, ROLE_POLICE, (0, 2), (6, 6)))
    if action.barrier is not None:
        assert action.barrier[1] == WALL_COLUMN
    else:  # still walking to the build spot - the move must head for the wall
        assert action.move != MOVE_STAY


def test_the_door_is_never_walled(config: ConfigManager) -> None:
    state = play(config, WallPoliceBrain, EvadeThiefBrain, (0, 0), (6, 6))
    assert DOOR not in state.board.barriers


def test_the_trap_preempts_the_build(config: ConfigManager) -> None:
    cop = WallPoliceBrain(ROLE_POLICE, config.contract)
    board = Board(7)
    action = cop.decide(view(board, ROLE_POLICE, (5, 6), (6, 6)))
    assert action.move == MOVE_STAY and action.barrier == (6, 6)


def test_without_quota_the_wall_phase_yields_to_the_hunt(config: ConfigManager) -> None:
    cop = WallPoliceBrain(ROLE_POLICE, config.contract)
    board = Board(7)
    action = cop.decide(view(board, ROLE_POLICE, (0, 2), (6, 6), barriers_left=0))
    assert action.barrier is None
    assert action.move != MOVE_STAY


def test_wall_progress_counts_only_wall_stones() -> None:
    board = Board(7, [(0, 3), (4, 3), (2, 2)])
    assert wall_progress(board) == 2


# --- the open-field thief ---------------------------------------------------


def test_openness_is_distance_from_the_nearest_edge() -> None:
    board = Board(7)
    assert openness(board, (3, 3)) == 3
    assert openness(board, (0, 5)) == 0
    assert openness(board, (5, 1)) == 1


def test_worst_case_region_prices_the_cops_best_reply() -> None:
    board = Board(7)
    # Adjacent to the cop, the reply "step onto us" zeroes the safe region.
    assert worst_case_region(board, (3, 4), (3, 3)) == 0
    # Far away, even the best reply leaves a large region.
    assert worst_case_region(board, (6, 6), (0, 0)) > 10


def test_the_evader_never_steps_onto_the_believed_cop(config: ConfigManager) -> None:
    thief = EvadeThiefBrain(ROLE_THIEF, config.contract)
    board = Board(7, [(0, 1), (1, 1)])  # corridor: only exit leads to the cop
    move = thief._pick_move(view(board, ROLE_THIEF, (0, 0), (1, 0)))
    assert move == MOVE_STAY  # staying beats suicide


def test_the_evader_prefers_open_center_over_edges(config: ConfigManager) -> None:
    thief = EvadeThiefBrain(ROLE_THIEF, config.contract)
    move = thief._pick_move(view(Board(7), ROLE_THIEF, (0, 3), (0, 0)))
    assert move == "S"  # off the top edge: more sky, more distance, more region


# --- the arms race, pinned as regression facts ------------------------------


@pytest.mark.parametrize("starts", [((0, 0), (6, 6)), ((3, 0), (3, 6)), ((6, 3), (0, 3))])
def test_the_wall_cop_beats_the_strongest_evader(config: ConfigManager, starts) -> None:
    state = play(config, WallPoliceBrain, EvadeThiefBrain, *starts)
    assert state.outcome is not None and state.outcome.event == "capture"
    assert state.step <= 31  # margin under the 35-step ceiling
    assert state.barriers_used <= 9  # quota headroom


def test_the_evader_outlives_the_enhanced_thief_against_the_region_cop(
    config: ConfigManager,
) -> None:
    """The notebook's headline: blending beats priority-ordering for defense."""
    evader = play(config, RegionPoliceBrain, EvadeThiefBrain, (0, 0), (6, 6))
    enhanced = play(config, RegionPoliceBrain, EnhancedThiefBrain, (0, 0), (6, 6))
    assert evader.step > enhanced.step
