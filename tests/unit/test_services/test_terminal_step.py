"""One game, one length: the terminal turn, in the causing side's numbering.

``view.step`` counts only a peer's OWN moves, and the loser seals one more real
turn to concede (:mod:`services.concession`) - so a report built from it files
the winner's number on one side and the loser's on the other. sharNamr and this
repository discovered exactly that reconciling friendly-9 (2026-08-17): each of
us reported our own record count on the sub-games we lost, and neither of us was
wrong about our own logs, because the field was never defined.

The definition these tests pin:

    steps = the number of the turn on which the terminal condition occurred,
            in the numbering of the side that CAUSED it - the cop's turn for a
            capture, the thief's for a survival - counting the first turn as 1.

What makes it agreeable rather than merely ours: that turn number travels on
the wire inside the sealed message that ends the game, and again inside the
disclosure exchanged at the mutual audit. Neither side has to trust the other's
arithmetic; both read the same integer off the same bytes.
"""

from __future__ import annotations

import pytest

from police_thief.domain.turnmsg import TurnMessage
from police_thief.services.match_runtime import MatchRuntime
from police_thief.shared.config import ConfigManager


@pytest.fixture(scope="module")
def config_thief() -> ConfigManager:
    """The thief side's configuration."""
    return ConfigManager.load("thief")


@pytest.fixture(scope="module")
def config_police() -> ConfigManager:
    """The cop side's configuration."""
    return ConfigManager.load("police")


def message(sender: str, step: int, **extra) -> TurnMessage:
    """A minimal legal turn message from ``sender`` at ``step``."""
    return TurnMessage(step=step, sender=sender, hint="", smell_grid={},
                       commit="a" * 64, **extra)


def deliver(runtime: MatchRuntime, sender: str, step: int, **extra) -> None:
    """Hand ``runtime`` an opponent turn at ``step``, mid-stream rather than first.

    The sequence enforcement (:mod:`services.enforcement`) refuses a step that
    skips ahead, so a test starting at turn 26 has to say that turns 1..25
    already happened - which is exactly what a real game would have done.
    """
    runtime.view.opponent_step = step - 1
    runtime.on_turn(message(sender, step, **extra))


def test_the_losing_thief_reports_the_cops_turn_not_its_own_concession(
    config_thief: ConfigManager,
) -> None:
    """The exact friendly-9 disagreement, from the side that seals the extra turn."""
    runtime = MatchRuntime(config_thief, game_id="t1", sub_game=1, github_commit="x")
    runtime.view.step = 27  # we have played 27 turns of our own
    deliver(runtime, "police", 26, barrier_placed=list(runtime.view.position))
    assert runtime.result["how"] == "trapping barrier"
    assert runtime.view.step == 28, "the concession is a real sealed turn and still counts one"
    assert runtime.steps == 26, "but the GAME ended on the cop's 26th turn, and that is its length"


def test_the_winning_cop_reports_the_turn_it_claimed_on(config_police: ConfigManager) -> None:
    """The mirror: our own claim turn, not the turn the answer arrived on."""
    runtime = MatchRuntime(config_police, game_id="t2", sub_game=1, github_commit="x")
    runtime.view.step = 26
    deliver(runtime, "thief", 27, claim_response={
        "caught": True, "claim": list(runtime.view.position)})
    assert runtime.result["winner"] == "police"
    assert runtime.steps == 26, "the capture happened when we claimed; we have not moved since"


def test_a_conceded_capture_is_dated_by_the_cops_turn_too(config_police: ConfigManager) -> None:
    """A thief that concedes rather than answering settles on the same integer."""
    runtime = MatchRuntime(config_police, game_id="t3", sub_game=1, github_commit="x")
    runtime.view.step = 19
    deliver(runtime, "thief", 20, win_claim={"type": "capture"})
    assert runtime.result["how"] == "conceded"
    assert runtime.steps == 19


def test_survival_is_dated_by_the_thiefs_own_threshold_turn(
    config_thief: ConfigManager, config_police: ConfigManager,
) -> None:
    """Both peers land on the thief's turn number, from opposite sides of the wire."""
    threshold = ConfigManager.load("thief").contract.movement.survival_threshold
    thief = MatchRuntime(config_thief, game_id="t4", sub_game=1, github_commit="x")
    thief.view.step = threshold - 1
    thief.play_turn()
    assert thief.result == {"type": "survival", "winner": "thief"}
    assert thief.steps == threshold

    cop = MatchRuntime(config_police, game_id="t4", sub_game=1, github_commit="x")
    cop.view.step = threshold
    deliver(cop, "thief", threshold, win_claim={"type": "survival"})
    assert cop.result == {"type": "survival", "winner": "thief"}
    assert cop.steps == threshold, "the cop files the thief's number, not its own"


def test_only_the_first_settlement_dates_the_game(config_thief: ConfigManager) -> None:
    """Post-terminal traffic cannot move the length - that is the point of the field."""
    runtime = MatchRuntime(config_thief, game_id="t5", sub_game=1, github_commit="x")
    runtime.view.settle({"type": "capture", "winner": "police", "how": "first"}, 11)
    runtime.view.settle({"type": "survival", "winner": "thief"}, 35)
    assert runtime.result["how"] == "first" and runtime.steps == 11


def test_an_unsettled_game_falls_back_to_our_own_count(config_thief: ConfigManager) -> None:
    """A timeout has no terminal turn; our own count is all either side has."""
    runtime = MatchRuntime(config_thief, game_id="t6", sub_game=1, github_commit="x")
    runtime.view.step = 8
    assert runtime.result is None and runtime.steps == 8
