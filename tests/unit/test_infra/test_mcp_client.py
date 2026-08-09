"""Tests for the outbound peer client: deadlines, retries and give-up."""

from __future__ import annotations

import pytest

from police_thief.infra.mcp_client import PeerClient, PeerUnreachableError
from police_thief.infra.transport import FlakyTransport, LoopbackTransport
from police_thief.services.deadline import DeadlineExpiredError


class FakeOpponent:
    """An opponent exposing the three protocol tools, recording every call."""

    def __init__(self) -> None:
        """Start with an empty call log."""
        self.calls: list[tuple[str, dict]] = []

    def negotiate(self, payload: dict) -> dict:
        """Record the greeting and accept it."""
        self.calls.append(("negotiate", payload))
        return {"accepted": True}

    def receive_turn(self, payload: dict) -> dict:
        """Record the turn and acknowledge it."""
        self.calls.append(("receive_turn", payload))
        return {"ok": True, "step": payload.get("step")}

    def submit_audit(self, payload: dict) -> dict:
        """Record the disclosure and acknowledge it."""
        self.calls.append(("submit_audit", payload))
        return {"ok": True, "records": len(payload.get("records", []))}


@pytest.fixture
def opponent() -> FakeOpponent:
    """A fake opponent recording every tool call it receives."""
    return FakeOpponent()


@pytest.fixture
def build(network_config, rate_limits, fake_clock):
    """Build a client, optionally recording backoff sleeps."""

    def _build(transport, sleeps: list[float] | None = None, clock=None) -> PeerClient:
        """A peer client wired to the given transport and limits."""
        return PeerClient(
            transport,
            network_config,
            rate_limits,
            sleep=(sleeps.append if sleeps is not None else lambda _: None),
            clock=clock or fake_clock,
        )

    return _build


def test_every_protocol_message_has_a_client_method(opponent, build) -> None:
    client = build(LoopbackTransport(opponent))
    client.negotiate({"role": "police"})
    client.send_turn({"step": 1, "sender": "police"})
    client.submit_audit({"sender": "police", "records": [1]})
    assert [name for name, _ in opponent.calls] == ["negotiate", "receive_turn", "submit_audit"]


def test_a_transient_failure_is_retried(opponent, build) -> None:
    transport = FlakyTransport(LoopbackTransport(opponent), failures=2)
    sleeps: list[float] = []
    reply = build(transport, sleeps).negotiate({"role": "police"})
    assert reply["accepted"]
    assert sleeps == [5, 5]


def test_the_retry_budget_is_bounded(opponent, build) -> None:
    """After the budget is spent we give up rather than wait forever."""
    transport = FlakyTransport(LoopbackTransport(opponent), failures=99)
    with pytest.raises(PeerUnreachableError, match="after 3 attempts"):
        build(transport).negotiate({"role": "police"})


def test_no_backoff_is_slept_after_the_final_attempt(opponent, build, rate_limits) -> None:
    transport = FlakyTransport(LoopbackTransport(opponent), failures=99)
    sleeps: list[float] = []
    with pytest.raises(PeerUnreachableError):
        build(transport, sleeps).send_turn({"step": 1})
    assert len(sleeps) == rate_limits.max_retries - 1


def test_a_late_reply_is_treated_as_a_failure(build, fake_clock) -> None:
    """A missed deadline is a failure, not an invitation to keep waiting."""
    clock = fake_clock

    class SlowTransport:
        """A transport whose send overruns the response deadline."""
        def send(self, tool: str, payload: dict) -> dict:
            """Deliver the payload, advancing the fake clock as the case requires."""
            clock.advance(31)
            return {"ok": True}

    with pytest.raises(DeadlineExpiredError, match="deadline"):
        build(SlowTransport(), clock=clock).send_turn({"step": 1})


def test_a_reply_inside_the_deadline_is_accepted(build, fake_clock) -> None:
    clock = fake_clock

    class PromptTransport:
        """A transport that answers just inside the response deadline."""
        def send(self, tool: str, payload: dict) -> dict:
            """Deliver the payload, advancing the fake clock as the case requires."""
            clock.advance(29)
            return {"ok": True}

    assert build(PromptTransport(), clock=clock).send_turn({"step": 1})["ok"]


def test_nothing_stays_in_flight_after_success_or_giving_up(opponent, build) -> None:
    client = build(LoopbackTransport(opponent))
    client.send_turn({"step": 1})
    assert client.deadlines.in_flight == ()
    failing = build(FlakyTransport(LoopbackTransport(opponent), failures=99))
    with pytest.raises(PeerUnreachableError):
        failing.send_turn({"step": 2})
    assert failing.deadlines.in_flight == ()


def test_the_deadline_comes_from_the_contract(opponent, build, network_config) -> None:
    client = build(LoopbackTransport(opponent))
    assert client.deadlines.timeout_sec == network_config.response_timeout_sec


def test_calling_a_tool_the_opponent_lacks_is_refused(build) -> None:
    with pytest.raises(PeerUnreachableError):
        build(LoopbackTransport(object())).send_turn({"step": 1})
