"""Tests for the concession protocol - how a trapped thief's loss crosses the wire.

Found by the region cop: the first strategy that ever converted a networked
capture exposed a dead end in the ending flow - the thief detected its own
loss and went silent, so the winner never learned it won. The concession
message closes that hole; these tests pin every side of it.
"""

from __future__ import annotations

import pytest

from police_thief.domain.crypto import verify
from police_thief.domain.turnmsg import TurnMessage
from police_thief.services.match_runtime import MatchRuntime
from police_thief.services.turn_receiving import receive_turn
from police_thief.services.world_view import WorldView
from police_thief.shared.config import ConfigManager


@pytest.fixture(scope="module")
def config_police() -> ConfigManager:
    """The cop side's configuration."""
    return ConfigManager.load("police")


@pytest.fixture(scope="module")
def config_thief() -> ConfigManager:
    """The thief side's configuration."""
    return ConfigManager.load("thief")


def message(sender: str, **extra) -> TurnMessage:
    """A minimal legal turn message from ``sender``."""
    return TurnMessage(
        step=extra.pop("step", 1), sender=sender, hint="", smell_grid={},
        commit=extra.pop("commit", "a" * 64), **extra,
    )


def test_a_trapping_barrier_makes_the_thief_concede(config_thief: ConfigManager) -> None:
    runtime = MatchRuntime(config_thief, game_id="c1", sub_game=1, github_commit="x")
    trap = message("police", barrier_placed=list(runtime.view.position))
    reply = runtime.on_turn(trap)
    assert runtime.result == {"type": "capture", "winner": "police", "how": "trapping barrier"}
    assert reply is not None and reply.claim_response == {"claim": list(runtime.view.position), "caught": True}
    assert reply.sender == "thief"


def test_the_concession_is_sealed_into_the_logbook(config_thief: ConfigManager) -> None:
    runtime = MatchRuntime(config_thief, game_id="c2", sub_game=1, github_commit="x")
    reply = runtime.on_turn(message("police", barrier_placed=list(runtime.view.position)))
    record = runtime.book.records[-1]
    assert record["payload"]["type"] == "concession"
    assert record["commit"] == reply.commit
    assert verify(record["payload"], record["nonce"], record["commit"])


def test_the_thief_concedes_exactly_once(config_thief: ConfigManager) -> None:
    runtime = MatchRuntime(config_thief, game_id="c3", sub_game=1, github_commit="x")
    first = runtime.on_turn(message("police", barrier_placed=list(runtime.view.position)))
    second = runtime.on_turn(message("police", step=2))
    assert first is not None and second is None


def test_the_police_accepts_the_concession(config_police: ConfigManager) -> None:
    runtime = MatchRuntime(config_police, game_id="c4", sub_game=1, github_commit="x")
    reply = runtime.on_turn(message("thief", win_claim={"type": "capture"}))
    assert runtime.result == {"type": "capture", "winner": "police", "how": "conceded"}
    assert reply is None  # only the thief ever concedes


def test_the_police_accepts_the_new_kit_shape_concession(config_police: ConfigManager) -> None:
    runtime = MatchRuntime(config_police, game_id="c4b", sub_game=1, github_commit="x")
    # A true concession uses the claim_response format
    reply = runtime.on_turn(message("thief", claim_response={"claim": [0, 0], "caught": True}))
    assert runtime.result == {"type": "capture", "winner": "police", "how": "capture claim"}
    assert reply is None  # only the thief ever concedes

def test_a_concession_from_the_police_side_is_ignored(config_thief: ConfigManager) -> None:
    """A malicious cop cannot win by 'conceding' on the thief's behalf."""
    view = WorldView.open("thief", config_thief.contract)
    receive_turn(view, message("police", win_claim={"type": "capture"}), config_thief.contract)
    assert view.result is None

def test_a_claim_response_from_the_police_is_a_violation(config_thief: ConfigManager) -> None:
    view = WorldView.open("thief", config_thief.contract)
    receive_turn(view, message("police", claim_response={"claim": [0, 0], "caught": True}), config_thief.contract)
    assert view.result is not None and view.result["type"] == "technical_loss"


def test_a_survival_claim_from_the_police_side_is_ignored(
    config_police: ConfigManager,
) -> None:
    """Only the thief may claim survival - and never below the threshold."""
    view = WorldView.open("police", config_police.contract)
    receive_turn(
        view, message("police", step=1, win_claim={"type": "survival"}),
        config_police.contract,
    )
    assert view.result is None

def test_a_boxed_in_thief_concedes_rule_47(config_thief: ConfigManager) -> None:
    """Rule 47: every exit a barrier, STAY does not rescue - and it must be SAID.

    The kit's SPEC 3.1 warning verbatim: a thief that does not speak this
    ending forks the game - it settles CAPTURE while the cop settles TIMEOUT.
    Found live in our own wire audit: the cop boxed the thief at step 28 and
    the game silently ran to a false survival.
    """
    runtime = MatchRuntime(config_thief, game_id="r47", sub_game=1, github_commit="x")
    row, col = runtime.view.position
    exits = [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]
    reply = None
    for step, cell in enumerate(exits, start=1):
        reply = runtime.on_turn(message("police", step=step, commit=f"c{step}" * 8,
                                        barrier_placed=list(cell)))
    assert runtime.result == {"type": "capture", "winner": "police", "how": "boxed in (rule 47)"}
    assert reply is not None
    assert reply.claim_response == {"claim": [row, col], "caught": True}


def test_a_thief_with_one_exit_left_does_not_concede(config_thief: ConfigManager) -> None:
    runtime = MatchRuntime(config_thief, game_id="r47b", sub_game=1, github_commit="x")
    row, col = runtime.view.position
    for step, cell in enumerate([(row - 1, col), (row + 1, col), (row, col - 1)], start=1):
        reply = runtime.on_turn(message("police", step=step, commit=f"c{step}" * 8,
                                        barrier_placed=list(cell)))
        assert reply is None
    assert runtime.result is None  # one door still open - keep running

