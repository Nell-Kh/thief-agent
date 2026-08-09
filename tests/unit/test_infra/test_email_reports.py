"""Tests for the lifecycle reports in the league's joined shape (kit schema 1.1)."""

from __future__ import annotations

import json
from pathlib import Path

from police_thief.constants import AGENT_REPORT_ADDRESS
from police_thief.infra.email.naming import (
    config_file_name,
    declaration_file_name,
    result_file_name,
    write_lifecycle_file,
)
from police_thief.infra.email.report_blocks import group_block, links_block
from police_thief.infra.email.reports import (
    config_payload,
    declaration_payload,
    result_payload,
)
from police_thief.shared.config_io import canonical_json, sha256_of

RECIPIENT = AGENT_REPORT_ADDRESS
A, B = "team-north", "team-south"
GITHUB = {
    A: {"cop": "https://github.com/north/cop", "thief": "https://github.com/north/thief"},
    B: {"cop": "https://github.com/south/cop", "thief": "https://github.com/south/thief"},
}
LINKS = links_block("north-vs-south", GITHUB)


def make_group(gid: str) -> dict:
    """One team's declaration block with placeholder identity."""
    return group_block(
        group_id=gid, group_name=gid, members=["m1", "m2"], repos=GITHUB[gid],
        mcp_servers={"cop": f"https://{gid}.example/mcp"}, llm_model="template",
        hardware_spec={"cpu": "arm", "ram_gb": 16}, github_commit="a" * 40,
        counted_games_played=0, code_version="1.0",
    )


def make_row(number: int, winner: str, score_a: int, score_b: int, *, tie: bool = False) -> dict:
    """One sub-game result row."""
    return {
        "sub_game_number": number, "roles": {A: "police", B: "thief"},
        "started_at": "2026-08-04T10:00:00+03:00", "ended_at": "2026-08-04T10:00:09+03:00",
        "result": "capture", "winner_group": winner, "tie": tie, "steps": 6,
        "github_commit": {A: "a" * 40, B: "b" * 40}, "tokens": {A: 3, B: 4},
        "score": {A: score_a, B: score_b},
        "log_files": {A: "log_g01.json", B: "log_g01.json"},
        "audit": {"log_verified": True, "tampered": False},
    }


def make_result(rows: list[dict], **overrides) -> dict:
    """A full result payload, with per-test overrides applied."""
    kwargs = {
        "game_uid": "uid-7", "game_id": "north-vs-south", "links": LINKS,
        "timezone": "Asia/Jerusalem", "group_ids": [A, B], "sub_games": rows,
        "tie_score": 2, "games_played": {A: 1, B: None}, "first_meeting": True,
        "recipient": RECIPIENT,
    }
    kwargs.update(overrides)
    return result_payload(**kwargs)


def test_the_group_block_signature_is_sign_then_insert() -> None:
    block = make_group(A)
    signature = block.pop("signature")
    assert signature == "sha256:" + sha256_of(block)  # its own key excluded


def test_the_declaration_freezes_the_series_constants() -> None:
    record = declaration_payload(
        game_uid="uid-7", game_id="north-vs-south", links=LINKS, timezone="Asia/Jerusalem",
        started_at="2026-08-04T10:00:00+03:00", num_sub_games=6, max_tokens_per_game=200000,
        groups=[make_group(A), make_group(B)], recipient=RECIPIENT,
    )
    assert record["declaration_type"] == "pre_game_declaration"
    assert record["groups"]["group_1"]["group_id"] == A
    assert record["links"]["github"] == GITHUB  # all four links - ch. 9.4
    assert record["league"] == {"counted": True, "reason": "counted"}
    assert "ended_at" not in record  # nothing here is known only after the games


def test_a_friendly_declaration_rides_disarmed() -> None:
    record = declaration_payload(
        game_uid="u", game_id="g", links=LINKS, timezone="Asia/Jerusalem",
        started_at="t", num_sub_games=1, max_tokens_per_game=0,
        groups=[make_group(A), make_group(B)], counted=False, recipient=RECIPIENT,
    )
    assert record["league"] == {"counted": False, "reason": "friendly"}


def test_the_config_file_lets_an_auditor_rederive_the_uid() -> None:
    terms = {"grid_size": 7, "num_barriers": 5}
    record = config_payload("uid-7", "north-vs-south", 3, terms, LINKS, RECIPIENT)
    assert record["config_sha256"] == sha256_of(terms)
    assert record["terms"] == terms  # the preimage itself rides along
    assert record["sub_game_number"] == 3
    assert record["config_name"] == "config_north-vs-south_g03.json"


def test_the_result_aggregate_is_derived_from_the_rows() -> None:
    rows = [make_row(1, A, 20, 5), make_row(2, A, 20, 5)]
    record = make_result(rows)
    final = record["final_result"]
    assert final["total_score"] == {A: 40, B: 10}
    assert final["sub_games_won"] == {A: 2, B: 0}
    assert final["winner_group"] == A and final["series_tie"] is False
    assert final["tokens_total_series"] == {A: 6, B: 8}  # summed from the rows
    assert final["games_played_including_this"] == {A: 1, B: None}  # theirs unclaimed
    assert record["mutual_agreement"]["confirmed"] is True


def test_a_series_tie_adds_the_tie_score_into_both_totals() -> None:
    rows = [make_row(1, A, 20, 5), make_row(2, B, 5, 20)]
    final = make_result(rows)["final_result"]
    assert final["series_tie"] is True and final["winner_group"] is None
    assert final["total_score"] == {A: 27, B: 27}  # 25 + the App. F tie award


def test_the_diversity_award_is_a_flag_and_never_enters_the_totals() -> None:
    rows = [make_row(1, A, 20, 5)]
    final = make_result(rows)["final_result"]
    assert final["diversity_reward_applied"] == {A: True, B: False}
    assert final["total_score"][A] == 20  # the pure sum, +10 nowhere
    friendly = make_result(rows, counted=False)["final_result"]
    assert friendly["diversity_reward_applied"] == {A: False, B: False}


def test_a_counted_claim_arms_when_addressed_to_the_binding_league_address() -> None:
    record = make_result([make_row(1, A, 20, 5)])
    assert record["league"] == {"counted": True, "reason": "counted"}


def test_a_counted_claim_disarms_when_the_recipient_is_not_the_binding_address() -> None:
    rows = [make_row(1, A, 20, 5)]
    record = make_result(rows, recipient="someone-else@example.com")
    assert record["league"] == {
        "counted": False,
        "reason": "counted-blocked: recipient is not the binding league address",
    }
    # A disarmed claim never triggers the diversity award either - same guard.
    assert record["final_result"]["diversity_reward_applied"] == {A: False, B: False}


def test_file_names_derive_from_the_game_id() -> None:
    assert declaration_file_name("G7") == "declaration_G7.json"
    assert config_file_name("G7", 4) == "config_G7_g04.json"
    assert result_file_name("G7") == "result_G7.json"


def test_lifecycle_files_are_canonical_json_on_disk(tmp_path: Path) -> None:
    record = config_payload("uid-7", "G7", 1, {"a": 1}, LINKS, RECIPIENT)
    path = write_lifecycle_file(tmp_path / "results", config_file_name("G7", 1), record)
    text = path.read_text(encoding="utf-8")
    assert text == canonical_json(record)  # byte-identical to the mailed copy
    assert json.loads(text) == record


def test_the_binding_report_address_is_the_rulebooks() -> None:
    assert AGENT_REPORT_ADDRESS == "rmisegal+uoh26finalgame@gmail.com"
