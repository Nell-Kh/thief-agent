"""Tests for the turn-message wire format."""

from __future__ import annotations

import pytest

from police_thief.domain.turnmsg import (
    TurnMessage,
    TurnMessageError,
    decode_scent,
    encode_scent,
)


def message(**overrides) -> dict:
    """A valid wire message, with per-test overrides applied."""
    wire = {
        "step": 3,
        "sender": "thief",
        "hint": "slipping north past Times Square",
        "smell_grid": {"3,5": 0.9, "4,5": 0.62},
        "commit": "a" * 64,
        "barrier_placed": None,
        "capture_claim": None,
        "claim_response": None,
        "win_claim": None,
    }
    wire.update(overrides)
    return wire


def test_scent_encoding_round_trips() -> None:
    snapshot = {(3, 5): 0.9, (4, 5): 0.62}
    assert decode_scent(encode_scent(snapshot)) == snapshot


def test_quiet_cells_are_not_transmitted() -> None:
    assert encode_scent({(1, 1): 0.0, (2, 2): 0.5}) == {"2,2": 0.5}


def test_a_bad_scent_key_is_rejected() -> None:
    with pytest.raises(TurnMessageError, match="bad scent cell"):
        decode_scent({"not-a-cell": 0.5})


def test_a_valid_message_parses_and_round_trips() -> None:
    parsed = TurnMessage.from_wire(message())
    assert parsed.step == 3
    assert parsed.sender == "thief"
    assert parsed.commit == "a" * 64
    wire_out = parsed.to_wire()
    wire_out.pop("timestamp", None)
    assert TurnMessage.from_wire(wire_out) == parsed


def test_every_mandatory_field_is_required() -> None:
    for name in ("step", "sender", "hint", "smell_grid", "commit"):
        wire = message()
        del wire[name]
        with pytest.raises(TurnMessageError, match=f"missing field '{name}'"):
            TurnMessage.from_wire(wire)


def test_an_unknown_sender_is_rejected() -> None:
    with pytest.raises(TurnMessageError, match="unknown sender"):
        TurnMessage.from_wire(message(sender="burglar"))


def test_a_negative_step_is_rejected() -> None:
    with pytest.raises(TurnMessageError, match="must not be negative"):
        TurnMessage.from_wire(message(step=-1))


def test_an_empty_commit_is_rejected() -> None:
    with pytest.raises(TurnMessageError, match="must not be empty"):
        TurnMessage.from_wire(message(commit=""))


@pytest.mark.parametrize("leak", ["position", "move", "intent"])
def test_cleartext_position_fields_are_refused(leak: str) -> None:
    """ADR-7: the true move and position never cross the wire in the clear."""
    with pytest.raises(TurnMessageError, match=f"must not carry '{leak}'"):
        TurnMessage.from_wire(message(**{leak: [3, 3]}))


def test_public_events_are_carried_when_present() -> None:
    parsed = TurnMessage.from_wire(
        message(
            barrier_placed=[2, 3],
            capture_claim=[3, 3],
            claim_response={"claim": [3, 3], "caught": False},
            win_claim={"type": "survival"},
        )
    )
    assert parsed.barrier_placed == [2, 3]
    assert parsed.capture_claim == [3, 3]
    assert parsed.claim_response == {"claim": [3, 3], "caught": False}
    assert parsed.win_claim == {"type": "survival"}


def test_a_malformed_public_cell_is_rejected() -> None:
    with pytest.raises(TurnMessageError, match="must be \\[row, col\\]"):
        TurnMessage.from_wire(message(barrier_placed=[1]))


def test_unknown_extra_fields_survive_the_round_trip() -> None:
    """Forward compatibility: an opponent may send fields we do not know."""
    parsed = TurnMessage.from_wire(message(timestamp="2026-08-04T17:00:00Z"))
    assert parsed.extras["timestamp"] == "2026-08-04T17:00:00Z"
    assert parsed.to_wire()["timestamp"] == "2026-08-04T17:00:00Z"


def test_a_non_object_message_is_rejected() -> None:
    with pytest.raises(TurnMessageError, match="must be an object"):
        TurnMessage.from_wire(["not", "a", "dict"])  # type: ignore[arg-type]
