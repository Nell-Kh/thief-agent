"""Tests for sealing, verification and record auditing."""

from __future__ import annotations

from police_thief.domain.crypto import audit_records, digest_of, new_nonce, seal, verify

PAYLOAD = {"step": 3, "role": "thief", "move": "move:N", "intent": "lie"}


def test_a_nonce_is_32_hex_characters() -> None:
    nonce = new_nonce()
    assert len(nonce) == 32
    assert all(char in "0123456789abcdef" for char in nonce)


def test_nonces_never_repeat() -> None:
    """Two seals of identical payloads must differ - a repeat would leak the move."""
    assert len({new_nonce() for _ in range(200)}) == 200


def test_sealing_returns_payload_nonce_and_commit() -> None:
    record = seal(PAYLOAD)
    assert record["payload"] == PAYLOAD
    assert len(record["commit"]) == 64
    assert verify(record["payload"], record["nonce"], record["commit"])


def test_identical_actions_hash_differently() -> None:
    """The nonce defeats dictionary attacks over the tiny move space."""
    first = seal(PAYLOAD)
    second = seal(PAYLOAD)
    assert first["commit"] != second["commit"]


def test_the_digest_is_stable_for_the_same_payload_and_nonce() -> None:
    assert digest_of(PAYLOAD, "a" * 32) == digest_of(dict(PAYLOAD), "a" * 32)


def test_key_order_does_not_change_the_digest() -> None:
    """Canonical JSON: both peers hash byte-identical input."""
    reordered = {"intent": "lie", "move": "move:N", "role": "thief", "step": 3}
    assert digest_of(PAYLOAD, "a" * 32) == digest_of(reordered, "a" * 32)


def test_the_smallest_payload_change_breaks_verification() -> None:
    record = seal(PAYLOAD)
    forged = dict(record["payload"], move="move:S")
    assert not verify(forged, record["nonce"], record["commit"])


def test_a_wrong_nonce_breaks_verification() -> None:
    record = seal(PAYLOAD)
    assert not verify(record["payload"], "f" * 32, record["commit"])


def test_a_clean_log_passes_the_audit() -> None:
    records = [seal({"step": step, "move": "move:N"}) for step in range(5)]
    report = audit_records(records)
    assert report["passed"]
    assert report["verified_steps"] == [0, 1, 2, 3, 4]
    assert report["failed_steps"] == []


def test_one_forged_record_fails_the_whole_audit() -> None:
    """The iron law: a single mismatch is proven tampering."""
    records = [seal({"step": step, "move": "move:N"}) for step in range(5)]
    records[2]["payload"]["move"] = "move:E"
    report = audit_records(records)
    assert not report["passed"]
    assert report["failed_steps"] == [2]
    assert 3 in report["verified_steps"]


def test_a_malformed_record_counts_as_failed() -> None:
    report = audit_records([{"payload": {"step": 9}}])
    assert not report["passed"]
    assert report["failed_steps"] == [9]


def test_an_empty_log_passes_vacuously() -> None:
    assert audit_records([])["passed"]
