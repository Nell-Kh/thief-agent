"""Tests for the token-bucket rate limiter - driven by a hand-cranked clock."""

from __future__ import annotations

import pytest

from police_thief.shared.bucket import TokenBucket


class FakeClock:
    """A monotonic clock the test advances by hand."""

    def __init__(self) -> None:
        """Start the fake clock at zero."""
        self.now = 0.0

    def __call__(self) -> float:
        """Return the current fake time, standing in for ``time.monotonic``."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the fake clock forward without actually sleeping."""
        self.now += seconds


def test_a_new_bucket_starts_full_and_spends_down() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=3, refill_per_sec=1.0, clock=clock)
    assert bucket.tokens == 3
    assert all(bucket.allow() for _ in range(3))
    assert not bucket.allow()  # the burst is exhausted


def test_quiet_time_refills_but_never_past_capacity() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=2, refill_per_sec=0.5, clock=clock)
    bucket.allow()
    bucket.allow()
    clock.advance(2.0)  # earns exactly one token
    assert bucket.allow()
    assert not bucket.allow()
    clock.advance(1000.0)  # a long silence still caps at C
    assert bucket.tokens == 2


def test_the_verbatim_update_rule_holds() -> None:
    """tokens <- min(C, tokens + r*dt): fractional refill accumulates."""
    clock = FakeClock()
    bucket = TokenBucket(capacity=5, refill_per_sec=0.8, clock=clock)
    for _ in range(5):
        bucket.allow()
    clock.advance(1.0)
    assert not bucket.allow()  # 0.8 tokens is not a whole token
    clock.advance(0.25)
    assert bucket.allow()  # 1.0 accumulated - allow <=> tokens >= 1


def test_a_costlier_request_needs_more_tokens() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=4, refill_per_sec=1.0, clock=clock)
    assert bucket.allow(cost=4.0)
    assert not bucket.allow(cost=0.5) or bucket.tokens >= 0.5


def test_per_minute_matches_the_contract_rate() -> None:
    clock = FakeClock()
    bucket = TokenBucket.per_minute(30, clock=clock)
    assert bucket.capacity == 30
    assert bucket.refill_per_sec == pytest.approx(0.5)
    for _ in range(30):
        assert bucket.allow()
    clock.advance(2.0)  # one token per two seconds at 30/min
    assert bucket.allow()
    assert not bucket.allow()


@pytest.mark.parametrize("capacity,rate", [(0, 1.0), (-1, 1.0), (5, 0.0), (5, -0.5)])
def test_non_positive_parameters_are_rejected(capacity: float, rate: float) -> None:
    with pytest.raises(ValueError):
        TokenBucket(capacity=capacity, refill_per_sec=rate)
