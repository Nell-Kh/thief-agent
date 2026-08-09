"""Tests for the brain contract, the class loader and the blind brains."""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.board import Board
from police_thief.domain.brain.base import BrainBase, BrainLoadError, BrainView, load_brain
from police_thief.domain.brain.blind import BlindPoliceBrain, BlindThiefBrain
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
    """A convenient hand-built brain view."""
    return BrainView(
        role=role,
        position=position,
        target=target,
        board=board or Board(contract.board.grid_size),
        barriers_left=barriers_left,
        step=0,
    )


def test_the_base_brain_refuses_to_decide(contract) -> None:
    with pytest.raises(NotImplementedError, match="must override"):
        BrainBase("police", contract).decide(view(contract))


def test_the_default_action_wraps_pick_move(contract) -> None:
    class OneTrick(BrainBase):
        """A brain that always plays the same move, isolating the wiring from strategy."""
        def _pick_move(self, _view: BrainView) -> str:
            """Always go east, whatever the board says."""
            return "E"

    action = OneTrick("police", contract).decide(view(contract))
    assert action.move == "E"
    assert action.barrier is None


def test_load_brain_builds_the_named_class(contract) -> None:
    brain = load_brain("police_thief.domain.brain.blind:BlindPoliceBrain", "police", contract)
    assert isinstance(brain, BlindPoliceBrain)
    assert brain.role == "police"


def test_load_brain_rejects_a_malformed_spec(contract) -> None:
    with pytest.raises(BrainLoadError, match="package.module:Class form"):
        load_brain("just-a-string", "police", contract)


def test_load_brain_rejects_a_missing_module(contract) -> None:
    with pytest.raises(BrainLoadError, match="cannot import brain module"):
        load_brain("no.such.module:Brain", "police", contract)


def test_load_brain_rejects_a_missing_class(contract) -> None:
    with pytest.raises(BrainLoadError, match="has no class"):
        load_brain("police_thief.domain.brain.blind:NoSuchBrain", "police", contract)


def test_load_brain_rejects_a_non_brain_class(contract) -> None:
    """Only BrainBase subclasses may drive an agent."""
    with pytest.raises(BrainLoadError, match="not a BrainBase subclass"):
        load_brain("police_thief.domain.board:Board", "police", contract)


def test_the_blind_cop_closes_the_true_distance(contract) -> None:
    brain = BlindPoliceBrain("police", contract)
    assert brain.decide(view(contract, position=(0, 0), target=(3, 0))).move == "S"


def test_the_blind_cop_routes_around_barriers(contract) -> None:
    board = Board(contract.board.grid_size, [(0, 1), (1, 1), (2, 1)])
    action = BlindPoliceBrain("police", contract).decide(
        view(contract, position=(0, 0), target=(0, 2), board=board)
    )
    assert action.move == "S"


def test_the_blind_cop_traps_an_adjacent_target(contract) -> None:
    """One step away with quota left: block the target's own cell and win."""
    action = BlindPoliceBrain("police", contract).decide(
        view(contract, position=(3, 2), target=(3, 3))
    )
    assert action.move == "STAY"
    assert action.barrier == (3, 3)


def test_the_blind_cop_cannot_trap_without_quota(contract) -> None:
    action = BlindPoliceBrain("police", contract).decide(
        view(contract, position=(3, 2), target=(3, 3), barriers_left=0)
    )
    assert action.barrier is None


def test_the_blind_cop_does_not_trap_diagonally(contract) -> None:
    action = BlindPoliceBrain("police", contract).decide(
        view(contract, position=(2, 2), target=(3, 3))
    )
    assert action.barrier is None


def test_the_blind_thief_flees_the_cop(contract) -> None:
    brain = BlindThiefBrain("thief", contract)
    action = brain.decide(view(contract, role="thief", position=(3, 3), target=(0, 0)))
    assert action.move == "S"
    assert action.barrier is None


def test_the_blind_thief_avoids_a_one_exit_pocket(contract) -> None:
    """Walking into a dead end hands the cop a one-barrier win.

    With a wall at (1, 0), the corner (0, 0) is the farthest cell from the cop
    - but it has a single exit, so the penalty makes the open flight win.
    """
    board = Board(contract.board.grid_size, [(1, 0)])
    action = BlindThiefBrain("thief", contract).decide(
        view(contract, role="thief", position=(0, 1), target=(3, 3), board=board)
    )
    assert action.move != "W"


def test_the_dead_end_penalty_is_a_bounded_trade_off(contract) -> None:
    """The penalty shaves a constant off the score - it is not a taboo."""
    from police_thief.domain.brain.blind import DEAD_END_PENALTY

    assert DEAD_END_PENALTY == 2


def test_both_blind_brains_are_deterministic(contract) -> None:
    """The same view must always produce the same move on both sides."""
    for brain in (BlindPoliceBrain("police", contract), BlindThiefBrain("thief", contract)):
        first = brain.decide(view(contract, role=brain.role))
        for _ in range(5):
            assert brain.decide(view(contract, role=brain.role)) == first
