"""The M3 milestone: brains drive a whole game with no manual intervention.

Given a known target location, the agent computes and executes the shortest
path on its own - and the runner wires the brains in exactly where the design
demands, so swapping a brain never touches the engine.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.brain.base import BrainView
from police_thief.domain.brain.blind import BlindPoliceBrain
from police_thief.domain.brain.pathfind import distance
from police_thief.sdk import SimulationSdk
from police_thief.services.runtime import (
    LocalMatchRunner,
    configured_brain,
    runner_from_config,
)
from police_thief.shared.config import ConfigManager


@pytest.fixture
def config(config_dir: Path) -> ConfigManager:
    """The loaded configuration under test."""
    return ConfigManager.load("police", config_dir)


class StandStill(BlindPoliceBrain):
    """A target that never moves - for measuring pure pursuit."""

    def _decide_move(self, view: BrainView):
        """Always stay put, isolating the blind strategy from movement."""
        from police_thief.domain.engine import stay

        return stay()


def test_the_configured_brains_load_from_the_toml(config_dir: Path) -> None:
    """Each role's own TOML selects its competition brain."""
    police = configured_brain(ConfigManager.load("police", config_dir), "police")
    thief = configured_brain(ConfigManager.load("thief", config_dir), "thief")
    assert type(police).__name__ == "WallPoliceBrain"
    assert type(thief).__name__ == "EvadeThiefBrain"


def test_an_absent_strategy_section_falls_back_to_the_default(
    raw_shared, raw_private_police
) -> None:
    raw_private_police.pop("strategy", None)
    config = ConfigManager(raw_shared, raw_private_police, "police")
    assert configured_brain(config, "police") is not None


def test_the_cop_executes_a_shortest_path_with_no_intervention(
    config: ConfigManager,
) -> None:
    """M3: the pursuit takes exactly the true-path number of turns."""
    sdk = SimulationSdk(config)
    runner = LocalMatchRunner(
        sdk,
        police_brain=BlindPoliceBrain("police", config.contract),
        thief_brain=StandStill("thief", config.contract),
    )
    state = sdk.new_game()
    expected = distance(state.board, state.cop, state.thief)
    turns = 0
    while not state.finished:
        runner.play_turn(state)
        turns += 1
    assert state.outcome is not None
    assert state.outcome.event == "capture"
    assert turns == expected


def test_the_full_configured_match_runs_to_a_verdict(config: ConfigManager) -> None:
    state = runner_from_config(config).play()
    assert state.finished
    assert state.outcome is not None
    assert state.outcome.event in {"capture", "survival"}


def test_the_match_is_reproducible(config: ConfigManager) -> None:
    """Deterministic brains: the same configuration replays the same game."""
    first = runner_from_config(config).play()
    second = runner_from_config(config).play()
    assert first.outcome == second.outcome
    assert first.step == second.step
    assert first.history == second.history


def test_the_view_shows_only_what_the_role_may_know(config: ConfigManager) -> None:
    sdk = SimulationSdk(config)
    runner = runner_from_config(config)
    state = sdk.new_game()
    view = runner.view_for(state, "police")
    assert view.position == state.cop
    assert view.target == state.thief
    assert view.barriers_left == config.contract.movement.max_barriers


def test_the_safety_stop_bounds_a_test_match(config: ConfigManager) -> None:
    state = runner_from_config(config).play(max_turns=3)
    assert state.step <= 3
