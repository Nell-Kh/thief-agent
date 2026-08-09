"""Tests for the belief-driven competition brains."""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.board import Board
from police_thief.domain.brain.base import BrainView
from police_thief.domain.brain.enhanced import (
    BARRIER_RESERVE,
    EnhancedPoliceBrain,
    EnhancedThiefBrain,
)
from police_thief.shared.config import ConfigManager


@pytest.fixture
def contract(config_dir: Path):
    """The signed contract these tests enforce physics against."""
    return ConfigManager.load("police", config_dir).contract


def view(
    contract,
    *,
    role: str = "police",
    position=(0, 0),
    target=(3, 3),
    board: Board | None = None,
    barriers_left: int = 14,
) -> BrainView:
    """A brain view built for one specific board position."""
    return BrainView(
        role=role,
        position=position,
        target=target,
        board=board or Board(contract.board.grid_size),
        barriers_left=barriers_left,
        step=0,
    )


def test_the_enhanced_cop_still_traps_an_adjacent_target(contract) -> None:
    action = EnhancedPoliceBrain("police", contract).decide(
        view(contract, position=(3, 2), target=(3, 3))
    )
    assert action.move == "STAY"
    assert action.barrier == (3, 3)


def test_the_enhanced_cop_pinches_an_escape_corridor_when_close(contract) -> None:
    """Two true steps away: seal the target's widest door instead of stepping."""
    action = EnhancedPoliceBrain("police", contract).decide(
        view(contract, position=(3, 1), target=(3, 3))
    )
    assert action.move == "STAY"
    assert action.barrier == (3, 2)


def test_the_pinch_respects_the_barrier_reserve(contract) -> None:
    """With only the reserve left, keep the barriers for the endgame trap."""
    action = EnhancedPoliceBrain("police", contract).decide(
        view(contract, position=(3, 1), target=(3, 3), barriers_left=BARRIER_RESERVE)
    )
    assert action.barrier is None
    assert action.move != "STAY"


def test_the_cop_pursues_when_the_target_is_far(contract) -> None:
    action = EnhancedPoliceBrain("police", contract).decide(
        view(contract, position=(0, 0), target=(6, 6))
    )
    assert action.barrier is None
    assert action.move in {"S", "E"}


def test_the_pinch_only_seals_cells_in_placement_range(contract) -> None:
    """A pinch must still obey the barrier law: within one step of the cop."""
    brain = EnhancedPoliceBrain("police", contract)
    for position in [(3, 1), (2, 2), (4, 2)]:
        action = brain.decide(view(contract, position=position, target=(3, 3)))
        if action.barrier is not None:
            row_gap = abs(action.barrier[0] - position[0])
            col_gap = abs(action.barrier[1] - position[1])
            assert row_gap + col_gap <= 1


def test_the_enhanced_thief_flees_like_the_blind_one(contract) -> None:
    action = EnhancedThiefBrain("thief", contract).decide(
        view(contract, role="thief", position=(3, 3), target=(0, 0))
    )
    assert action.move == "S"


def test_the_enhanced_thief_refuses_a_cell_beside_the_cop(contract) -> None:
    """Standing next to the cop invites the trapping placement."""
    board = Board(contract.board.grid_size)
    action = EnhancedThiefBrain("thief", contract).decide(
        view(contract, role="thief", position=(2, 3), target=(4, 3), board=board)
    )
    landing = {
        "N": (1, 3),
        "S": (3, 3),
        "E": (2, 4),
        "W": (2, 2),
        "STAY": (2, 3),
    }[action.move]
    gap = abs(landing[0] - 4) + abs(landing[1] - 3)
    assert gap > 1


def test_both_enhanced_brains_are_deterministic(contract) -> None:
    for brain in (
        EnhancedPoliceBrain("police", contract),
        EnhancedThiefBrain("thief", contract),
    ):
        first = brain.decide(view(contract, role=brain.role))
        for _ in range(5):
            assert brain.decide(view(contract, role=brain.role)) == first


def test_the_configured_toml_selects_the_competition_brains(config_dir: Path) -> None:
    """Police: the wall cop; thief: the open-field evader (phase-8 arms race)."""
    from police_thief.domain.brain.evade import EvadeThiefBrain
    from police_thief.domain.brain.wall import WallPoliceBrain
    from police_thief.services.runtime import configured_brain

    police = configured_brain(ConfigManager.load("police", config_dir), "police")
    thief = configured_brain(ConfigManager.load("thief", config_dir), "thief")
    assert isinstance(police, WallPoliceBrain)
    assert isinstance(thief, EvadeThiefBrain)
