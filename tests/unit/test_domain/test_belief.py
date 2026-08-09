"""Tests for the Bayesian belief map."""

from __future__ import annotations

import pytest

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board


@pytest.fixture
def board() -> Board:
    """An empty board for the belief map to spread over."""
    return Board(7)


@pytest.fixture
def belief(board: Board) -> BeliefMap:
    """A fresh belief map with a uniform prior."""
    return BeliefMap(board)


def _total(belief: BeliefMap) -> float:
    """Total probability mass, which must stay 1.0 under every update."""
    return sum(belief.snapshot().values())


def test_the_prior_is_uniform_over_free_cells(belief: BeliefMap) -> None:
    values = set(belief.snapshot().values())
    assert len(values) == 1
    assert _total(belief) == pytest.approx(1.0)


def test_barrier_cells_start_with_zero_belief() -> None:
    board = Board(7, [(3, 3)])
    belief = BeliefMap(board)
    assert belief.probability((3, 3)) == 0.0
    assert _total(belief) == pytest.approx(1.0)


def test_off_board_cells_have_zero_probability(belief: BeliefMap) -> None:
    assert belief.probability((9, 9)) == 0.0


def test_scent_evidence_concentrates_the_mass(belief: BeliefMap) -> None:
    belief.observe_scent({(1, 4): 0.81, (1, 3): 0.63})
    assert belief.argmax() == (1, 4)
    assert belief.probability((1, 4)) > belief.probability((1, 3))
    assert belief.probability((1, 3)) > belief.probability((5, 5))
    assert _total(belief) == pytest.approx(1.0)


def test_quiet_cells_keep_only_their_prior(belief: BeliefMap) -> None:
    before = belief.probability((6, 6))
    belief.observe_scent({(0, 0): 0.9})
    assert belief.probability((6, 6)) < before


def test_diffusion_spreads_mass_to_reachable_neighbours(board: Board) -> None:
    belief = BeliefMap(board)
    belief.observe_scent({(3, 3): 100.0})  # near-certainty at the centre
    belief.diffuse()
    for cell in [(2, 3), (4, 3), (3, 2), (3, 4), (3, 3)]:
        assert belief.probability(cell) > 0.01
    assert belief.probability((0, 0)) < 0.01


def test_diffusion_never_leaks_into_barriers() -> None:
    board = Board(7, [(2, 3)])
    belief = BeliefMap(board)
    belief.observe_scent({(3, 3): 100.0})
    belief.diffuse()
    assert belief.probability((2, 3)) == 0.0


def test_diffusion_respects_the_board_edge(board: Board) -> None:
    belief = BeliefMap(board)
    belief.observe_scent({(0, 0): 100.0})
    belief.diffuse()
    assert _total(belief) == pytest.approx(1.0)
    assert belief.probability((0, 1)) > 0.0
    assert belief.probability((1, 0)) > 0.0


def test_a_barrier_placed_mid_game_zeroes_that_cell(board: Board) -> None:
    """The board reference is live: new walls constrain the belief."""
    belief = BeliefMap(board)
    board.place_barrier((3, 3))
    belief.diffuse()
    assert belief.probability((3, 3)) == 0.0


def test_argmax_breaks_ties_deterministically(belief: BeliefMap) -> None:
    """A uniform map must yield the same argmax on both peers: row-major."""
    assert belief.argmax() == (0, 0)


def test_a_trusted_hint_boosts_its_region(belief: BeliefMap) -> None:
    south = [(row, col) for row in range(4, 7) for col in range(7)]
    belief.observe_region(south, factor=3.0)
    assert belief.argmax()[0] >= 4
    assert _total(belief) == pytest.approx(1.0)


def test_a_distrusted_hint_damps_its_region(belief: BeliefMap) -> None:
    north = [(row, col) for row in range(0, 3) for col in range(7)]
    belief.observe_region(north, factor=0.2)
    assert belief.argmax()[0] >= 3


def test_a_negative_factor_is_rejected(belief: BeliefMap) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        belief.observe_region([(0, 0)], factor=-1.0)


def test_a_failed_capture_claim_excludes_the_cell(belief: BeliefMap) -> None:
    """The thief truthfully answered "not caught" - that cell is ruled out."""
    belief.exclude((3, 3))
    assert belief.probability((3, 3)) == 0.0
    assert _total(belief) == pytest.approx(1.0)


def test_contradictory_evidence_resets_to_uniform(board: Board) -> None:
    """If every hypothesis dies, admit ignorance rather than crash."""
    belief = BeliefMap(board)
    for cell in list(belief.snapshot()):
        if cell != (6, 6):
            belief.exclude(cell)
    belief.exclude((6, 6))
    assert _total(belief) == pytest.approx(1.0)
    assert len([p for p in belief.snapshot().values() if p > 0]) == 49


def test_the_reference_update_order_reproduces_the_lie_example(board: Board) -> None:
    """Ch. 4's worked example: scent in the south-east, silence in the north.

    After folding the scent, the belief must point south-east regardless of a
    verbal claim of "north" - the trust layer will then damp the north further.
    """
    belief = BeliefMap(board)
    belief.diffuse()
    belief.observe_scent({(1, 4): 0.81, (1, 3): 0.63})
    assert belief.argmax() == (1, 4)


def test_reset_restores_the_uniform_prior(belief: BeliefMap) -> None:
    belief.observe_scent({(2, 2): 5.0})
    belief.reset()
    assert len(set(belief.snapshot().values())) == 1
