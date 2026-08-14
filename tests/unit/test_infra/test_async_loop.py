"""Tests for the long-lived loop thread that carries a held-open session."""

from __future__ import annotations

import asyncio

import pytest

from police_thief.infra.async_loop import LoopThread, shared_loop


@pytest.fixture
def loop() -> LoopThread:
    """A private loop thread, stopped when the test finishes."""
    thread = LoopThread(name="test-loop")
    yield thread
    thread.close()


async def _answer(value: int) -> int:
    """Return ``value`` after yielding once, so the loop really runs it."""
    await asyncio.sleep(0)
    return value


async def _sleep_forever() -> None:
    """Never finish, standing in for a peer that has stopped answering."""
    await asyncio.sleep(3600)


async def _explode() -> None:
    """Fail inside the loop, so the caller's thread sees the real exception."""
    raise ValueError("inside the loop")


def test_a_coroutine_runs_on_the_loop_thread(loop: LoopThread) -> None:
    assert loop.run(_answer(7), timeout=5) == 7


def test_the_same_loop_serves_many_calls(loop: LoopThread) -> None:
    """The whole point: a session opened on call one is alive on call twenty."""
    assert [loop.run(_answer(n), timeout=5) for n in range(20)] == list(range(20))


def test_an_exception_crosses_back_to_the_caller(loop: LoopThread) -> None:
    with pytest.raises(ValueError, match="inside the loop"):
        loop.run(_explode(), timeout=5)


def test_a_hung_call_times_out_instead_of_wedging_the_turn_loop(loop: LoopThread) -> None:
    """Blocking forever on a peer we do not control is the forbidden deadlock."""
    with pytest.raises(TimeoutError, match="budget"):
        loop.run(_sleep_forever(), timeout=0.2)


def test_the_loop_still_works_after_a_timeout(loop: LoopThread) -> None:
    with pytest.raises(TimeoutError):
        loop.run(_sleep_forever(), timeout=0.2)
    assert loop.run(_answer(1), timeout=5) == 1


def test_closing_is_idempotent_and_reports_not_running(loop: LoopThread) -> None:
    assert loop.running
    loop.close()
    loop.close()
    assert not loop.running


def test_the_shared_loop_is_reused_across_callers() -> None:
    assert shared_loop() is shared_loop()


def test_a_closed_shared_loop_is_replaced_rather_than_reused() -> None:
    """A process that tore the loop down must still be able to play again."""
    first = shared_loop()
    first.close()
    second = shared_loop()
    assert second is not first
    assert second.running
