"""Conformance against the kit's at-least-once delivery contract (kit §7.1).

Split out of ``test_kit_vectors.py`` to keep both files under the 150-code-line
law: this file owns the ``delivery_contract.json`` decision table (apply /
absorb / equivocation / buffer / violation / discard) and the reorder-buffer
behavior it implies, while ``test_kit_vectors.py`` keeps the static byte-exact
vector conformance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from police_thief.shared.config import ConfigManager
from police_thief.shared.interop import terms_from_contract

VECTORS = Path(__file__).resolve().parents[1] / "vectors"


def load(name: str) -> dict:
    """Read one vendored kit vector file by name."""
    return json.loads((VECTORS / f"{name}.json").read_text(encoding="utf-8"))


def _turn_message(step: int, commit: str) -> dict:
    """A minimal well-formed turn message for the delivery decision table."""
    return {"step": step, "sender": "thief", "hint": "", "smell_grid": {}, "commit": commit}


def setup_receiver(config_dir: Path, reorder_window: int = 2):
    """Build an InboundHandler + MatchRuntime pair already at opponent step 2."""
    from police_thief.services.inbound import InboundHandler
    from police_thief.services.match_runtime import MatchRuntime

    config = ConfigManager.load("police", config_dir)
    runtime = MatchRuntime(config, game_id="interop", sub_game=1, github_commit="x")
    handler = InboundHandler(
        our_terms=terms_from_contract(config.contract),
        our_extras={},
        expect_role="thief",
        reorder_window=reorder_window,
    )
    for step in (1, 2):
        res = handler.receive_turn(_turn_message(step, f"c{step}"))
        assert res["ok"]
        turn = handler.next_turn()
        assert turn is not None
        runtime.on_turn(turn)

    assert runtime.view.opponent_step == 2
    return handler, runtime


def test_delivery_contract_arrivals(config_dir: Path) -> None:
    """Every arrival case in the kit's delivery decision table, applied in order."""
    from police_thief.services.inbound import HandshakeRejectedError

    vector = load("delivery_contract")

    for row in vector["arrivals"]:
        handler, runtime = setup_receiver(config_dir)
        arrival = row["arrival"]
        decision = row["decision"]
        msg = _turn_message(arrival["step"], arrival["commit"])

        if decision in ("apply", "violation"):
            res = handler.receive_turn(msg)
            assert res["ok"]
            turn = handler.next_turn()
            assert turn is not None
            runtime.on_turn(turn)
            if decision == "apply":
                assert runtime.view.opponent_step == arrival["step"]
                assert runtime.result is None
            else:
                assert runtime.result is not None
                assert runtime.result["type"] == "technical_loss"

        elif decision == "equivocation":
            with pytest.raises(HandshakeRejectedError, match="already committed"):
                handler.receive_turn(msg)

        else:  # absorb, buffer, discard: accepted but nothing new to apply yet
            res = handler.receive_turn(msg)
            assert res["ok"]
            assert handler.next_turn() is None


def test_no_reorder_window(config_dir: Path) -> None:
    """With the reorder window disabled, an out-of-order step is refused outright."""
    vector = load("delivery_contract")
    row = vector["no_reorder_window"]

    handler, runtime = setup_receiver(config_dir, reorder_window=0)
    arrival = row["arrival"]
    msg = _turn_message(arrival["step"], arrival["commit"])

    res = handler.receive_turn(msg)
    assert res["ok"]
    turn = handler.next_turn()
    assert turn is not None
    runtime.on_turn(turn)
    assert runtime.result is not None
    assert runtime.result["type"] == "technical_loss"


def test_buffered_steps_replay_in_order(config_dir: Path) -> None:
    handler, runtime = setup_receiver(config_dir)

    res_4 = handler.receive_turn(_turn_message(4, "c4"))
    assert res_4["ok"]
    assert handler.next_turn() is None

    res_3 = handler.receive_turn(_turn_message(3, "c3"))
    assert res_3["ok"]

    t3 = handler.next_turn()
    assert t3 is not None and t3.step == 3
    t4 = handler.next_turn()
    assert t4 is not None and t4.step == 4
    assert handler.next_turn() is None

    runtime.on_turn(t3)
    runtime.on_turn(t4)
    assert runtime.result is None
    assert runtime.view.opponent_step == 4
