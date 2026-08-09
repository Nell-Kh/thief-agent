"""Tests for turn application and termination detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.engine import Action, Engine, stay, stay_and_block
from police_thief.domain.rules import IllegalBarrierError, IllegalMoveError
from police_thief.shared.config import ConfigManager


@pytest.fixture
def engine(config_dir: Path) -> Engine:
    """An engine bound to the committed contract."""
    return Engine(ConfigManager.load("police", config_dir).contract)


def test_a_new_game_starts_at_the_contract_positions(engine: Engine) -> None:
    state = engine.new_game()
    assert state.cop == (0, 0)
    assert state.thief == (3, 3)
    assert state.step == 0
    assert not state.finished


def test_a_move_relocates_the_agent(engine: Engine) -> None:
    state = engine.new_game()
    engine.apply(state, "police", Action(move="S"))
    assert state.cop == (1, 0)


def test_an_illegal_move_is_rejected(engine: Engine) -> None:
    state = engine.new_game()
    with pytest.raises(IllegalMoveError, match="leaves the board"):
        engine.apply(state, "police", Action(move="N"))


def test_moving_onto_the_thief_captures_him(engine: Engine) -> None:
    state = engine.new_game()
    state.cop = (2, 3)
    engine.apply(state, "police", Action(move="S"))
    assert state.finished
    assert state.outcome is not None
    assert state.outcome.event == "capture"
    assert state.outcome.cop_points == 20


def test_the_thief_walking_into_the_cop_is_also_a_capture(engine: Engine) -> None:
    state = engine.new_game()
    state.cop = (3, 4)
    engine.apply(state, "thief", Action(move="E"))
    assert state.outcome is not None
    assert state.outcome.event == "capture"


def test_a_barrier_on_the_thief_cell_captures_him(engine: Engine) -> None:
    """The trapping placement: blocking the thief's own cell ends the game."""
    state = engine.new_game()
    state.cop = (2, 3)
    engine.apply(state, "police", stay_and_block((3, 3)))
    assert state.outcome is not None
    assert state.outcome.event == "capture"
    assert "barrier" in state.outcome.reason


def test_a_thief_with_no_legal_step_is_captured(engine: Engine) -> None:
    state = engine.new_game()
    state.thief = (0, 6)
    state.cop = (1, 6)
    state.board.place_barrier((0, 5))
    engine.apply(state, "police", stay_and_block((1, 6)))
    assert state.outcome is not None
    assert state.outcome.event == "capture"
    assert "no legal move" in state.outcome.reason


def test_placing_a_barrier_consumes_the_quota(engine: Engine) -> None:
    state = engine.new_game()
    engine.apply(state, "police", stay_and_block((0, 1)))
    assert state.barriers_used == 1
    assert state.barriers_left(engine.contract) == 13


def test_the_barrier_quota_is_enforced(engine: Engine) -> None:
    state = engine.new_game()
    state.barriers_used = engine.contract.movement.max_barriers
    with pytest.raises(IllegalBarrierError, match="quota exhausted"):
        engine.apply(state, "police", stay_and_block((0, 1)))


def test_the_thief_may_not_place_barriers(engine: Engine) -> None:
    state = engine.new_game()
    with pytest.raises(IllegalBarrierError, match="only the cop"):
        engine.apply(state, "thief", stay_and_block((3, 4)))


def test_a_barrier_requires_forgoing_movement(engine: Engine) -> None:
    state = engine.new_game()
    with pytest.raises(IllegalBarrierError, match="without movement"):
        engine.apply(state, "police", Action(move="S", barrier=(1, 1)))


def test_a_barrier_placement_is_recorded_openly(engine: Engine) -> None:
    """The cop must declare every barrier and its exact location."""
    state = engine.new_game()
    engine.apply(state, "police", stay_and_block((0, 1)))
    assert any("barrier at (0, 1)" in line for line in state.history)


def test_a_full_turn_advances_the_clock(engine: Engine) -> None:
    state = engine.new_game()
    engine.play_turn(state, stay(), stay())
    assert state.step == 1


def test_the_thief_wins_at_the_survival_threshold(engine: Engine) -> None:
    state = engine.new_game()
    state.step = engine.contract.movement.survival_threshold - 1
    engine.end_turn(state)
    assert state.outcome is not None
    assert state.outcome.event == "survival"
    assert state.outcome.thief_points == 10


def test_the_clock_stops_once_the_game_is_over(engine: Engine) -> None:
    state = engine.new_game()
    engine.forfeit(state, "opponent disconnected")
    engine.end_turn(state)
    assert state.step == 0


def test_actions_are_ignored_after_the_game_ends(engine: Engine) -> None:
    state = engine.new_game()
    engine.forfeit(state, "crash")
    engine.apply(state, "police", Action(move="S"))
    assert state.cop == (0, 0)


def test_a_forfeit_is_a_technical_loss_for_both(engine: Engine) -> None:
    state = engine.new_game()
    engine.forfeit(state, "missed deadline")
    assert state.outcome is not None
    assert (state.outcome.cop_points, state.outcome.thief_points) == (0, 0)


def test_stay_builds_a_plain_stay_action() -> None:
    assert stay() == Action(move="STAY", barrier=None)
