"""Tests for the mini-game state container."""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.board import Board
from police_thief.domain.scoring import capture
from police_thief.domain.state import GameState
from police_thief.shared.config import ConfigManager


@pytest.fixture
def contract(config_dir: Path):
    """The signed contract these tests enforce physics against."""
    return ConfigManager.load("police", config_dir).contract


def test_state_starts_from_the_contract_setup(contract) -> None:
    state = GameState.from_contract(contract)
    assert state.cop == contract.board.cop_start
    assert state.thief == contract.board.thief_start
    assert state.board.size == contract.board.grid_size


def test_a_fresh_state_is_unfinished(contract) -> None:
    assert not GameState.from_contract(contract).finished


def test_a_state_with_an_outcome_is_finished(contract) -> None:
    state = GameState.from_contract(contract)
    state.outcome = capture(contract.scoring)
    assert state.finished


def test_position_of_resolves_each_role(contract) -> None:
    state = GameState.from_contract(contract)
    assert state.position_of("police") == (0, 0)
    assert state.position_of("thief") == (3, 3)


def test_position_of_rejects_an_unknown_role(contract) -> None:
    with pytest.raises(ValueError, match="unknown role"):
        GameState.from_contract(contract).position_of("burglar")


def test_set_position_moves_the_named_role(contract) -> None:
    state = GameState.from_contract(contract)
    state.set_position("police", (2, 2))
    state.set_position("thief", (5, 5))
    assert (state.cop, state.thief) == ((2, 2), (5, 5))


def test_set_position_rejects_an_unknown_role(contract) -> None:
    with pytest.raises(ValueError, match="unknown role"):
        GameState.from_contract(contract).set_position("burglar", (0, 0))


def test_overlapping_detects_a_shared_cell(contract) -> None:
    state = GameState.from_contract(contract)
    assert not state.overlapping()
    state.cop = state.thief
    assert state.overlapping()


def test_barriers_left_counts_down_from_the_quota(contract) -> None:
    state = GameState.from_contract(contract)
    assert state.barriers_left(contract) == contract.movement.max_barriers
    state.barriers_used = 3
    assert state.barriers_left(contract) == contract.movement.max_barriers - 3


def test_barriers_left_never_goes_negative(contract) -> None:
    state = GameState.from_contract(contract)
    state.barriers_used = contract.movement.max_barriers + 5
    assert state.barriers_left(contract) == 0


def test_history_records_narrative_entries(contract) -> None:
    state = GameState.from_contract(contract)
    state.record("step 0: police plays S")
    assert state.history == ["step 0: police plays S"]


def test_states_do_not_share_a_board(contract) -> None:
    """Two mini-games must never leak barriers into each other."""
    first = GameState.from_contract(contract)
    second = GameState.from_contract(contract)
    first.board.place_barrier((1, 1))
    assert not second.board.is_barrier((1, 1))


def test_a_state_can_be_built_by_hand(contract) -> None:
    state = GameState(board=Board(5), cop=(0, 0), thief=(4, 4))
    assert state.board.size == 5
    assert not state.finished
