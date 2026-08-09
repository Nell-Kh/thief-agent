"""Conformance against the league interop kit's vendored vectors.

The kit (copthief-league-protocol, MIT - vendored under ``tests/vectors``)
pins the byte-level constructions two independent implementations must agree
on, because a mismatch at the audit scores BOTH teams zero. Every test here
feeds a kit vector through OUR code and demands byte equality - the same
certification `verify_vectors.py` gives the kit itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from police_thief.domain.crypto import digest_of
from police_thief.domain.scent import ScentField, emission_delta
from police_thief.shared.config import ConfigManager
from police_thief.shared.config_io import canonical_json, sha256_of
from police_thief.shared.interop import (
    INFO_MODE_SHA256,
    SCENT_MODEL_DOC,
    SCENT_MODEL_SHA256,
    WIRE_SHAPE_SHA256,
    derive_game_ids,
    scent_model_lock,
    sign_terms,
    terms_from_contract,
)
from police_thief.shared.schema import PheromoneConfig

VECTORS = Path(__file__).resolve().parents[1] / "vectors"


def load(name: str) -> dict:
    """Read one vendored kit vector by name."""
    return json.loads((VECTORS / f"{name}.json").read_text(encoding="utf-8"))


# --- canonical JSON (kit §2): the serialization under every hash ------------


def test_canonical_json_matches_every_kit_vector() -> None:
    for case in load("canonical_json")["vectors"]:
        assert canonical_json(case["object"]) == case["canonical"], case["note"]
        assert sha256_of(case["object"]) == case["sha256"], case["note"]


# --- commit-reveal (kit §3): the opponent re-hashes our revealed log --------


def test_commit_construction_matches_every_kit_vector() -> None:
    for case in load("commit_reveal")["vectors"]:
        assert digest_of(case["payload"], case["nonce"]) == case["commit"], case["note"]


# --- terms signature and shared game ids (kit §4) ---------------------------


def test_terms_signature_matches_the_kit_vectors() -> None:
    for case in load("terms_signature")["vectors"]:
        assert sign_terms(case["terms"], case["nonce"]) == case["signature"]


def test_game_ids_match_the_kit_vectors() -> None:
    for case in load("game_uid")["vectors"]:
        game_id, game_uid = derive_game_ids(case["terms"], case["group_a"], case["group_b"])
        assert game_id == case["game_id"], case.get("note", "")
        assert game_uid == case["game_uid"], case.get("note", "")


def test_our_contract_produces_the_full_flat_term_set() -> None:
    """Our extraction carries exactly the kit's 14 keys - no more, no fewer."""
    contract = ConfigManager.load("police").contract
    terms = terms_from_contract(contract)
    kit_keys = set(load("terms_signature")["vectors"][0]["terms"].keys())
    assert set(terms.keys()) == kit_keys


# --- the scent model (kit §5.1, multiplicative_book_v1) ---------------------


@pytest.fixture(scope="module")
def scent_config() -> PheromoneConfig:
    """The pheromone parameters the vendored scent vectors are pinned against."""
    return ConfigManager.load("police").contract.pheromones


def test_the_kernel_is_the_printed_matrix_verbatim(scent_config: PheromoneConfig) -> None:
    """Byte-exact doubles: a computed kernel drifts one IEEE bit off 0.42."""
    kernel = load("scent_book_v3")["model"]["params"]["kernel"]
    for row_offset in range(-2, 3):
        for col_offset in range(-2, 3):
            expected = kernel[row_offset + 2][col_offset + 2]
            got = emission_delta(scent_config, (3, 3), (3 + row_offset, 3 + col_offset))
            assert got == expected, f"offset ({row_offset},{col_offset})"


def test_emission_on_an_empty_field_matches_the_fixture(
    scent_config: PheromoneConfig,
) -> None:
    for case in load("scent_book_v3")["emit"]:
        field = ScentField(7, scent_config)
        field.advance(tuple(case["center"]))
        got = {f"{r},{c}": v for (r, c), v in field.snapshot().items()}
        assert got == case["field"], case["note"]


def test_the_field_walk_reproduces_every_turn(scent_config: PheromoneConfig) -> None:
    walk = load("scent_book_v3")["field_walk"]
    field = ScentField(int(walk["board_size"]), scent_config)
    for turn in walk["turns"]:
        field.advance(tuple(turn["center"]))
        got = {f"{r},{c}": v for (r, c), v in field.snapshot().items()}
        assert got == turn["field"], turn.get("note", "")


def test_the_clamp_case_from_the_registered_doc(scent_config: PheromoneConfig) -> None:
    """A saturated cell decays then takes an adjacent deposit: clamped at 0.9."""
    example = SCENT_MODEL_DOC["example"]
    raw = (1.0 - scent_config.decay) * example["tau"] + example["delta"]
    assert raw == example["raw"]  # the exact IEEE double, no rounding
    assert min(scent_config.center_intensity, raw) == example["clamped"]


# --- locked-model declarations (kit §7) -------------------------------------


def test_our_scent_model_declaration_is_the_registered_hash() -> None:
    assert scent_model_lock() == SCENT_MODEL_SHA256


def test_all_three_declared_hashes_match_the_kit_registry() -> None:
    registered = {
        (item["doc"]["family"], item["doc"]["name"]): item["sha256"]
        for item in load("locked_model")["registered"]
    }
    assert registered[("scent_model", "multiplicative_book_v1")] == SCENT_MODEL_SHA256
    assert registered[("wire_shape", "reference-v3")] == WIRE_SHAPE_SHA256
    assert registered[("info_mode", "belief")] == INFO_MODE_SHA256
    # and the registry hash really is the hash of the registered doc
    for item in load("locked_model")["registered"]:
        assert sha256_of(item["doc"]) == item["sha256"], item["doc"]["name"]
