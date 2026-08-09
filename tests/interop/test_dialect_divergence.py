"""Each dialect fork, exercised through the real code path that carries it.

:mod:`test_interop_profile` pins the flags; this pins the CONSEQUENCES - the
actual digests, tau values, key counts and settlement hashes two peers would
exchange. If any pair below ever stops differing, the profile has become
decoration and the kit-vs-book choice is once again being made silently.
"""

from __future__ import annotations

import hashlib

from police_thief.domain.crypto import digest_of, verify
from police_thief.domain.scent import ScentField
from police_thief.infra.email.consensus import (
    mutual_agreement_hash,
    serialize_spaced,
    series_aggregate,
)
from police_thief.shared.config import ConfigManager
from police_thief.shared.config_io import canonical_json
from police_thief.shared.interop import terms_from_contract
from police_thief.shared.interop_profile import (
    PROFILE_BOOK,
    PROFILE_KIT,
    TIE_AWARD_SUBSTITUTE,
    resolve,
)
from police_thief.shared.schema import PheromoneConfig

KIT = resolve(PROFILE_KIT)
BOOK = resolve(PROFILE_BOOK)

PAYLOAD = {"step": 1, "role": "police", "move": "move:N"}
NONCE = "a1a2a3a4b1b2b3b4c1c2c3c4d1d2d3d4"
PHEROMONES = PheromoneConfig(
    center_intensity=0.9, decay=0.1, grid_size=5, min_center_intensity=0.5
)


def _rows(score_a: int, score_b: int) -> list[dict]:
    """One sub-game row pair shaped as the settlement scope expects."""
    return [
        {
            "sub_game_number": 1, "roles": {"a": "police", "b": "thief"},
            "result": "capture", "winner_group": None, "tie": True,
            "score": {"a": score_a, "b": score_b},
        }
    ]


def test_the_seal_digest_differs_and_each_verifies_only_under_its_own_dialect() -> None:
    """The failure mode: every step of the audit fails, in both directions."""
    kit_digest = digest_of(PAYLOAD, NONCE, KIT)
    book_digest = digest_of(PAYLOAD, NONCE, BOOK)
    assert kit_digest != book_digest
    assert verify(PAYLOAD, NONCE, kit_digest, KIT)
    assert verify(PAYLOAD, NONCE, book_digest, BOOK)
    assert not verify(PAYLOAD, NONCE, kit_digest, BOOK)
    assert not verify(PAYLOAD, NONCE, book_digest, KIT)


def test_each_seal_is_its_own_printed_construction() -> None:
    """Both digests re-derived by hand, so neither can drift into the other.

    Book (ch. 5.3.1): the nonce is a key inside the object that gets serialized.
    Kit/reference: it is appended to the canonical text after a pipe.
    """
    book_expected = hashlib.sha256(
        canonical_json({**PAYLOAD, "nonce": NONCE}).encode("utf-8")
    ).hexdigest()
    kit_expected = hashlib.sha256(
        f"{canonical_json(PAYLOAD)}|{NONCE}".encode()
    ).hexdigest()
    assert digest_of(PAYLOAD, NONCE, BOOK) == book_expected
    assert digest_of(PAYLOAD, NONCE, KIT) == kit_expected


def test_the_scent_clamp_diverges_on_the_very_first_re_emission() -> None:
    """0.9*0.9 + 0.9 = 1.71: clamped to 0.9, or kept, depending on dialect."""
    kit_field = ScentField(7, PHEROMONES, KIT)
    book_field = ScentField(7, PHEROMONES, BOOK)
    for _ in range(2):
        kit_field.advance((3, 3))
        book_field.advance((3, 3))
    assert kit_field.intensity((3, 3)) == 0.9
    assert book_field.intensity((3, 3)) > 1.0
    assert kit_field.snapshot() != book_field.snapshot()


def test_the_signed_terms_differ_by_exactly_the_non_book_key() -> None:
    """13 keys vs 14; validate_terms compares whole objects, so the count refuses."""
    contract = ConfigManager.load("police").contract
    kit_terms = terms_from_contract(contract, KIT)
    book_terms = terms_from_contract(contract, BOOK)
    assert set(kit_terms) - set(book_terms) == {"min_center_intensity"}
    assert set(book_terms) - set(kit_terms) == set()
    assert len(kit_terms) == 14
    assert len(book_terms) == 13


def test_the_settlement_serialization_differs_in_spacing() -> None:
    """Spaced under kit, compact under book - the same bytes never both work."""
    payload = {"b": 1, "a": [2, 3]}
    assert serialize_spaced(payload, KIT) == '{"a": [2, 3], "b": 1}'
    assert serialize_spaced(payload, BOOK) == '{"a":[2,3],"b":1}'


def test_the_settlement_hash_differs_between_dialects_on_identical_rows() -> None:
    """Same game, same rows, two hashes - rule #35 zeroes both teams."""
    rows = _rows(20, 20)
    aggregate_kit = series_aggregate(rows, tie_score=2, profile=KIT)
    aggregate_book = series_aggregate(rows, tie_score=2, profile=BOOK)
    scope_kit = {"game_id": "g", "aggregate": aggregate_kit, "sub_games": rows}
    scope_book = {"game_id": "g", "aggregate": aggregate_book, "sub_games": rows}
    assert mutual_agreement_hash(scope_kit, KIT) != mutual_agreement_hash(
        scope_book, BOOK
    )


def test_the_tie_award_reading_changes_the_totals_under_either_dialect() -> None:
    """add vs substitute forks total_score, which sits inside the settlement scope."""
    rows = _rows(20, 20)
    added = series_aggregate(rows, tie_score=2, profile=resolve(PROFILE_KIT))
    replaced = series_aggregate(
        rows, tie_score=2, profile=resolve(PROFILE_KIT, TIE_AWARD_SUBSTITUTE)
    )
    assert added["total_score"] == {"a": 22, "b": 22}
    assert replaced["total_score"] == {"a": 2, "b": 2}
    assert added["series_tie"] is True and replaced["series_tie"] is True


def test_the_shipped_config_selects_the_kit_dialect_on_both_sides() -> None:
    """Both peers must speak one dialect; a split config is a self-inflicted refusal."""
    police = ConfigManager.load("police").interop
    thief = ConfigManager.load("thief").interop
    assert police == thief
    assert police.name == PROFILE_KIT
