"""Tests for the inbound handler: the three tools an opponent may call."""

from __future__ import annotations

import pytest

from police_thief.services.inbound import HandshakeRejectedError, InboundHandler
from police_thief.shared.interop import sign_terms

FLAT_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1,
    "emit_intensity": 0.9, "min_center_intensity": 0.5, "max_steps": 35,
    "barriers_max": 14, "setting": "New York", "hint_max_words": 15,
    "axis_origin_corner": "top-left", "axis_start_index": 0,
    "thief_start": [3, 3], "cop_start": [0, 0], "num_games": 6,
}
NONCE = "a1" * 16
OUR_EXTRAS = {"role": "police", "sub_game_number": 1, "scent_model_sha256": "d" * 64}


def terms(**overrides) -> dict:
    """A greeting's terms, with per-test overrides applied."""
    base = {
        "terms": dict(FLAT_TERMS),
        "nonce": NONCE,
        "signature": sign_terms(FLAT_TERMS, NONCE),
        "role": "thief",
        "sub_game_number": 1,
        "group_id": "team-b",
        "counted_games_played": 2,
        "scent_model_sha256": "d" * 64,
        "step0_commit": "e" * 64,
    }
    base.update(overrides)
    return base


def turn_wire(step: int = 1, sender: str = "thief", **overrides) -> dict:
    """A raw turn message dict, with per-test overrides applied."""
    base = {
        "step": step,
        "sender": sender,
        "hint": "slipping north",
        "smell_grid": {"3,3": 0.9},
        "commit": "a" * 64,
    }
    base.update(overrides)
    return base


@pytest.fixture
def handler() -> InboundHandler:
    """A police peer expecting calls from the thief."""
    return InboundHandler(our_terms=dict(FLAT_TERMS), our_extras=dict(OUR_EXTRAS), expect_role="thief")


def test_matching_terms_are_accepted(handler: InboundHandler) -> None:
    reply = handler.negotiate(terms())
    assert reply["accepted"]
    assert handler.opponent_games_played == 2


def test_a_terms_mismatch_refuses_the_match(handler: InboundHandler) -> None:
    bad = dict(FLAT_TERMS, board_size=9)
    with pytest.raises(HandshakeRejectedError, match="terms mismatch"):
        handler.negotiate(terms(terms=bad, signature=sign_terms(bad, NONCE)))


def test_a_scent_model_mismatch_refuses_the_match(handler: InboundHandler) -> None:
    with pytest.raises(HandshakeRejectedError, match="scent_model"):
        handler.negotiate(terms(scent_model_sha256="f" * 64))


def test_terms_from_the_wrong_role_are_refused(handler: InboundHandler) -> None:
    """Both peers claiming the same side can only deadlock - refuse."""
    with pytest.raises(HandshakeRejectedError, match="role clash"):
        handler.negotiate(terms(role="police"))


def test_no_games_count_before_negotiation(handler: InboundHandler) -> None:
    assert handler.opponent_games_played is None


def test_a_turn_is_queued_and_its_commitment_recorded(handler: InboundHandler) -> None:
    reply = handler.receive_turn(turn_wire(step=1))
    assert reply["ok"]
    assert handler.commitments[1] == "a" * 64
    message = handler.next_turn()
    assert message is not None and message.step == 1
    assert handler.next_turn() is None


def test_next_step_reports_the_step_still_awaited(handler: InboundHandler) -> None:
    """The series drivers name this step when a turn wait times out.

    It is read straight off the reorder buffer. The drivers referenced it before
    the handler exposed it, which crashed ``play_networked`` with an
    ``AttributeError`` on the very first turn of every sub-game.
    """
    assert handler.next_step == 1
    handler.receive_turn(turn_wire(step=1))
    assert handler.next_step == 2


def test_a_turn_from_the_wrong_role_is_refused(handler: InboundHandler) -> None:
    with pytest.raises(HandshakeRejectedError, match="expected a turn from 'thief'"):
        handler.receive_turn(turn_wire(sender="police"))


def test_a_second_commitment_for_a_step_is_refused(handler: InboundHandler) -> None:
    """Once sealed, a move cannot be replaced."""
    handler.receive_turn(turn_wire(step=1))
    with pytest.raises(HandshakeRejectedError, match="already committed"):
        handler.receive_turn(turn_wire(step=1, commit="b" * 64))

def test_a_concession_records_the_final_commit_without_overwriting(handler: InboundHandler) -> None:
    # First commit for step 1
    handler.receive_turn(turn_wire(step=1, commit="a" * 64))

    # Thief concedes on step 1 with a new commit
    reply = handler.receive_turn(turn_wire(step=1, commit="b" * 64, claim_response={"claim": [3, 3], "caught": True}))
    assert reply["ok"]

    # Original step commitment is preserved
    assert handler.commitments[1] == "a" * 64
    # The concession commit is stored separately
    assert handler.final_commit == "b" * 64


def test_a_same_step_survival_claim_with_a_new_commit_is_refused(handler: InboundHandler) -> None:
    handler.receive_turn(turn_wire(step=1, commit="a" * 64))
    with pytest.raises(HandshakeRejectedError, match="already committed"):
        handler.receive_turn(turn_wire(step=1, commit="b" * 64, win_claim={"type": "survival"}))


def test_a_cleartext_position_is_refused_at_the_door(handler: InboundHandler) -> None:
    from police_thief.domain.turnmsg import TurnMessageError

    with pytest.raises(TurnMessageError, match="must not carry 'position'"):
        handler.receive_turn(turn_wire(position=[3, 3]))


def test_an_audit_disclosure_is_stored(handler: InboundHandler) -> None:
    reply = handler.submit_audit({"sender": "thief", "records": [1, 2], "result_claim": {}})
    assert reply["records"] == 2
    assert handler.audit is not None


def test_an_audit_without_records_is_refused(handler: InboundHandler) -> None:
    with pytest.raises(HandshakeRejectedError, match="must carry a list of records"):
        handler.submit_audit({"sender": "thief"})


def test_an_audit_with_a_non_list_records_field_is_refused(handler: InboundHandler) -> None:
    with pytest.raises(HandshakeRejectedError, match="must carry a list of records"):
        handler.submit_audit({"sender": "thief", "records": "not-a-list"})


def test_an_audit_from_the_wrong_role_is_refused(handler: InboundHandler) -> None:
    with pytest.raises(HandshakeRejectedError, match="expected an audit"):
        handler.submit_audit({"sender": "police", "records": []})
