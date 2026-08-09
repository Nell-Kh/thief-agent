"""Commit-reveal over SHA-256: sealing, verification, and record audit.

Every game step is sealed before it is played out loud: the full record -
state, position, move, intent, hint, step, role - is serialized canonically,
joined with a fresh cryptographic nonce, and hashed. Only the hash travels
during play; payloads and nonces are disclosed at the end-of-game audit, where
each side recomputes every hash. One mismatch proves tampering - no statistics,
no discretion (rulebook ch. 5).

The seal format is a declared dialect, not a constant. The kit/reference form is
``sha256(canonical_json(payload) + "|" + nonce)``; the book's printed sample
(ch. 5.3.1) hashes the nonce *inside* the serialized object instead. Both are
lawful under the front-matter rule that code samples illustrate rather than
bind, and a pair that disagrees fails every step of the audit in both
directions - so the choice lives in :mod:`shared.interop_profile`, travels in
the handshake, and refuses on mismatch (ADR-6/ADR-7, README section 8).
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

from ..shared.config_io import canonical_json
from ..shared.interop_profile import DEFAULT, InteropProfile

#: Bytes of entropy per nonce; 16 bytes = 32 hex characters.
NONCE_BYTES = 16


def new_nonce() -> str:
    """A fresh cryptographic nonce - ``secrets``, never ``random``.

    Uniqueness makes identical actions hash differently every step, and the
    entropy defeats dictionary attacks over the small move space.
    """
    return secrets.token_hex(NONCE_BYTES)


def digest_of(
    payload: dict[str, Any], nonce: str, profile: InteropProfile = DEFAULT
) -> str:
    """The commitment digest of ``payload`` sealed with ``nonce``.

    Under the kit dialect the nonce is appended to the canonical text; under the
    book dialect it is carried as a ``nonce`` key inside the object that gets
    serialized, exactly as ch. 5.3.1 prints it. One bit of disagreement here
    fails every step of the mutual audit, which is why the dialect is declared
    at the handshake rather than assumed.
    """
    if profile.nonce_inside_payload:
        return hashlib.sha256(
            canonical_json({**payload, "nonce": nonce}).encode("utf-8")
        ).hexdigest()
    material = f"{canonical_json(payload)}|{nonce}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def seal(payload: dict[str, Any], profile: InteropProfile = DEFAULT) -> dict[str, Any]:
    """Seal a record: draw a nonce, compute the digest, keep all three.

    Returns:
        ``{"payload": ..., "nonce": ..., "commit": ...}`` - the full record
        stays local; only ``commit`` may travel before the audit.
    """
    nonce = new_nonce()
    return {
        "payload": payload,
        "nonce": nonce,
        "commit": digest_of(payload, nonce, profile),
    }


def verify(
    payload: dict[str, Any], nonce: str, commit: str, profile: InteropProfile = DEFAULT
) -> bool:
    """Whether a revealed payload and nonce reproduce the committed digest.

    Constant-time comparison; the answer is binary - there is no "almost".
    """
    return secrets.compare_digest(digest_of(payload, nonce, profile), commit)


def audit_records(
    records: list[dict[str, Any]], profile: InteropProfile = DEFAULT
) -> dict[str, Any]:
    """Re-verify a full set of revealed records against their commitments.

    Returns:
        ``passed`` (bool), ``verified_steps`` and ``failed_steps`` (lists of
        the ``step`` field of each record, or its index when absent). A single
        failure fails the audit: the smallest change alters the hash entirely.
    """
    verified: list[Any] = []
    failed: list[Any] = []
    for index, record in enumerate(records):
        label = record.get("payload", {}).get("step", index)
        try:
            ok = verify(record["payload"], record["nonce"], record["commit"], profile)
        except (KeyError, TypeError):
            ok = False
        (verified if ok else failed).append(label)
    return {"passed": not failed, "verified_steps": verified, "failed_steps": failed}
