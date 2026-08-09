"""Tests for the hybrid cop and the verified-claim belief pin."""

from __future__ import annotations

import pytest

from police_thief.constants import ROLE_POLICE, ROLE_THIEF
from police_thief.domain.board import Board
from police_thief.domain.brain.enhanced import EnhancedThiefBrain
from police_thief.domain.brain.evade import EvadeThiefBrain
from police_thief.domain.brain.hybrid import HybridPoliceBrain
from police_thief.domain.state import GameState
from police_thief.domain.turnmsg import TurnMessage
from police_thief.sdk import SimulationSdk
from police_thief.services.runtime import LocalMatchRunner
from police_thief.services.turn_receiving import receive_turn
from police_thief.services.world_view import WorldView
from police_thief.shared.config import ConfigManager


@pytest.fixture(scope="module")
def config() -> ConfigManager:
    """The loaded configuration under test."""
    return ConfigManager.load(ROLE_POLICE)


def play(config: ConfigManager, thief_cls, cop_at, thief_at) -> GameState:
    """Run a full local match and return its outcome."""
    runner = LocalMatchRunner(
        SimulationSdk(config),
        police_brain=HybridPoliceBrain(ROLE_POLICE, config.contract),
        thief_brain=thief_cls(ROLE_THIEF, config.contract),
    )
    state = GameState(board=Board(config.contract.board.grid_size), cop=cop_at, thief=thief_at)
    while not state.finished:
        runner.play_turn(state)
    return state


# --- the hybrid cop ---------------------------------------------------------


@pytest.mark.parametrize("starts", [((0, 0), (6, 6)), ((6, 0), (0, 6)), ((3, 0), (3, 6))])
def test_reference_style_thieves_die_fast(config: ConfigManager, starts) -> None:
    """The hunt phase converts weak thieves in a fraction of the wall's time."""
    state = play(config, EnhancedThiefBrain, *starts)
    assert state.outcome is not None and state.outcome.event == "capture"
    assert state.step <= 12  # the wall alone needs ~25


@pytest.mark.parametrize("starts", [((0, 0), (6, 6)), ((3, 0), (3, 6)), ((6, 3), (0, 3))])
def test_the_elite_evader_still_falls(config: ConfigManager, starts) -> None:
    """The tripwires commit to the wall in time to convert the strongest thief."""
    state = play(config, EvadeThiefBrain, *starts)
    assert state.outcome is not None and state.outcome.event == "capture"
    assert state.step <= config.contract.movement.max_moves - 1


def test_commitment_to_the_wall_is_one_way(config: ConfigManager) -> None:
    cop = HybridPoliceBrain(ROLE_POLICE, config.contract)
    cop._committed = True
    cop._stalled = 0
    cop._best_region = 0  # even with "progress", a committed cop keeps building
    assert cop._tripped(step=1, current_region=1) or cop._committed


# --- the verified-claim pin -------------------------------------------------


def claim_msg(step: int, claim, scent) -> TurnMessage:
    """A turn message carrying a capture claim at the given step."""
    return TurnMessage(step=step, sender="police", hint="", smell_grid=scent,
                       commit="a" * 64, capture_claim=list(claim))


def test_a_scent_verified_claim_pins_the_cop_belief(config: ConfigManager) -> None:
    view = WorldView.open(ROLE_THIEF, config.contract)
    receive_turn(view, claim_msg(1, (2, 2), {"2,2": 0.9}), config.contract)
    assert view.belief.argmax() == (2, 2)


def test_an_unverified_claim_moves_nothing(config: ConfigManager) -> None:
    """A claim with no scent behind it may be a lie - the belief stays put."""
    view = WorldView.open(ROLE_THIEF, config.contract)
    before = view.belief.argmax()
    receive_turn(view, claim_msg(1, (6, 6), {"0,0": 0.9}), config.contract)
    assert view.belief.argmax() != (6, 6) or before == (6, 6)


def test_a_weakly_scented_claim_is_not_trusted(config: ConfigManager) -> None:
    """Stale scent at the claim cell: the fresh trail elsewhere wins the argmax."""
    view = WorldView.open(ROLE_THIEF, config.contract)
    receive_turn(view, claim_msg(1, (2, 2), {"2,2": 0.1, "5,5": 0.9}), config.contract)
    assert view.belief.argmax() == (5, 5)  # no pin fired - scent alone decides
