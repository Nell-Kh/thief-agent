"""Tests for hint parsing, region mapping and the lie-detection trust model."""

from __future__ import annotations

import pytest

from police_thief.domain.trust import (
    INITIAL_TRUST,
    TrustModel,
    parse_directions,
    region_for,
)

YARDSTICK = 0.81  # (1 - rho) * 0.9 under the binding parameters


@pytest.fixture
def model() -> TrustModel:
    """A trust model calibrated to the one-turn-old trail yardstick."""
    return TrustModel(fresh_trail=YARDSTICK, board_size=7)


def test_plain_cardinal_words_are_parsed() -> None:
    assert parse_directions("I moved north") == frozenset({"N"})
    assert parse_directions("heading south now") == frozenset({"S"})


def test_compound_directions_are_parsed() -> None:
    assert parse_directions("slipping north-east past the docks") == {"N", "E"}


def test_colloquial_directions_are_parsed() -> None:
    assert parse_directions("going up and to the left") == {"N", "W"}


def test_landmark_hints_carry_no_geometry() -> None:
    assert parse_directions("slipping past Times Square") == frozenset()


def test_the_word_cap_does_not_break_parsing() -> None:
    hint = "somewhere far in the cold northern alleys beyond the old market wall tonight friend"
    assert len(hint.split()) <= 15
    assert parse_directions(hint) == {"N"}


def test_a_single_direction_maps_to_a_half_board() -> None:
    north = region_for(frozenset({"N"}), 7)
    assert all(row <= 2 for row, _ in north)
    assert len(north) == 21


def test_compound_directions_intersect_to_a_quadrant() -> None:
    quadrant = region_for(frozenset({"S", "E"}), 7)
    assert all(row >= 4 and col >= 4 for row, col in quadrant)
    assert len(quadrant) == 9


def test_no_directions_map_to_no_region() -> None:
    assert region_for(frozenset(), 7) == frozenset()


def test_trust_starts_neutral(model: TrustModel) -> None:
    """Before any evidence, an opponent is neither believed nor doubted."""
    assert model.trust == INITIAL_TRUST


def test_the_chapter_4_lie_is_caught(model: TrustModel) -> None:
    """Claimed north while the fresh trail visibly walked south."""
    model.appraise("warming up", {(4, 5): 0.81, (3, 5): 0.63})  # baseline turn
    appraisal = model.appraise("I moved north", {(5, 5): 0.81, (4, 5): 0.63})
    assert appraisal.verdict == "contradicted"
    assert appraisal.factor < 1.0
    assert model.trust < INITIAL_TRUST


def test_a_truthful_hint_is_corroborated(model: TrustModel) -> None:
    """The fresh trail moved exactly where the opponent said it walked."""
    model.appraise("warming up", {(2, 4): 0.81, (3, 4): 0.63})  # baseline turn
    appraisal = model.appraise("I moved north", {(1, 4): 0.81, (2, 4): 0.63})
    assert appraisal.verdict == "corroborated"
    assert appraisal.factor > 1.0
    assert model.trust > INITIAL_TRUST


def test_a_landmark_hint_changes_nothing(model: TrustModel) -> None:
    appraisal = model.appraise("slipping past Times Square", {(5, 5): 0.81})
    assert appraisal.verdict == "uninformative"
    assert appraisal.factor == 1.0
    assert model.trust == INITIAL_TRUST


def test_weak_evidence_stays_uninformative(model: TrustModel) -> None:
    """Faint scent everywhere: neither confirmation nor contradiction."""
    scent = {(1, 1): 0.10, (5, 5): 0.12}
    appraisal = model.appraise("I moved north", scent)
    assert appraisal.verdict == "uninformative"
    assert model.trust == INITIAL_TRUST


def test_repeated_lies_erode_trust_toward_zero(model: TrustModel) -> None:
    """Six turns of walking south while claiming north every single time."""
    model.appraise("warming up", {(0, 3): 0.81})
    for row in range(1, 7):
        model.appraise("heading north", {(row, 3): 0.81})
    assert model.trust < 0.1


def test_repeated_truth_builds_trust_toward_one(model: TrustModel) -> None:
    """Six turns of walking north, honestly announced every single time."""
    model.appraise("warming up", {(6, 3): 0.81})
    for row in range(5, -1, -1):
        model.appraise("heading north", {(row, 3): 0.81})
    assert model.trust > 0.9


def test_a_liar_earns_weaker_damping_credibility(model: TrustModel) -> None:
    """The lower the trust, the harder a contradicted region is damped."""
    model.appraise("warming up", {(0, 5): 0.81})
    first = model.appraise("north", {(1, 5): 0.81}).factor
    for row in range(2, 6):
        model.appraise("north", {(row, 5): 0.81})
    later = model.appraise("north", {(6, 5): 0.81}).factor
    assert later < first < 1.0


def test_the_appraisal_region_matches_the_claim(model: TrustModel) -> None:
    appraisal = model.appraise("running south-west", {(1, 1): 0.81})
    assert appraisal.directions == {"S", "W"}
    assert all(row >= 4 and col <= 2 for row, col in appraisal.region)


def test_appraisals_are_deterministic(model: TrustModel) -> None:
    """The same hint and the same scent must always yield the same appraisal."""
    scent = {(5, 5): 0.81}
    first = TrustModel(YARDSTICK, 7).appraise("north", scent)
    second = TrustModel(YARDSTICK, 7).appraise("north", scent)
    assert first == second
