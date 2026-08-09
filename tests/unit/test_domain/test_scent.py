"""Tests for the pheromone emission-decay model.

Every number asserted here is printed in the rulebook: the Figure 4 matrix, the
rho = 0.10 decay, the [0, 0.9] range, the ~6-7-turn readable trail, and the
lie-detection yardstick (1 - rho) * 0.9 = 0.81.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.scent import (
    ScentField,
    emission_delta,
    lock_payload,
    lock_sha256,
)
from police_thief.shared.config import ConfigManager


@pytest.fixture
def pheromones(config_dir: Path):
    """The locked emission and decay parameters."""
    return ConfigManager.load("police", config_dir).contract.pheromones


@pytest.fixture
def field(pheromones) -> ScentField:
    """An empty scent field over a 7x7 board."""
    return ScentField(board_size=7, config=pheromones)


def test_the_emission_matrix_matches_figure_4_digit_for_digit(pheromones) -> None:
    """Centre 0.90; ring by ring exactly as printed."""
    source = (3, 3)
    expected = {
        (0, 0): 0.90,
        (0, 1): 0.62,
        (1, 1): 0.42,
        (0, 2): 0.20,
        (1, 2): 0.14,
        (2, 2): 0.04,
    }
    for (d_row, d_col), value in expected.items():
        for sign_r, sign_c in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            cell = (source[0] + sign_r * d_row, source[1] + sign_c * d_col)
            assert emission_delta(pheromones, source, cell) == pytest.approx(value)
            mirrored = (source[0] + sign_r * d_col, source[1] + sign_c * d_row)
            assert emission_delta(pheromones, source, mirrored) == pytest.approx(value)


def test_emission_is_zero_outside_the_5x5_window(pheromones) -> None:
    assert emission_delta(pheromones, (3, 3), (3, 6)) == 0.0
    assert emission_delta(pheromones, (3, 3), (0, 0)) == 0.0


def test_a_fresh_field_is_quiet_everywhere(field: ScentField) -> None:
    assert field.intensity((3, 3)) == 0.0
    assert field.snapshot() == {}


def test_one_turn_writes_the_full_emission_footprint(field: ScentField) -> None:
    field.advance((3, 3))
    assert field.intensity((3, 3)) == pytest.approx(0.90)
    assert field.intensity((2, 3)) == pytest.approx(0.62)
    assert field.intensity((2, 2)) == pytest.approx(0.42)
    assert field.intensity((3, 5)) == pytest.approx(0.20)
    assert field.intensity((2, 5)) == pytest.approx(0.14)
    assert field.intensity((1, 5)) == pytest.approx(0.04)


def test_a_trail_decays_by_ten_percent_per_turn(field: ScentField) -> None:
    """After the agent leaves, the old centre keeps only (1 - rho) per turn."""
    field.advance((3, 3))
    field.advance((6, 6))
    assert field.intensity((3, 3)) == pytest.approx(0.9 * 0.9)


def test_the_lie_detection_yardstick_is_081(field: ScentField) -> None:
    """A path walked one turn ago must show about (1 - rho) * 0.9 = 0.81."""
    assert field.expected_fresh_trail() == pytest.approx(0.81)


def test_re_emission_holds_the_centre_at_the_ceiling(field: ScentField) -> None:
    """Figure 5: while the agent stays present the centre stays at 0.9."""
    for _ in range(5):
        field.advance((3, 3))
    assert field.intensity((3, 3)) == pytest.approx(0.9)


def test_intensity_never_exceeds_the_printed_range(field: ScentField) -> None:
    for _ in range(10):
        field.advance((3, 3))
    for value in field.snapshot().values():
        assert 0.0 < value <= 0.9 + 1e-9


def test_the_trail_stays_readable_for_about_six_to_seven_turns(field: ScentField) -> None:
    """Figure 5: the lone deposit crosses half-peak around turn seven."""
    field.advance((3, 3))
    trail = [0.9]
    for _ in range(8):
        field.advance((6, 6))
        trail.append(field.intensity((3, 3)))
    half_peak = 0.45
    assert trail[6] > half_peak
    assert trail[7] < half_peak


def test_emission_truncates_at_the_board_edge(pheromones) -> None:
    field = ScentField(board_size=7, config=pheromones)
    field.advance((0, 0))
    snapshot = field.snapshot()
    assert all(0 <= row < 7 and 0 <= col < 7 for row, col in snapshot)
    assert field.intensity((0, 0)) == pytest.approx(0.9)
    assert field.intensity((1, 1)) == pytest.approx(0.42)
    assert field.intensity((2, 2)) == pytest.approx(0.04)



def test_the_lock_is_the_registered_interop_document(pheromones) -> None:
    """The lock is the kit-registered multiplicative_book_v1 doc, verbatim -
    a home-grown field set would hash differently for the very same model."""
    from police_thief.shared.interop import SCENT_MODEL_SHA256

    payload = lock_payload(pheromones)
    assert payload["family"] == "scent_model"
    assert payload["name"] == "multiplicative_book_v1"
    assert payload["params"]["decay_rho"] == pytest.approx(0.10)
    assert payload["params"]["kernel"][2][2] == 0.9
    assert lock_sha256(pheromones) == SCENT_MODEL_SHA256


def test_two_fields_do_not_share_traces(pheromones) -> None:
    """Each side emits its own field; the cop's and the thief's never mix."""
    cop_field = ScentField(7, pheromones)
    thief_field = ScentField(7, pheromones)
    cop_field.advance((0, 0))
    assert thief_field.snapshot() == {}
