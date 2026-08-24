"""A capture must be cryptographically declared in the sealed log, not only on
the wire (rulebook 3.4.4/3.4.5, rule #21). uoh-ay26's G010 audit (2026-08-24)
found our barrier-trap captures legal but the claim absent from the sealed
evidence - it travelled on the wire and was never logged. These tests pin that
the claim fields are now inside the commit preimage, while a turn that declares
nothing keeps its original preimage so no existing record or vector moves.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from police_thief.domain.crypto import digest_of, seal, verify  # noqa: E402
from police_thief.domain.sealing import turn_record  # noqa: E402

_BASE = {
    "step": 25, "role": "police", "grid_size": 7, "position": (5, 5),
    "barriers": frozenset({(6, 5)}), "move": "STAY", "intent": "truth",
    "hint": "north bridge", "tokens_step": 0, "tokens_total": 0,
}


def test_a_barrier_trap_capture_seals_its_claim_and_barrier() -> None:
    """The capturing turn now carries capture_claim + barrier_placed, sealed."""
    rec = turn_record(**_BASE, capture_claim=[5, 5], barrier_placed=[6, 5])
    assert rec["capture_claim"] == [5, 5]
    assert rec["barrier_placed"] == [6, 5]
    sealed = seal(rec)
    assert verify(sealed["payload"], sealed["nonce"], sealed["commit"])


def test_a_plain_turn_keeps_its_original_preimage() -> None:
    """Omitted-when-absent: a declaration-free turn is byte-identical to the
    pre-fix record, so no existing commit or golden vector shifts."""
    rec = turn_record(**_BASE)
    for key in ("capture_claim", "claim_response", "win_claim", "barrier_placed"):
        assert key not in rec


def test_the_claim_is_bound_by_the_commit() -> None:
    """Sealing the claim changes the digest under a fixed nonce - proof it is
    inside the preimage, not floating loose on the wire."""
    nonce = "0" * 32
    plain = turn_record(**_BASE)
    claimed = turn_record(**_BASE, capture_claim=[5, 5], barrier_placed=[6, 5])
    assert digest_of(plain, nonce) != digest_of(claimed, nonce)
