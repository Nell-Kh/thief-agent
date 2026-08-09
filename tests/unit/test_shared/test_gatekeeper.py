"""Tests for the Gatekeeper - three gates, a queue, and a monitoring log."""

from __future__ import annotations

from police_thief.shared.gatekeeper import (
    STATUS_LOCKED,
    STATUS_QUEUED,
    STATUS_SENT,
    Gatekeeper,
)


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


def make_keeper(clock: FakeClock, **overrides: object) -> Gatekeeper:
    """A small, fully-configured Gatekeeper with no hidden defaults."""
    settings: dict = {
        "requests_per_minute": 60,
        "daily_quota": 5,
        "queue_depth": 3,
        "dos_max_per_window": 10,
        "dos_window_sec": 1.0,
        "clock": clock,
    }
    settings.update(overrides)
    return Gatekeeper(**settings)


def test_a_clean_request_passes_all_three_gates() -> None:
    clock, sent = FakeClock(), []
    keeper = make_keeper(clock)
    assert keeper.execute(lambda: sent.append(1), label="report") == STATUS_SENT
    assert sent == [1]
    assert keeper.log[-1]["status"] == STATUS_SENT


def test_the_daily_quota_is_the_last_line_before_suspension() -> None:
    clock, sent = FakeClock(), []
    keeper = make_keeper(clock, daily_quota=2)
    for _ in range(2):
        clock.advance(2.0)
        keeper.execute(lambda: sent.append(1))
    clock.advance(2.0)
    assert keeper.execute(lambda: sent.append(1)) == STATUS_QUEUED
    assert sent == [1, 1]  # the third call never went out


def test_an_empty_bucket_queues_and_drain_recovers() -> None:
    clock, sent = FakeClock(), []
    keeper = make_keeper(
        clock, requests_per_minute=60, daily_quota=100, dos_max_per_window=200
    )  # 1 token/sec, C=60; other gates opened wide to isolate the bucket
    for _ in range(60):
        keeper.execute(lambda: sent.append(1))
    assert keeper.execute(lambda: sent.append(1)) == STATUS_QUEUED
    assert keeper.queue_size == 1
    clock.advance(5.0)  # refill earns whole tokens again
    assert keeper.drain() == 1
    assert keeper.queue_size == 0 and len(sent) == 61


def test_dos_burst_locks_the_whole_pipeline() -> None:
    clock, sent = FakeClock(), []
    keeper = make_keeper(clock, dos_max_per_window=3, daily_quota=100)
    for _ in range(3):
        clock.advance(0.01)
        keeper.execute(lambda: sent.append(1))
    clock.advance(0.01)
    assert keeper.execute(lambda: sent.append(1)) == STATUS_LOCKED
    assert keeper.locked
    # A locked pipeline sacrifices every report - even legitimate ones.
    clock.advance(30.0)
    assert keeper.execute(lambda: sent.append(1)) == STATUS_LOCKED
    assert len(sent) == 3


def test_reset_lock_rearms_after_the_anomaly_is_investigated() -> None:
    clock, sent = FakeClock(), []
    keeper = make_keeper(clock, dos_max_per_window=2, daily_quota=100)
    for _ in range(4):
        keeper.execute(lambda: sent.append(1))
    assert keeper.locked
    keeper.reset_lock()
    clock.advance(10.0)
    assert keeper.execute(lambda: sent.append(1)) == STATUS_SENT


def test_overflow_beyond_queue_depth_is_dropped_but_logged() -> None:
    clock = FakeClock()
    keeper = make_keeper(clock, daily_quota=0, queue_depth=2, dos_max_per_window=50)
    for _ in range(4):
        clock.advance(1.0)
        keeper.execute(lambda: None)
    assert keeper.queue_size == 2  # depth respected - no unbounded memory
    assert keeper.backpressure
    assert len(keeper.log) == 4  # every attempt visible to monitoring


def test_drain_stops_at_the_daily_quota() -> None:
    clock, sent = FakeClock(), []
    keeper = make_keeper(clock, daily_quota=1, queue_depth=5, dos_max_per_window=50)
    clock.advance(1.0)
    keeper.execute(lambda: sent.append(1))  # spends the whole quota
    clock.advance(1.0)
    keeper.execute(lambda: sent.append(1))  # queued
    clock.advance(60.0)
    assert keeper.drain() == 0  # quota, not rate, is the binding gate
    assert sent == [1]
