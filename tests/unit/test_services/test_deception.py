"""Tests for the deception controller and the vague hint style."""

from __future__ import annotations

import pytest

from police_thief.constants import INTENT_LIE, INTENT_TRUTH
from police_thief.domain.trust import parse_directions
from police_thief.infra.llm.base import STYLE_DIRECTIONAL, STYLE_VAGUE, HintRequest
from police_thief.infra.llm.template import TemplateProvider
from police_thief.services.deception import (
    MODE_HONEST,
    MODE_MISLEAD,
    MODE_VAGUE,
    DeceptionPolicy,
)


def request(step: int, style: str, intent: str = INTENT_TRUTH) -> HintRequest:
    """A hint request carrying the intent under test."""
    return HintRequest(role="thief", intent=intent, true_direction="N",
                       map_area="New York", max_words=15, step=step, style=style)


# --- the vague style --------------------------------------------------------


def test_vague_hints_contain_no_verifiable_geometry() -> None:
    """Across every pattern in the pool: nothing our own parser can read."""
    provider = TemplateProvider()
    for step in range(1, 11):
        hint = provider.generate(request(step, STYLE_VAGUE))
        assert parse_directions(hint) == frozenset(), hint


def test_directional_hints_still_carry_geometry() -> None:
    provider = TemplateProvider()
    hint = provider.generate(request(1, STYLE_DIRECTIONAL))
    assert parse_directions(hint) == frozenset({"N"})


def test_a_vague_request_claims_no_direction_even_when_lying() -> None:
    assert request(1, STYLE_VAGUE, INTENT_LIE).claimed_direction() is None


def test_an_unknown_style_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown hint style"):
        request(1, "cryptic")


# --- the policy -------------------------------------------------------------


def test_fixed_modes_ignore_the_claims() -> None:
    honest = DeceptionPolicy(MODE_HONEST)
    mislead = DeceptionPolicy(MODE_MISLEAD)
    vague = DeceptionPolicy(MODE_VAGUE)
    for gap in (0, 0, 0):
        for policy in (honest, mislead, vague):
            policy.observe_claim_gap(gap)
    assert honest.choose() == (INTENT_TRUTH, STYLE_DIRECTIONAL)
    assert mislead.choose() == (INTENT_LIE, STYLE_DIRECTIONAL)
    assert vague.choose() == (INTENT_TRUTH, STYLE_VAGUE)


def test_adaptive_starts_misleading_before_any_claims() -> None:
    assert DeceptionPolicy().choose() == (INTENT_LIE, STYLE_DIRECTIONAL)


def test_adaptive_goes_vague_when_claims_land_close() -> None:
    policy = DeceptionPolicy(tracked_gap=2, window=3)
    for gap in (5, 1, 2, 1):  # recent window mean = (1+2+1)/3 <= 2
        policy.observe_claim_gap(gap)
    assert policy.opponent_sees_us
    assert policy.choose() == (INTENT_TRUTH, STYLE_VAGUE)


def test_adaptive_keeps_lying_while_claims_wander() -> None:
    policy = DeceptionPolicy(tracked_gap=2, window=3)
    for gap in (1, 6, 5, 6):  # the early hit ages out of the window
        policy.observe_claim_gap(gap)
    assert not policy.opponent_sees_us
    assert policy.choose() == (INTENT_LIE, STYLE_DIRECTIONAL)


def test_an_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="deception mode"):
        DeceptionPolicy("gaslight")
