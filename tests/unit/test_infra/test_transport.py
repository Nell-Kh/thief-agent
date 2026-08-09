"""Tests for the transport abstraction between peers."""

from __future__ import annotations

import pytest

from police_thief.infra.transport import (
    FlakyTransport,
    LoopbackTransport,
    Transport,
    TransportError,
)


class Recorder:
    """A handler with one protocol tool, recording what it receives."""

    def __init__(self) -> None:
        """Start with an empty received log."""
        self.received: list[dict] = []

    def receive_turn(self, payload: dict) -> dict:
        """Record the payload and acknowledge the step."""
        self.received.append(payload)
        return {"ok": True, "step": payload.get("step")}


def test_the_loopback_delivers_to_the_matching_tool() -> None:
    handler = Recorder()
    transport = LoopbackTransport(handler)
    reply = transport.send("receive_turn", {"step": 4})
    assert reply["ok"] and reply["step"] == 4
    assert handler.received == [{"step": 4}]


def test_the_loopback_records_what_was_sent() -> None:
    transport = LoopbackTransport(Recorder())
    transport.send("receive_turn", {"step": 2})
    tool, payload = transport.sent[0]
    assert tool == "receive_turn"
    assert payload["step"] == 2


def test_an_unknown_tool_is_refused() -> None:
    """A peer cannot invoke a tool its opponent does not expose."""
    with pytest.raises(TransportError, match="no tool named 'gossip'"):
        LoopbackTransport(object()).send("gossip", {})


def test_the_flaky_transport_fails_its_budget_then_delivers() -> None:
    transport = FlakyTransport(LoopbackTransport(Recorder()), failures=1)
    with pytest.raises(TransportError, match="simulated delivery failure"):
        transport.send("receive_turn", {"step": 1})
    assert transport.send("receive_turn", {"step": 1})["ok"]


def test_both_transports_satisfy_the_protocol() -> None:
    """Any transport is interchangeable: loopback, localhost or a tunnel."""
    assert isinstance(LoopbackTransport(Recorder()), Transport)
    assert isinstance(FlakyTransport(LoopbackTransport(Recorder()), 0), Transport)
