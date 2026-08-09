"""Tests for the settlement consensus - the hash that must match a rival's byte-for-byte."""

from __future__ import annotations

import pytest

from police_thief.infra.email.consensus import (
    SIGNATURE_KEY,
    consensus_signature,
    mutual_agreement_hash,
    mutual_agreement_scope,
    serialize_spaced,
    series_aggregate,
    sign_report,
    verify_signed_report,
)
from police_thief.shared.config_io import canonical_json


def row(number: int, winner: str | None, scores: dict, *, tie: bool = False) -> dict:
    """One sub-game row carrying the scores the aggregate is derived from."""
    return {
        "sub_game_number": number, "roles": {"a": "police", "b": "thief"},
        "started_at": "t0", "ended_at": "t1", "result": "capture",
        "winner_group": winner, "tie": tie, "steps": 6,
        "github_commit": {"a": "x", "b": "y"}, "tokens": {"a": 0, "b": 0},
        "score": scores, "log_files": {}, "audit": {},
    }


def test_the_spaced_form_is_not_the_compact_form() -> None:
    """The settlement serialization must differ from the commit serialization."""
    payload = {"ניקוד": [20, 5], "b": 1.5}
    assert serialize_spaced(payload) != canonical_json(payload)
    assert '", "' not in canonical_json(payload)  # compact has no spaces
    assert ", " in serialize_spaced(payload)


def test_signing_is_sign_then_insert() -> None:
    report = {"game_uid": "u", "score": [20, 5]}
    signed = sign_report(report)
    assert signed[SIGNATURE_KEY] == consensus_signature(report)  # preimage excludes the key
    assert verify_signed_report(signed)
    assert SIGNATURE_KEY not in report  # the input is not mutated


def test_a_signed_report_refuses_a_second_signature() -> None:
    signed = sign_report({"a": 1})
    with pytest.raises(ValueError, match="already signed"):
        sign_report(signed)


def test_a_tampered_report_fails_verification() -> None:
    signed = sign_report({"a": 1})
    tampered = {**signed, "a": 2}
    assert not verify_signed_report(tampered)
    assert not verify_signed_report({"a": 1})  # no signature at all


def test_the_aggregate_is_derived_from_the_rows() -> None:
    rows = [row(1, "a", {"a": 20, "b": 5}), row(2, "b", {"a": 5, "b": 10})]
    aggregate = series_aggregate(rows, tie_score=2)
    assert aggregate == {
        "total_score": {"a": 25, "b": 15}, "sub_games_won": {"a": 1, "b": 1},
        "ties": 0, "winner_group": "a", "series_tie": False,
    }


def test_a_series_tie_adds_the_tie_award_into_both_totals() -> None:
    rows = [row(1, "a", {"a": 20, "b": 5}), row(2, "b", {"a": 5, "b": 20})]
    aggregate = series_aggregate(rows, tie_score=2)
    assert aggregate["series_tie"] is True and aggregate["winner_group"] is None
    assert aggregate["total_score"] == {"a": 27, "b": 27}


def test_zeroed_rows_are_sanctions_not_ties() -> None:
    """The accounting identity: won_a + won_b + ties + zeroed == num_sub_games."""
    rows = [
        row(1, "a", {"a": 20, "b": 5}),
        row(2, None, {"a": 2, "b": 2}, tie=True),  # scored as a tie
        row(3, None, {"a": 0, "b": 0}),  # zeroed: credited to nobody
    ]
    aggregate = series_aggregate(rows, tie_score=2)
    assert aggregate["ties"] == 1  # only the tie-SCORED row
    won = aggregate["sub_games_won"]
    zeroed = 1
    assert won["a"] + won["b"] + aggregate["ties"] + zeroed == len(rows)


def test_the_scope_keeps_only_pair_observable_fields() -> None:
    rows = [row(1, "a", {"a": 20, "b": 5})]
    scope = mutual_agreement_scope("gid", rows, series_aggregate(rows, tie_score=2))
    assert set(scope) == {"game_id", "aggregate", "sub_games"}
    trimmed = scope["sub_games"][0]
    assert set(trimmed) == {"sub_game_number", "roles", "result", "winner_group", "tie", "score"}
    assert "started_at" not in trimmed and "tokens" not in trimmed  # per-side facts cut


def test_the_hash_moves_when_the_outcome_moves() -> None:
    """A consensus, not a cache: different outcomes must hash differently."""
    won = [row(1, "a", {"a": 20, "b": 5})]
    lost = [row(1, "b", {"a": 5, "b": 10})]
    hashes = {
        mutual_agreement_hash(mutual_agreement_scope("g", rows, series_aggregate(rows, 2)))
        for rows in (won, lost)
    }
    assert len(hashes) == 2
