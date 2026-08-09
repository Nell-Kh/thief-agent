"""Tests for the Orchestrator - the single gateway to a peer's subsystems."""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.infra.transport import FlakyTransport, LoopbackTransport
from police_thief.services.inbound import HandshakeRejectedError, InboundHandler
from police_thief.services.orchestrator import Orchestrator
from police_thief.shared.config import ConfigManager


@pytest.fixture
def opponent(config_dir: Path) -> InboundHandler:
    """A thief peer holding the same contract as us."""
    from police_thief.shared.interop import negotiate_extras, terms_from_contract

    thief = ConfigManager.load("thief", config_dir)
    return InboundHandler(
        our_terms=terms_from_contract(thief.contract),
        our_extras=negotiate_extras(thief.role, 1),
        expect_role="police",
    )


@pytest.fixture
def police(config_dir: Path, opponent: InboundHandler) -> Orchestrator:
    """An orchestrator for the cop over a loopback transport."""
    return Orchestrator(ConfigManager.load("police", config_dir), LoopbackTransport(opponent))


def test_the_orchestrator_owns_every_subsystem(police: Orchestrator) -> None:
    """One gateway; no peripheral module reaches another directly."""
    assert police.sdk is not None
    assert police.phases.state == "WAITING_FOR_OPPONENT"
    assert police.client is not None
    assert police.inbound is not None
    assert police.watchdog.timeout_sec == 60


def test_the_role_comes_from_the_configuration(police: Orchestrator) -> None:
    assert police.role == "police"


def test_no_state_exists_before_the_match_starts(police: Orchestrator) -> None:
    with pytest.raises(RuntimeError, match="no match in progress"):
        _ = police.state


def test_starting_a_match_shakes_hands_and_creates_the_board(
    police: Orchestrator, opponent: InboundHandler
) -> None:
    reply = police.start_match(peer_id="team-a", games_played=1)
    assert reply["accepted"]
    assert police.state.cop == (0, 0)
    assert opponent.opponent_games_played == 1


def test_a_contract_mismatch_stops_the_match_before_the_first_move(
    config_dir: Path,
) -> None:
    stranger = InboundHandler(our_terms={"board_size": 9}, our_extras={}, expect_role="police")
    police = Orchestrator(ConfigManager.load("police", config_dir), LoopbackTransport(stranger))
    with pytest.raises(HandshakeRejectedError, match="terms mismatch"):
        police.start_match(peer_id="team-a", games_played=0)


def test_an_unreachable_opponent_becomes_a_technical_loss(
    config_dir: Path, opponent: InboundHandler
) -> None:
    """We announce a result rather than hang - that is the whole point."""
    transport = FlakyTransport(LoopbackTransport(opponent), failures=99)
    police = Orchestrator(ConfigManager.load("police", config_dir), transport)
    police._state = police.sdk.new_game()
    result = police.run_guarded(lambda: police.client.send_turn({"step": 1}))
    assert result is None
    assert police.lost
    assert police.state.outcome is not None
    assert police.state.outcome.event == "technical_loss"


def test_a_successful_call_passes_its_result_through(police: Orchestrator) -> None:
    police.start_match(peer_id="team-a", games_played=0)
    wire = {
        "step": 1,
        "sender": "police",
        "hint": "on the move",
        "smell_grid": {"0,0": 0.9},
        "commit": "a" * 64,
    }
    reply = police.run_guarded(lambda: police.client.send_turn(wire))
    assert reply is not None
    assert reply["ok"]
    assert not police.lost


def test_failing_forfeits_the_game_and_terminates_the_machine(police: Orchestrator) -> None:
    police.start_match(peer_id="team-a", games_played=0)
    police.fail("the opponent went dark")
    assert police.lost
    assert police.phases.terminal
    assert police.state.outcome is not None
    assert police.state.outcome.cop_points == 0


def test_failing_before_a_match_is_still_safe(police: Orchestrator) -> None:
    police.fail("crashed during setup")
    assert police.lost


def test_a_heartbeat_keeps_the_peer_alive(police: Orchestrator) -> None:
    assert police.heartbeat() == "ALIVE"


def test_the_watchdog_rescues_state_when_the_loop_freezes(police: Orchestrator) -> None:
    police.start_match(peer_id="team-a", games_played=0)
    police.watchdog._last_beat -= police.watchdog.timeout_sec + 1
    assert police.guard() == "SHUTDOWN"
    assert police.recovery.state is police.state
    assert police.recovery.shutdown_called


def test_the_peer_expects_messages_from_its_opponent_only(police: Orchestrator) -> None:
    assert police.inbound.expect_role == "thief"


def test_both_peers_can_be_orchestrated_from_the_same_contract(config_dir: Path) -> None:
    """Symmetry: the thief runs exactly the same machinery as the cop."""
    from police_thief.shared.interop import negotiate_extras, terms_from_contract

    police_config = ConfigManager.load("police", config_dir)
    police_handler = InboundHandler(
        our_terms=terms_from_contract(police_config.contract),
        our_extras=negotiate_extras(police_config.role, 1),
        expect_role="thief",
    )
    thief = Orchestrator(
        ConfigManager.load("thief", config_dir), LoopbackTransport(police_handler)
    )
    assert thief.role == "thief"
    assert thief.start_match(peer_id="team-b", games_played=0)["accepted"]
