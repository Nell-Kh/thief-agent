"""Tests for locating an opponent by inverting the scent model."""

from __future__ import annotations

import random

import pytest

from police_thief.domain.emitter import ACCEPT_RATIO, locate_emitter, observed_ceiling
from police_thief.domain.scent import ScentField
from police_thief.shared.config import ConfigManager

BOARD = 7
CELLS = [(row, col) for row in range(BOARD) for col in range(BOARD)]


def chebyshev_field(path, decay):
    """NajAmjad's ``subtractive_chebyshev_v1``, replayed over a path.

    Rings 0.90/0.60/0.30 by Chebyshev distance, accumulated with the same
    ``(1 - rho) * tau + delta`` update we use and NOT clamped - which is the
    lawful reading this module had to be taught to read.
    """
    frames, field = [], {}
    for source in path:
        deposit = {
            cell: round(0.9 * max(0.0, 1 - max(abs(cell[0] - source[0]),
                                               abs(cell[1] - source[1])) / 3.0), 2)
            for cell in CELLS
        }
        field = {
            cell: field.get(cell, 0.0) * (1 - decay) + deposit[cell]
            for cell in CELLS
            if field.get(cell, 0.0) * (1 - decay) + deposit[cell] > 0
        }
        frames.append(field)
    return frames


@pytest.fixture(scope="module")
def pheromones():
    """The registered model's constants."""
    return ConfigManager.load("police").contract.pheromones


def test_the_peak_is_a_plateau_but_the_fit_is_exact(pheromones) -> None:
    """The finding that motivated this module, pinned as a measurement.

    After a few moves the transmitted field holds many cells at the ceiling,
    so an argmax answers with whatever the tie-break orders first. The fit
    recovers the true emitter on every step of a moving path.
    """
    field = ScentField(7, pheromones)
    previous: dict = {}
    path = [(3, 3), (3, 4), (3, 5), (4, 5), (4, 4), (5, 4), (5, 5), (6, 5)]
    plateau_seen = 0
    for cell in path:
        field.advance(cell)
        current = field.snapshot()
        ceiling = max(current.values())
        at_ceiling = [key for key, value in current.items() if value >= ceiling - 1e-9]
        plateau_seen = max(plateau_seen, len(at_ceiling))
        if previous:
            assert locate_emitter(previous, current, pheromones, 7) == cell
        previous = current
    assert plateau_seen > 1, "no plateau means this test proves nothing"


def test_the_first_field_has_nothing_to_difference(pheromones) -> None:
    field = ScentField(7, pheromones)
    field.advance((2, 2))
    assert locate_emitter(None, field.snapshot(), pheromones, 7) is None


def test_an_empty_field_locates_nothing(pheromones) -> None:
    assert locate_emitter({}, {}, pheromones, 7) is None


def test_a_stationary_emitter_is_still_found(pheromones) -> None:
    """Standing still saturates the centre; the fit must not drift off it."""
    field = ScentField(7, pheromones)
    field.advance((1, 5))
    previous = field.snapshot()
    field.advance((1, 5))
    assert locate_emitter(previous, field.snapshot(), pheromones, 7) == (1, 5)


def test_a_peer_that_does_not_clamp_is_read_exactly(pheromones) -> None:
    """A foreign but lawful kernel, located on every step of a moving path.

    NajAmjad (2026-08-16) read chapter 4 without an upper clamp, so their
    accumulation runs past our ``center_intensity``. Predicting under OUR clamp
    against THEIR field is wrong at every saturated cell by an unbounded
    amount: it located 7 of 11 steps, and the residual it left made a wrong
    candidate score better than the right one, which would have made any
    fit-quality guard reject the good answer. Reading the ceiling off the
    arriving field instead restores all 11.
    """
    path = [(3, 3), (3, 4), (2, 4), (2, 5), (1, 5), (1, 4),
            (0, 4), (0, 3), (1, 3), (2, 3), (2, 2), (3, 2)]
    frames = chebyshev_field(path, pheromones.decay)
    assert max(frames[-1].values()) > pheromones.center_intensity, "no clamp broken, no test"
    located = [
        locate_emitter(frames[i - 1], frames[i], pheromones, BOARD) == path[i]
        for i in range(1, len(path))
    ]
    assert all(located), f"located only {sum(located)} of {len(located)}"


def test_the_observed_ceiling_prefers_evidence_over_assumption(pheromones) -> None:
    ours = pheromones.center_intensity
    assert observed_ceiling({(0, 0): ours}, ours) == ours
    assert observed_ceiling({(0, 0): ours + 0.5}, ours) == float("inf")
    assert observed_ceiling({}, ours) == ours


def test_a_field_no_emission_explains_is_refused_rather_than_guessed(pheromones) -> None:
    """Noise must return None, not a confident phantom.

    The pin this feeds is deliberately heavy, so a wrong answer is worse than
    no answer. An unreadable field is exactly where the old code was most
    dangerous: it always returned its argmin, however badly that fitted.
    """
    rng = random.Random(7)
    previous = {cell: rng.random() * 0.9 for cell in CELLS}
    current = {cell: rng.random() * 0.9 for cell in CELLS}
    assert locate_emitter(previous, current, pheromones, BOARD) is None


def test_an_unchanged_field_carries_no_emission_to_find(pheromones) -> None:
    """Decay alone explains it perfectly, so there is no emitter to report."""
    field = ScentField(7, pheromones)
    field.advance((4, 2))
    previous = field.snapshot()
    decayed = {cell: value * (1 - pheromones.decay) for cell, value in previous.items()}
    assert locate_emitter(previous, decayed, pheromones, BOARD) is None


def test_the_acceptance_threshold_sits_between_the_measured_populations() -> None:
    """The calibration, pinned: 0.13 (lawful foreign kernel) < 0.5 < 0.82 (noise)."""
    assert 0.15 < ACCEPT_RATIO < 0.80
