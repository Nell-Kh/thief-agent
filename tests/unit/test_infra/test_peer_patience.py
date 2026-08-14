"""Tests for the turn-delivery patience budget that rides out a tunnel drop.

The contract's budget - three tries, five seconds apart - spans fifteen
seconds. A free tunnel that drops takes longer than that to re-establish
itself, so under the bare budget a reconnect costs a whole sub-game. These
tests pin the three properties that make the extra patience safe: a turn
survives a drop, the handshake does not borrow the budget, and a peer that is
genuinely gone still becomes a technical loss.
"""

from __future__ import annotations

import pytest

from police_thief.infra.mcp_client import PeerClient, PeerUnreachableError
from police_thief.infra.transport import FlakyTransport, LoopbackTransport
from tests.unit.test_infra.test_mcp_client import FakeOpponent


@pytest.fixture
def patient(network_config, rate_limits, fake_clock):
    """Build a client whose turns keep retrying for forty more seconds."""

    def _build(failures: int, patience: float = 40.0) -> PeerClient:
        """A client over a transport that fails its first ``failures`` sends."""
        return PeerClient(
            FlakyTransport(LoopbackTransport(FakeOpponent()), failures=failures),
            network_config,
            rate_limits,
            sleep=fake_clock.advance,
            clock=fake_clock,
            turn_patience_sec=patience,
        )

    return _build


def test_the_patience_budget_is_reported(patient) -> None:
    assert patient(0).turn_patience_sec == 40.0


def test_a_negative_patience_is_read_as_none(network_config, rate_limits) -> None:
    """A nonsense value must not silently invert into an unbounded wait."""
    client = PeerClient(LoopbackTransport(FakeOpponent()), network_config, rate_limits,
                        turn_patience_sec=-5.0)
    assert client.turn_patience_sec == 0.0


def test_a_turn_survives_a_tunnel_that_comes_back(patient) -> None:
    """Six failures - twice the contract's budget - and the move still lands."""
    assert patient(6).send_turn({"step": 1, "sender": "police"})["ok"]


def test_an_audit_gets_the_same_patience_as_a_turn(patient) -> None:
    """Losing the disclosure after a won sub-game zeroes it just as thoroughly."""
    assert patient(6).submit_audit({"sender": "police", "records": [1]})["ok"]


def test_the_handshake_never_borrows_the_turn_patience(patient) -> None:
    """The opening wait belongs to the rendezvous loop, which can spot a refusal."""
    with pytest.raises(PeerUnreachableError, match="after 3 attempts"):
        patient(99).negotiate({"role": "police"})


def test_a_peer_that_is_really_gone_still_becomes_a_technical_loss(patient) -> None:
    with pytest.raises(PeerUnreachableError, match="unreachable"):
        patient(99).send_turn({"step": 1})


def test_the_give_up_message_counts_the_attempts_actually_made(patient) -> None:
    """More tries than the contract's three, and the message must say so."""
    with pytest.raises(PeerUnreachableError) as raised:
        patient(99).send_turn({"step": 1})
    attempts = int(str(raised.value).split("after ")[1].split(" ")[0])
    assert attempts > 3
