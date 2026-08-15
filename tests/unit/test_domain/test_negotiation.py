"""Tests for the interoperable handshake - signed terms, locks, pairing."""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.negotiation import (
    TermsRejectedError,
    build_terms,
    validate_terms,
)
from police_thief.shared.config import ConfigManager
from police_thief.shared.interop import (
    SCENT_MODEL_SHA256,
    negotiate_extras,
    sign_terms,
    terms_from_contract,
)


@pytest.fixture
def police(config_dir: Path) -> ConfigManager:
    """The cop side's configuration."""
    return ConfigManager.load("police", config_dir)


@pytest.fixture
def thief(config_dir: Path) -> ConfigManager:
    """The thief side's configuration."""
    return ConfigManager.load("thief", config_dir)


def greeting_of(config: ConfigManager, **overrides):
    """Build one peer's handshake greeting, with overrides applied."""
    base = build_terms(
        config, peer_id="team-x", games_played=2, sub_game=1, step0_commit="c" * 64
    )
    base.update(overrides)
    return base


def check(theirs, ours_config: ConfigManager, expect_role: str = "thief"):
    """Validate a greeting against ours, raising on any refusal."""
    return validate_terms(
        theirs,
        our_terms=terms_from_contract(ours_config.contract),
        our_extras=negotiate_extras(ours_config.role, 1),
        expect_role=expect_role,
    )


def test_the_greeting_carries_the_interop_shape(police: ConfigManager) -> None:
    greeting = greeting_of(police)
    assert set(greeting["terms"].keys()) == {
        "board_size", "smell_grid_size", "decay_per_step", "emit_intensity",
        "min_center_intensity", "max_steps", "barriers_max", "setting",
        "hint_max_words", "axis_origin_corner", "axis_start_index",
        "thief_start", "cop_start", "num_games",
    }
    assert greeting["signature"] == sign_terms(greeting["terms"], greeting["nonce"])
    assert greeting["scent_model_sha256"] == SCENT_MODEL_SHA256
    assert greeting["role"] == "police"
    assert greeting["sub_game_number"] == 1
    assert greeting["counted_games_played"] == 2


def test_matching_greetings_are_accepted(police: ConfigManager, thief: ConfigManager) -> None:
    """Two peers loading byte-identical game.json accept each other."""
    accepted = check(greeting_of(thief), police)
    assert accepted["terms"] == terms_from_contract(police.contract)


def test_a_terms_value_mismatch_is_refused(police: ConfigManager, thief: ConfigManager) -> None:
    greeting = greeting_of(thief)
    greeting["terms"] = dict(greeting["terms"], board_size=9)
    greeting["signature"] = sign_terms(greeting["terms"], greeting["nonce"])
    with pytest.raises(TermsRejectedError, match="board_size"):
        check(greeting, police)


def test_a_bad_signature_is_refused(police: ConfigManager, thief: ConfigManager) -> None:
    greeting = greeting_of(thief, signature="f" * 64)
    with pytest.raises(TermsRejectedError, match="signature"):
        check(greeting, police)


def test_a_scent_model_mismatch_is_refused(police: ConfigManager, thief: ConfigManager) -> None:
    greeting = greeting_of(thief, scent_model_sha256="f" * 64)
    with pytest.raises(TermsRejectedError, match="scent_model"):
        check(greeting, police)


def test_an_omitted_model_family_is_never_refused(
    police: ConfigManager, thief: ConfigManager
) -> None:
    """The unmodified reference peer declares nothing; silence must play."""
    greeting = greeting_of(thief)
    for family in ("scent_model_sha256", "wire_shape_sha256", "info_mode_sha256"):
        greeting.pop(family, None)
    assert check(greeting, police)


def test_a_sub_game_mismatch_is_refused(police: ConfigManager, thief: ConfigManager) -> None:
    with pytest.raises(TermsRejectedError, match="sub-game"):
        check(greeting_of(thief, sub_game_number=4), police)


def test_a_role_clash_is_refused(police: ConfigManager, thief: ConfigManager) -> None:
    with pytest.raises(TermsRejectedError, match="role clash"):
        check(greeting_of(thief, role="police"), police)


def test_uncomparable_pairing_values_are_silence(
    police: ConfigManager, thief: ConfigManager
) -> None:
    """A wrong-typed declaration is treated as silence, not refused."""
    assert check(greeting_of(thief, sub_game_number="three", role=17), police)


def test_non_object_greetings_are_refused(police: ConfigManager) -> None:
    with pytest.raises(TermsRejectedError, match="terms object"):
        check(["not", "a", "greeting"], police)


def test_a_group_id_nested_under_identity_is_accepted(police) -> None:
    """The kit's rule: top-level ``group_id`` OR ``identity.group_id``.

    The first real opponent sent only the nested form; refusing it as
    "group_id None" at kickoff is a false refusal of a valid partner.
    """
    from police_thief.domain.negotiation import build_terms, validate_terms
    from police_thief.shared.interop import negotiate_extras, terms_from_contract

    greeting = build_terms(police, peer_id="moamteam", games_played=0, sub_game=1,
                           step0_commit="c" * 64)
    del greeting["group_id"]
    greeting["identity"] = {"group_id": "moamteam", "group_name": "MOAMTEAM"}
    accepted = validate_terms(
        greeting, our_terms=terms_from_contract(police.contract),
        our_extras=negotiate_extras("thief", 1), expect_role="police",
    )
    assert accepted["group_id"] == "moamteam"
