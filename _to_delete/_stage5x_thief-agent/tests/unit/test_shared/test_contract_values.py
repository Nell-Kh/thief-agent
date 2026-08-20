"""Guard tests on the shipped ``config/game.json``.

Every value asserted here is a binding value of the rulebook's Mandatory
Parameters Table (Appendix F), so an accidental edit to the contract fails the
suite. Parameters with **fixed** status are asserted for equality; parameters
with **minimum** status are asserted with ``>=`` because they may only ever be
raised by mutual agreement, never lowered.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.shared.config import ConfigManager


@pytest.fixture
def contract(config_dir: Path):
    """The signed contract these tests enforce physics against."""
    return ConfigManager.load("police", config_dir).contract


def test_board_matches_the_binding_parameters(contract) -> None:
    board = contract.board
    assert board.grid_size >= 7          # minimum - may only be raised
    assert board.num_agents == 2         # fixed
    assert board.thief_start == (3, 3)
    assert board.cop_start == (0, 0)
    assert board.axis_origin_corner == "top-left"
    assert board.axis_start_index == 0


def test_movement_matches_the_binding_parameters(contract) -> None:
    movement = contract.movement
    assert set(movement.move_set) == {"N", "S", "E", "W", "STAY"}   # fixed
    assert movement.max_barriers >= 14                              # minimum
    assert movement.max_moves >= 35                                 # minimum
    assert movement.survival_threshold >= 35                        # minimum


def test_scoring_matches_the_fixed_parameters(contract) -> None:
    """All scoring values carry 'fixed' status: deviation disqualifies."""
    scoring = contract.scoring
    assert (scoring.capture_cop, scoring.capture_thief) == (20, 5)
    assert (scoring.survival_cop, scoring.survival_thief) == (5, 10)
    assert (scoring.tie_score, scoring.technical_loss) == (2, 0)


def test_pheromones_match_the_fixed_parameters(contract) -> None:
    pheromones = contract.pheromones
    assert pheromones.center_intensity == pytest.approx(0.9)
    assert pheromones.decay == pytest.approx(0.10)
    assert pheromones.grid_size == 5


def test_league_parameters_match_the_binding_table(contract) -> None:
    network = contract.network
    assert network.num_games == 6                # fixed: mini-games per series
    assert network.diversity_reward == 10        # fixed
    assert network.min_games_to_pass == 2        # fixed
    assert network.max_games_per_team == 10      # fixed
    # NEGOTIATION status (PRD_p2p_mcp table), not fixed: 60/30 are the
    # rulebook defaults and rule #12 allows RAISING them by mutual agreement,
    # never lowering. Pinned as equality until 2026-08-20, which would have
    # failed the suite for a lawfully negotiated contract - uoh-ay26 play
    # 180/120 and we agreed to match them.
    assert network.watchdog_timeout_sec >= 60       # negotiable upward
    assert network.response_timeout_sec >= 30       # negotiable upward
    assert network.token_budget_per_series >= 200000


def test_rate_limiter_meets_the_minimum_thresholds(contract) -> None:
    limiter = contract.rate_limiter
    assert limiter.requests_per_minute >= 30
    assert limiter.concurrent_requests >= 2
    assert limiter.retry_backoff_sec >= 5
    assert limiter.max_retries >= 3
    assert limiter.queue_depth >= 100


def test_hint_word_cap_and_arena_are_exposed(contract) -> None:
    assert contract.world.hint_max_words == 15
    assert isinstance(contract.world.map_area, str)
