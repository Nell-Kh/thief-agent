"""Recomputation against the kit's own settlement artifacts - byte equality or nothing.

Two suites: the ``report_consensus`` vectors pin the spaced serialization and
the sign-then-insert discipline; the vendored example result file
(``kit_example_result.json``, the kit's counted-series bundle) proves that OUR
production ``result_payload`` - fed the example's own rows - reproduces the
kit's aggregate and its ``mutual_agreement.sha256`` exactly. That is the hash
the league joins both teams' emails on: equal settles the series, different
zeroes both teams.
"""

from __future__ import annotations

import json
from pathlib import Path

from police_thief.constants import AGENT_REPORT_ADDRESS
from police_thief.infra.email.consensus import (
    consensus_signature,
    mutual_agreement_hash,
    mutual_agreement_scope,
    series_aggregate,
    sign_report,
    verify_signed_report,
)
from police_thief.infra.email.reports import result_payload
from police_thief.shared.config import ConfigManager
from police_thief.shared.config_io import sha256_of

VECTORS = Path(__file__).resolve().parents[1] / "vectors"


def load(name: str) -> dict:
    """Read one vendored kit vector by name."""
    return json.loads((VECTORS / f"{name}.json").read_text(encoding="utf-8"))


# --- the consensus signature vectors (kit §6) -------------------------------


def test_the_consensus_signature_matches_every_kit_vector() -> None:
    for case in load("report_consensus")["vectors"]:
        assert consensus_signature(case["report"]) == case["signature"], case["note"]
        assert sign_report(case["report"]) == case["signed_report"], case["note"]
        assert verify_signed_report(case["signed_report"]), case["note"]


def test_the_compact_form_is_provably_the_wrong_one() -> None:
    """The vectors carry the compact hash as a contrast - we must NOT produce it."""
    for case in load("report_consensus")["vectors"]:
        assert sha256_of(case["report"]) == case["compact_form_sha256"], case["note"]
        assert consensus_signature(case["report"]) != case["compact_form_sha256"]


# --- the kit's counted-series example, recomputed by OUR production code ----


def test_our_aggregate_reproduces_the_kit_examples_final_result() -> None:
    example = load("kit_example_result")
    tie_score = ConfigManager.load("police").contract.scoring.tie_score
    aggregate = series_aggregate(example["sub_games"], tie_score=tie_score)
    expected = {key: example["final_result"][key] for key in aggregate}
    assert aggregate == expected


def test_our_mutual_agreement_hash_matches_the_kit_example_byte_for_byte() -> None:
    example = load("kit_example_result")
    tie_score = ConfigManager.load("police").contract.scoring.tie_score
    aggregate = series_aggregate(example["sub_games"], tie_score=tie_score)
    scope = mutual_agreement_scope(example["game_id"], example["sub_games"], aggregate)
    assert mutual_agreement_hash(scope) == example["mutual_agreement"]["sha256"]


def test_the_production_result_builder_reproduces_the_kit_example() -> None:
    """Not a hand-built demo dict - the SHIPPED builder, fed the example's rows."""
    example = load("kit_example_result")
    tie_score = ConfigManager.load("police").contract.scoring.tie_score
    ours = result_payload(
        game_uid=example["game_uid"], game_id=example["game_id"], links=example["links"],
        timezone=example["timezone"], group_ids=example["groups"],
        sub_games=example["sub_games"], tie_score=tie_score,
        games_played=example["final_result"]["games_played_including_this"],
        first_meeting=example["final_result"]["first_meeting_between_groups"],
        counted=True, recipient=AGENT_REPORT_ADDRESS,
    )
    for key in ("game_uid", "game_id", "report_type", "groups", "num_sub_games",
                "sub_games", "final_result", "mutual_agreement", "schema_version"):
        assert ours[key] == example[key], key
