"""Tests for the pre-game agreement check - it must find what the handshake refuses."""

from __future__ import annotations

import pytest

from police_thief.domain.crypto import new_nonce
from police_thief.domain.negotiation import TermsRejectedError, validate_terms
from police_thief.shared.config import ConfigManager
from police_thief.shared.config_io import ConfigError
from police_thief.shared.interop import negotiate_extras, sign_terms, terms_from_contract
from police_thief.shared.preflight import (
    ABSENT,
    compare_signed_terms,
    report_lines,
    terms_from_raw,
    would_handshake,
)


@pytest.fixture(scope="module")
def our_terms() -> dict:
    """The signed terms this peer would present."""
    return terms_from_contract(ConfigManager.load("police").contract)


def test_identical_terms_report_no_difference(our_terms: dict) -> None:
    assert compare_signed_terms(our_terms, dict(our_terms)) == []
    assert would_handshake([]) is True


def test_a_differing_arena_is_found(our_terms: dict) -> None:
    """The exact live case: two teams on different map_area values."""
    theirs = {**our_terms, "setting": "New York"}
    differences = compare_signed_terms(our_terms, theirs)
    assert [d.key for d in differences] == ["setting"]
    assert differences[0].theirs == "New York"
    assert would_handshake(differences) is False


def test_a_missing_term_is_absent_not_skipped(our_terms: dict) -> None:
    """An omitted key still breaks the handshake's equality - it must be reported."""
    theirs = {key: value for key, value in our_terms.items() if key != "min_center_intensity"}
    differences = compare_signed_terms(our_terms, theirs)
    assert [d.key for d in differences] == ["min_center_intensity"]
    assert differences[0].theirs == ABSENT


def test_the_check_agrees_with_the_real_handshake(our_terms: dict) -> None:
    """The whole point: whatever preflight passes, validate_terms must accept.

    Two independent code paths decide the same question; if they ever diverge
    the check becomes a false reassurance, which is worse than no check.
    """
    for theirs, expected_ok in (
        (dict(our_terms), True),
        ({**our_terms, "setting": "New York"}, False),
        ({**our_terms, "max_steps": 40}, False),
    ):
        preflight_ok = would_handshake(compare_signed_terms(our_terms, theirs))
        nonce = new_nonce()
        greeting = {
            "terms": theirs, "nonce": nonce, "signature": sign_terms(theirs, nonce),
            "group_id": "them", "role": "thief",
        }
        try:
            validate_terms(greeting, our_terms=our_terms,
                           our_extras=negotiate_extras("police", 1), expect_role="thief")
            handshake_ok = True
        except TermsRejectedError:
            handshake_ok = False
        assert preflight_ok == handshake_ok == expected_ok


def test_a_config_missing_a_required_key_is_rejected_loudly() -> None:
    """A file our contract cannot load is a finding, not a crash to discover live."""
    with pytest.raises(ConfigError):
        terms_from_raw({"board_and_agents": {"grid_size": 7}})


def test_the_report_names_blockers_and_the_unreadable_questions(our_terms: dict) -> None:
    differences = compare_signed_terms(our_terms, {**our_terms, "setting": "New York"})
    text = "\n".join(report_lines(differences, negotiate_extras("thief", 1), "thief"))
    assert "BLOCKER" in text and "setting" in text
    assert "scent model" in text  # not in any config file - must be asked
    assert "group_id" in text
    assert "thief" in text  # our role, so the complement is unambiguous


def test_a_clean_report_says_so(our_terms: dict) -> None:
    text = "\n".join(report_lines([], negotiate_extras("police", 1), "police"))
    assert "OK" in text and "BLOCKER" not in text
