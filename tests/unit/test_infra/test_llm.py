"""Tests for the verbal layer: template, chain wrappers and the token ledger."""

from __future__ import annotations

import pytest

from police_thief.infra.llm.base import HintProvider, HintRequest, ProviderError, clip_words
from police_thief.infra.llm.chain import (
    BudgetGuard,
    FallbackProvider,
    ThrottledProvider,
    build_provider,
)
from police_thief.infra.llm.ledger import TokenLedger
from police_thief.infra.llm.template import TemplateProvider


def request(step: int = 0, intent: str = "truth", direction: str | None = "N") -> HintRequest:
    """A hint request with the fields every provider reads."""
    return HintRequest(
        role="thief",
        intent=intent,
        true_direction=direction,
        map_area="New York",
        max_words=15,
        step=step,
    )


class Exploding(HintProvider):
    """A provider that always fails, so the fallback is what gets tested."""
    name = "exploding"

    def generate(self, _request: HintRequest) -> str:
        """Produce the canned provider response for this test."""
        raise ProviderError("boom")


class Canned(HintProvider):
    """A provider returning a fixed string, so assertions can be exact."""
    name = "canned"

    def generate(self, _request: HintRequest) -> str:
        """Produce the canned provider response for this test."""
        return "a canned hint"


def test_an_unknown_intent_is_rejected() -> None:
    with pytest.raises(ValueError, match="intent must be one of"):
        request(intent="maybe")


def test_intents_claim_truth_or_the_opposite() -> None:
    assert request(intent="truth", direction="N").claimed_direction() == "N"
    assert request(intent="lie", direction="N").claimed_direction() == "S"
    assert request(intent="lie", direction="E").claimed_direction() == "W"



def test_clip_words_enforces_the_signed_cap() -> None:
    text = " ".join(["word"] * 40)
    assert len(clip_words(text, 15).split()) == 15


def test_the_template_speaks_the_claimed_direction() -> None:
    hint = TemplateProvider().generate(request(intent="truth", direction="S"))
    assert "south" in hint.lower()


def test_the_template_lies_convincingly() -> None:
    """With intent=lie the sentence points the opposite way."""
    hint = TemplateProvider().generate(request(intent="lie", direction="S"))
    assert "north" in hint.lower()
    assert "south" not in hint.lower()


def test_the_template_uses_arena_landmarks() -> None:
    from police_thief.infra.llm.template import LANDMARKS

    hints = [TemplateProvider().generate(request(step=step)) for step in range(6)]
    assert any(any(mark in hint for mark in LANDMARKS["New York"]) for hint in hints)


def test_the_shipped_arena_has_real_landmarks() -> None:
    """The arena config/game.json commits must never fall back to generic scenery.

    ``map_area`` is a signed term, so it moves when a series is renegotiated;
    whatever it moves to has to earn its own landmark pool, or FR-11's local
    flavour silently degrades to :data:`GENERIC_LANDMARKS` with nothing failing.
    """
    from police_thief.constants import ROLE_POLICE
    from police_thief.infra.llm.template import GENERIC_LANDMARKS, LANDMARKS
    from police_thief.shared.config import ConfigManager

    arena = ConfigManager.load(ROLE_POLICE).contract.world.map_area
    assert arena in LANDMARKS, f"shipped arena {arena!r} has no landmark pool"

    shipped = HintRequest(role="thief", intent="truth", true_direction="N",
                          map_area=arena, max_words=15, step=0)
    hints = [
        TemplateProvider().generate(
            HintRequest(role="thief", intent="truth", true_direction="N",
                        map_area=arena, max_words=15, step=step)
        )
        for step in range(6)
    ]
    assert any(any(mark in hint for mark in LANDMARKS[arena]) for hint in hints)
    assert not any(any(mark in hint for mark in GENERIC_LANDMARKS) for hint in hints)
    assert len(TemplateProvider().generate(shipped).split()) <= 15


def test_the_template_respects_the_word_cap() -> None:
    for step in range(10):
        hint = TemplateProvider().generate(request(step=step))
        assert len(hint.split()) <= 15


def test_the_template_is_deterministic() -> None:
    assert TemplateProvider().generate(request(3)) == TemplateProvider().generate(request(3))


def test_fallback_prefers_the_primary_and_rescues_failures() -> None:
    rescued = FallbackProvider(Exploding(), Canned())
    assert rescued.generate(request()) == "a canned hint"
    assert rescued.fallbacks_used == 1
    healthy = FallbackProvider(Canned(), Exploding())
    assert healthy.generate(request()) == "a canned hint"


def test_throttling_routes_by_step_number() -> None:
    chain = ThrottledProvider(Canned(), TemplateProvider(), every_n_steps=3)
    assert chain.generate(request(step=0)) == "a canned hint"
    assert chain.generate(request(step=1)) != "a canned hint"
    assert chain.generate(request(step=3)) == "a canned hint"


def test_the_budget_guard_cuts_off_paid_calls() -> None:
    ledger = TokenLedger(budget=100)
    ledger.record(step=0, provider="claude_api", input_tokens=80, output_tokens=30)
    guard = BudgetGuard(Canned(), ledger)
    with pytest.raises(ProviderError, match="budget exhausted"):
        guard.generate(request())


def test_the_ledger_tracks_totals_and_remaining() -> None:
    ledger = TokenLedger(budget=200000)
    ledger.record(step=1, provider="claude_api", input_tokens=120, output_tokens=40)
    ledger.record(step=2, provider="claude_api", input_tokens=100, output_tokens=30)
    assert ledger.total == 290
    assert ledger.step_total(1) == 160
    assert ledger.remaining == 200000 - 290
    assert not ledger.exhausted


def test_the_ledger_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        TokenLedger(budget=10).record(step=0, provider="x", input_tokens=-1, output_tokens=0)


def test_the_ledger_summary_reports_by_provider() -> None:
    ledger = TokenLedger(budget=1000)
    ledger.record(step=0, provider="claude_api", input_tokens=10, output_tokens=5)
    ledger.record(step=1, provider="ollama", input_tokens=7, output_tokens=3)
    summary = ledger.summary()
    assert summary["total_tokens"] == 25
    assert summary["by_provider"] == {"claude_api": 15, "ollama": 10}
    assert summary["calls"] == 2



def test_a_paid_chain_composes_guard_throttle_and_fallback() -> None:
    ledger = TokenLedger(budget=0)  # exhausted budget: paid calls must fail over
    provider = build_provider("claude_api", every_n_steps=1, ledger=ledger)
    hint = provider.generate(request(step=0))
    assert hint  # the template rescued the call
    assert isinstance(provider, FallbackProvider)


def test_an_unknown_provider_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown verbal provider"):
        build_provider("carrier_pigeon", every_n_steps=1, ledger=TokenLedger(budget=0))
