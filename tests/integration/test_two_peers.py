"""A complete networked mini-game between two full runtimes.

The two peers exchange only what the wire allows - commitments, hints, scent,
public events - play to a verdict, then disclose everything and audit each
other. Both the hash layer and the physics layer must pass on both sides, and
the two independently reached results must agree. This is the whole system in
one test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.audit import audit_disclosure
from police_thief.services.match_runtime import MatchRuntime
from police_thief.shared.config import ConfigManager

SAFETY_CAP = 90


@pytest.fixture
def peers(config_dir: Path) -> tuple[MatchRuntime, MatchRuntime]:
    """Two independent runtimes, cop and thief, that only ever exchange messages."""
    police = MatchRuntime(
        ConfigManager.load("police", config_dir), game_id="itest", sub_game=1,
        github_commit="deadbeef",
    )
    thief = MatchRuntime(
        ConfigManager.load("thief", config_dir), game_id="itest", sub_game=1,
        github_commit="deadbeef",
    )
    return police, thief


def deliver(receiver: MatchRuntime, sender: MatchRuntime, message) -> None:
    """Hand a message over, and route back any immediate reply (a concession)."""
    reply = receiver.on_turn(message)
    if reply is not None:
        sender.on_turn(reply)


def play_out(police: MatchRuntime, thief: MatchRuntime) -> None:
    """Alternate turns - thief first - delivering each message to the other."""
    for _ in range(SAFETY_CAP):
        if thief.ended and police.ended:
            return
        if not thief.ended:
            deliver(police, thief, thief.play_turn())
        if police.ended and thief.ended:
            return
        if not police.ended:
            deliver(thief, police, police.play_turn())
    raise AssertionError("the match did not terminate inside the safety cap")


def test_a_full_match_reaches_an_agreed_verdict(peers) -> None:
    police, thief = peers
    play_out(police, thief)
    assert police.result is not None and thief.result is not None
    assert police.result["type"] == thief.result["type"]
    assert police.result["winner"] == thief.result["winner"]
    assert police.result["type"] in {"capture", "survival"}


def test_the_shipped_mirror_match_settles_on_an_agreed_verdict(peers) -> None:
    """The shipped pair against itself, through the real blind pipeline.

    History, because this test has now asserted both answers more than once.
    The wall cop lost six sub-games out of six to the evader in the first
    internet rehearsal; the seal cop was written to beat it - commitment rather
    than information: cross the door and spend a stone ON it - and did; the
    emitter fit then let every barrier cop beat it; round 4 gave the thief an
    ``openness`` that counts a stone as a wall, which put it back in front of
    everything in the tree; and round 5 (``brain/box.py``) kept seal's opening
    and replaced its endgame with a two-ply search, which boxes the evader in
    the sealed chamber where the region hunt danced - so the mirror is a
    capture again.

    So the verdict this mirror settles on is not the invariant - the race keeps
    moving it, and tests/integration/test_strategy_selection.py is where that
    fact is owned and re-derived. What must hold here is what this file is for:
    two independent peers, exchanging only what the wire allows, agreeing on ONE
    verdict, with the shipped brains rather than doubles.
    """
    police, thief = peers
    play_out(police, thief)
    assert police.result["type"] == thief.result["type"] == "capture"
    assert police.result["winner"] == thief.result["winner"] == "police"


def test_the_mutual_audit_passes_on_both_sides(peers) -> None:
    police, thief = peers
    play_out(police, thief)
    police_report = audit_disclosure(police.disclosure(), police.contract)
    thief_report = audit_disclosure(thief.disclosure(), thief.contract)
    assert police_report.passed, police_report.violations
    assert thief_report.passed, thief_report.violations
    assert police_report.verdict == "Verified OK"
    assert thief_report.verdict == "Verified OK"


def test_a_forged_disclosure_is_caught_by_the_other_side(peers) -> None:
    police, thief = peers
    play_out(police, thief)
    disclosure = thief.disclosure()
    turn_records = [r for r in disclosure["records"] if r["payload"].get("type") == "turn"]
    turn_records[0]["payload"]["position"] = [6, 6]  # rewrite history
    report = audit_disclosure(disclosure, police.contract)
    assert not report.passed
    assert report.verdict == "TAMPERED"


def test_no_cleartext_position_ever_crossed_the_wire(peers) -> None:
    police, thief = peers
    messages = []
    for _ in range(10):
        if not thief.ended:
            message = thief.play_turn()
            messages.append(message)
            police.on_turn(message)
        if not police.ended:
            message = police.play_turn()
            messages.append(message)
            thief.on_turn(message)
    for message in messages:
        wire = message.to_wire()
        assert "position" not in wire and "move" not in wire and "intent" not in wire


def test_scoring_follows_the_agreed_verdict(peers) -> None:
    police, thief = peers
    play_out(police, thief)
    if police.result["type"] == "capture":
        assert police.points() == 20 and thief.points() == 5
    else:
        assert police.points() == 5 and thief.points() == 10


def test_the_match_is_reproducible(config_dir: Path) -> None:
    """Deterministic brains and templates: the same match replays identically."""

    def run() -> tuple:
        """Play a whole match between the two peers over messages alone."""
        police = MatchRuntime(
            ConfigManager.load("police", config_dir), "itest", 1, "deadbeef"
        )
        thief = MatchRuntime(
            ConfigManager.load("thief", config_dir), "itest", 1, "deadbeef"
        )
        play_out(police, thief)
        return police.result, thief.result, police.view.step, thief.view.step

    assert run() == run()


def test_step0_is_sealed_before_the_first_move(peers) -> None:
    police, _thief = peers
    assert police.step0["payload"]["type"] == "system_spec"
    assert police.step0["payload"]["github_commit"] == "deadbeef"
    assert len(police.step0_commit) == 64
