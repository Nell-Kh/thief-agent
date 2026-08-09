"""Tests for the deadline tracker.

Time is injected, so these tests are deterministic and never sleep."""

from __future__ import annotations

import pytest

from police_thief.services.deadline import DeadlineExpiredError, DeadlineTracker


class FakeClock:
    """A hand-cranked monotonic clock."""

    def __init__(self) -> None:
        """Start the fake clock at zero."""
        self.now = 0.0

    def __call__(self) -> float:
        """Return the current fake time, standing in for ``time.monotonic``."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the fake clock forward without actually sleeping."""
        self.now += seconds



def test_a_non_positive_timeout_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        DeadlineTracker(0)


def test_a_started_request_is_in_flight() -> None:
    tracker = DeadlineTracker(30, clock=FakeClock())
    tracker.start("reveal")
    assert tracker.in_flight == ("reveal",)


def test_the_expiry_is_the_timeout_ahead_of_the_send() -> None:
    clock = FakeClock()
    pending = DeadlineTracker(30, clock=clock).start("commit")
    assert pending.expires_at - pending.sent_at == 30


def test_completing_a_request_reports_its_duration() -> None:
    clock = FakeClock()
    tracker = DeadlineTracker(30, clock=clock)
    tracker.start("commit")
    clock.advance(4)
    assert tracker.complete("commit") == 4
    assert tracker.in_flight == ()


def test_completing_an_unknown_request_raises() -> None:
    with pytest.raises(KeyError):
        DeadlineTracker(30).complete("never-sent")


def test_a_request_within_its_deadline_passes() -> None:
    clock = FakeClock()
    tracker = DeadlineTracker(30, clock=clock)
    tracker.start("commit")
    clock.advance(29)
    tracker.check("commit")


def test_an_overdue_request_is_a_failure_not_patience() -> None:
    clock = FakeClock()
    tracker = DeadlineTracker(30, clock=clock)
    tracker.start("reveal")
    clock.advance(31)
    with pytest.raises(DeadlineExpiredError, match="exceeded its 30s deadline"):
        tracker.check("reveal")


def test_checking_an_unknown_request_is_a_no_op() -> None:
    DeadlineTracker(30).check("never-sent")


def test_expired_lists_only_overdue_requests() -> None:
    clock = FakeClock()
    tracker = DeadlineTracker(30, clock=clock)
    tracker.start("old")
    clock.advance(31)
    tracker.start("fresh")
    assert [pending.label for pending in tracker.expired()] == ["old"]


def test_check_all_raises_on_the_first_overdue_request() -> None:
    clock = FakeClock()
    tracker = DeadlineTracker(30, clock=clock)
    tracker.start("commit")
    clock.advance(31)
    with pytest.raises(DeadlineExpiredError, match="commit"):
        tracker.check_all()


def test_check_all_passes_when_nothing_is_overdue() -> None:
    tracker = DeadlineTracker(30, clock=FakeClock())
    tracker.start("commit")
    tracker.check_all()


def test_clearing_abandons_every_in_flight_request() -> None:
    tracker = DeadlineTracker(30, clock=FakeClock())
    tracker.start("commit")
    tracker.clear()
    assert tracker.in_flight == ()


def test_the_timeout_is_exposed() -> None:
    assert DeadlineTracker(30).timeout_sec == 30


def test_tolerated_traffic_never_renews_the_deadline() -> None:
    clock = FakeClock()
    tracker = DeadlineTracker(100, clock=clock)
    tracker.start("commit")

    clock.advance(90)
    tracker.check_all()

    clock.advance(10)
    with pytest.raises(DeadlineExpiredError, match="exceeded its 100s deadline"):
        tracker.check_all()
