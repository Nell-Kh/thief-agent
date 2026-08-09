"""End-to-end tests of a whole mini-game driven through the SDK.

These are the M1 milestone checks: two agents move legally on the board, a
barrier beyond the quota is rejected, and coordinate overlap triggers a capture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.rules import IllegalBarrierError
from police_thief.sdk import SimulationSdk


@pytest.fixture
def sdk(config_dir: Path) -> SimulationSdk:
    """A simulation SDK loaded from the committed configuration."""
    return SimulationSdk.load("police", config_dir)


def test_sdk_exposes_the_signed_contract(sdk: SimulationSdk) -> None:
    assert sdk.contract.board.grid_size >= 7
    assert len(sdk.config_sha256) == 64
    assert sdk.role == "police"
    assert sdk.opponent_role() == "thief"


def test_a_scripted_pursuit_ends_in_capture(sdk: SimulationSdk) -> None:
    """The cop walks from the corner to the centre and catches the thief."""
    state = sdk.new_game()
    for _ in range(3):
        sdk.play_cop(state, "S")
        sdk.play_thief(state, "STAY")
        sdk.end_turn(state)
    for _ in range(3):
        if state.finished:
            break
        sdk.play_cop(state, "E")
        sdk.play_thief(state, "STAY")
        sdk.end_turn(state)
    assert state.finished
    assert state.outcome is not None
    assert state.outcome.event == "capture"
    assert sdk.points(state, "police") == 20
    assert sdk.points(state, "thief") == 5


def test_a_fleeing_thief_survives_to_the_threshold(sdk: SimulationSdk) -> None:
    """The cop stands still, so the thief runs out the clock and wins."""
    state = sdk.new_game()
    moves = ["N", "S", "E", "W"]
    turn = 0
    while not state.finished and turn < 200:
        sdk.play_cop(state, "STAY")
        move = next(
            (m for m in moves[turn % 4 :] + moves if m in sdk.legal_moves(state, "thief")),
            "STAY",
        )
        sdk.play_thief(state, move)
        sdk.end_turn(state)
        turn += 1
    assert state.outcome is not None
    assert state.outcome.event == "survival"
    assert sdk.points(state, "thief") == 10
    assert state.step == sdk.contract.movement.survival_threshold


def test_the_cop_can_wall_the_thief_into_a_corner(sdk: SimulationSdk) -> None:
    """Barriers are the cop's asymmetric advantage: they end the game too."""
    state = sdk.new_game()
    state.thief = (0, 6)
    state.cop = (1, 6)
    state.board.place_barrier((0, 5))
    sdk.play_cop(state, "STAY", barrier=(1, 6))
    assert state.outcome is not None
    assert state.outcome.event == "capture"


def test_barrier_options_shrink_as_cells_fill(sdk: SimulationSdk) -> None:
    state = sdk.new_game()
    before = sdk.barrier_options(state)
    sdk.play_cop(state, "STAY", barrier=before[0])
    assert len(sdk.barrier_options(state)) == len(before) - 1


def test_barrier_options_are_empty_once_the_quota_is_spent(sdk: SimulationSdk) -> None:
    state = sdk.new_game()
    state.barriers_used = sdk.contract.movement.max_barriers
    assert sdk.barrier_options(state) == []


def test_a_barrier_beyond_the_quota_is_refused(sdk: SimulationSdk) -> None:
    state = sdk.new_game()
    state.barriers_used = sdk.contract.movement.max_barriers
    with pytest.raises(IllegalBarrierError, match="quota exhausted"):
        sdk.play_cop(state, "STAY", barrier=(0, 1))


def test_legal_moves_never_include_a_diagonal(sdk: SimulationSdk) -> None:
    state = sdk.new_game()
    for role in ("police", "thief"):
        assert set(sdk.legal_moves(state, role)) <= {"N", "S", "E", "W", "STAY"}


def test_points_are_unavailable_before_the_game_ends(sdk: SimulationSdk) -> None:
    state = sdk.new_game()
    with pytest.raises(ValueError, match="has not finished"):
        sdk.points(state, "police")


def test_a_forfeit_ends_the_game_with_no_points(sdk: SimulationSdk) -> None:
    state = sdk.new_game()
    sdk.forfeit(state, "the opponent missed the deadline")
    assert sdk.outcome(state) is not None
    assert sdk.points(state, "police") == 0
    assert sdk.points(state, "thief") == 0


def test_the_running_game_reports_no_outcome(sdk: SimulationSdk) -> None:
    assert sdk.outcome(sdk.new_game()) is None


def test_series_totals_aggregate_mini_games(sdk: SimulationSdk) -> None:
    first = sdk.new_game()
    sdk.forfeit(first, "crash")
    second = sdk.new_game()
    second.step = sdk.contract.movement.survival_threshold - 1
    sdk.end_turn(second)
    outcomes = [first.outcome, second.outcome]
    assert SimulationSdk.series_totals([o for o in outcomes if o]) == (5, 10)


def test_both_peers_agree_on_the_contract_digest(config_dir: Path) -> None:
    police = SimulationSdk.load("police", config_dir)
    thief = SimulationSdk.load("thief", config_dir)
    assert police.config_sha256 == thief.config_sha256
