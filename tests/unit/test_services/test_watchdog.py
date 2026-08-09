"""Tests for the watchdog that guards the whole peer.

Time is injected, so these tests are deterministic and never sleep."""

from __future__ import annotations

import pytest

from police_thief.services.watchdog import STATUS_ALIVE, STATUS_SHUTDOWN, Watchdog


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



def test_a_non_positive_watchdog_timeout_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        Watchdog(0)


def test_a_beating_loop_stays_alive() -> None:
    clock = FakeClock()
    dog = Watchdog(60, clock=clock)
    for _ in range(5):
        clock.advance(30)
        dog.beat()
        assert dog.check() == STATUS_ALIVE


def test_a_frozen_loop_triggers_a_controlled_shutdown() -> None:
    clock = FakeClock()
    events: list[str] = []
    dog = Watchdog(
        60,
        on_persist=lambda: events.append("persist"),
        on_shutdown=lambda: events.append("shutdown"),
        clock=clock,
    )
    clock.advance(61)
    assert dog.check() == STATUS_SHUTDOWN
    assert events == ["persist", "shutdown"]


def test_state_is_persisted_before_shutdown() -> None:
    """Recovery is only possible if the state was saved first."""
    clock = FakeClock()
    events: list[str] = []
    dog = Watchdog(
        60,
        on_persist=lambda: events.append("persist"),
        on_shutdown=lambda: events.append("shutdown"),
        clock=clock,
    )
    clock.advance(120)
    dog.check()
    assert events.index("persist") < events.index("shutdown")


def test_firing_is_idempotent() -> None:
    """A watchdog that already fired must not fire again and double-report."""
    clock = FakeClock()
    calls: list[int] = []
    dog = Watchdog(60, on_shutdown=lambda: calls.append(1), clock=clock)
    clock.advance(61)
    dog.check()
    dog.check()
    assert calls == [1]
    assert dog.triggered


def test_a_watchdog_without_callbacks_still_reports_shutdown() -> None:
    clock = FakeClock()
    dog = Watchdog(60, clock=clock)
    clock.advance(61)
    assert dog.check() == STATUS_SHUTDOWN


def test_resetting_rearms_the_watchdog() -> None:
    clock = FakeClock()
    dog = Watchdog(60, clock=clock)
    clock.advance(61)
    dog.check()
    dog.reset()
    assert not dog.triggered
    assert dog.check() == STATUS_ALIVE


def test_elapsed_measures_since_the_last_beat() -> None:
    clock = FakeClock()
    dog = Watchdog(60, clock=clock)
    clock.advance(10)
    assert dog.elapsed() == 10


def test_repr_shows_the_timeout_and_trigger_state() -> None:
    assert "timeout=60" in repr(Watchdog(60))
