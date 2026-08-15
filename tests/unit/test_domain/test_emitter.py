"""Tests for locating an opponent by inverting the scent model."""

from __future__ import annotations

import pytest

from police_thief.domain.emitter import locate_emitter
from police_thief.domain.scent import ScentField
from police_thief.shared.config import ConfigManager


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
