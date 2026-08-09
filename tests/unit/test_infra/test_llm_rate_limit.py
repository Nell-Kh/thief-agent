"""The verbal layer's requests-per-minute ceiling actually controls something.

`config/rate_limits.json` carried an ``anthropic`` block that no code path read:
configuration shaped like a control that was not one. The guidelines' ban on
hardcoded values cuts both ways - a limit nothing consults is the mirror image
of a number nobody can change - and a burst of paid calls is exactly what earns
a 429 mid-match.

These pin that the wiring is real: the file is read, the bucket refuses, and a
refusal degrades to a free template hint rather than costing a turn.
"""

from __future__ import annotations

import json

from police_thief.infra.llm import RateLimitedProvider, TokenLedger, build_provider
from police_thief.infra.llm.base import HintProvider, HintRequest, ProviderError
from police_thief.services.match_runtime import _verbal_rate_limit
from police_thief.shared.bucket import TokenBucket


class _Counting(HintProvider):
    """A stand-in paid provider that records how often it was actually reached."""

    name = "counting"

    def __init__(self) -> None:
        """Start with nothing generated."""
        self.calls = 0

    def generate(self, request: HintRequest) -> str:
        """Count the call and return a recognisable marker."""
        self.calls += 1
        return "paid hint"


def _request() -> HintRequest:
    """A minimal hint request; its content is irrelevant to rate limiting."""
    return HintRequest(
        role="police",
        intent="truth",
        true_direction="N",
        map_area="Haifa",
        max_words=15,
        step=1,
    )


def test_the_configured_limit_is_read_from_the_file() -> None:
    """The block that used to be dead is now the source of the ceiling."""
    assert _verbal_rate_limit() == 30


def test_a_missing_file_leaves_the_chain_unlimited_rather_than_crashing(tmp_path) -> None:
    """A checkout without the config must still play."""
    assert _verbal_rate_limit(str(tmp_path / "nope.json")) is None


def test_a_malformed_file_is_treated_as_no_limit(tmp_path) -> None:
    """Recovery beats refusal: a broken limit file must not stop a match."""
    broken = tmp_path / "rate_limits.json"
    broken.write_text(json.dumps({"unexpected": True}), encoding="utf-8")
    assert _verbal_rate_limit(str(broken)) is None


def test_the_bucket_refuses_once_the_allowance_is_spent() -> None:
    """Two permitted calls, then a refusal - the whole point of the wrapper."""
    inner = _Counting()
    limited = RateLimitedProvider(inner, TokenBucket(capacity=2, refill_per_sec=0.001))
    assert limited.generate(_request()) == "paid hint"
    assert limited.generate(_request()) == "paid hint"
    try:
        limited.generate(_request())
        raise AssertionError("third call should have been refused")
    except ProviderError:
        pass
    assert inner.calls == 2
    assert limited.refusals == 1


def test_a_refusal_degrades_to_the_template_instead_of_failing_the_turn() -> None:
    """End-to-end through the assembled chain: a burst costs words, never a game."""
    ledger = TokenLedger(budget=10_000)
    chain = build_provider(
        "claude_api", every_n_steps=1, ledger=ledger, requests_per_minute=1
    )
    first = chain.generate(_request())
    second = chain.generate(_request())
    assert isinstance(first, str) and first
    assert isinstance(second, str) and second


def test_omitting_the_limit_builds_a_chain_without_the_wrapper() -> None:
    """Most tests and the template path want no ceiling at all."""
    ledger = TokenLedger(budget=10)
    unlimited = build_provider("claude_api", every_n_steps=1, ledger=ledger)
    assert "rate_limited" not in repr(unlimited)
