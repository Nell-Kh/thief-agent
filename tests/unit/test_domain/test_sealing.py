"""Tests for the sealed-record builders and the hardware declaration."""

from __future__ import annotations

from police_thief.domain.crypto import verify
from police_thief.domain.sealing import (
    revealed_move,
    revealed_position,
    sealed,
    step0_record,
    turn_record,
)
from police_thief.domain.state_summary import state_summary
from police_thief.shared.sysinfo import hardware_spec


def _turn(**overrides):
    """A turn record with the given overrides applied before sealing."""
    base = {
        "step": 4,
        "role": "thief",
        "grid_size": 7,
        "position": (3, 5),
        "barriers": frozenset({(1, 1)}),
        "move": "N",
        "intent": "lie",
        "hint": "slipping north past the docks",
        "tokens_step": 0,
        "tokens_total": 120,
    }
    base.update(overrides)
    return turn_record(**base)


def test_the_state_summary_is_canonical() -> None:
    first = state_summary(7, (3, 5), frozenset({(2, 2), (1, 1)}))
    second = state_summary(7, (3, 5), frozenset({(1, 1), (2, 2)}))
    assert first == second
    assert "grid=7x7" in first
    assert "self=[3, 5]" in first


def test_a_turn_record_holds_the_full_truth() -> None:
    payload = _turn()
    assert payload["type"] == "turn"
    assert payload["position"] == [3, 5]
    assert payload["move"] == "move:N"
    assert payload["intent"] == "lie"
    assert payload["tokens_total"] == 120


def test_a_turn_record_seals_and_verifies() -> None:
    record = sealed(_turn())
    assert verify(record["payload"], record["nonce"], record["commit"])


def test_step0_declares_the_mandatory_identity_fields() -> None:
    """github_commit is a mandatory declaration - the exact code that played."""
    payload = step0_record(
        spec={"os": "Linux"},
        model="claude-haiku",
        code_version="1.00",
        github_commit="ade064c",
        group_name="TEAM-TBD",
        sub_game_number=1,
        token_budget=200000,
    )
    assert payload["step"] == 0
    assert payload["type"] == "system_spec"
    assert payload["github_commit"] == "ade064c"
    assert payload["token_budget"] == 200000


def test_step0_seals_and_verifies_like_any_record() -> None:
    record = sealed(step0_record(hardware_spec(), "m", "1.00", "abc", "team", 1, 0))
    assert verify(record["payload"], record["nonce"], record["commit"])


def test_revealed_move_strips_the_prefix() -> None:
    assert revealed_move(_turn()) == "N"
    assert revealed_move({"move": "STAY"}) == "STAY"


def test_revealed_position_is_a_cell_tuple() -> None:
    assert revealed_position(_turn()) == (3, 5)


def test_the_hardware_spec_reports_every_mandated_field() -> None:
    spec = hardware_spec()
    for key in ("os", "cpu_cores", "cpu_mhz", "ram_gb", "gpu", "machine", "python"):
        assert key in spec
    assert spec["cpu_cores"] >= 1
    assert isinstance(spec["gpu"], str) and spec["gpu"]
