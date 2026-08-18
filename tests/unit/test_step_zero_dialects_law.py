"""We must read the opponent's commit whichever way they spell Step-0.

Rule #53 wants the commit each sub-game was played on recorded for BOTH sides,
and the opponent's answer is inside the disclosure we have just audited - so
filing ``"unknown"`` is never "we could not know", it is "we did not look
properly".

MOAAMOHA (2026-08-18) told us before playing that their Step-0 record is
``record_type: "step_zero"`` and that their own reader accepts our
``type: "system_spec"`` as equivalent. That sentence is the whole finding: THEY
are tolerant and we were not, so their report would have carried our commit
while ours carried ``"unknown"`` for theirs - a hole in exactly one of the two
files an auditor joins, and one we would have discovered only after a counted
series was already filed.

The asymmetry is the lesson. Interop generosity has to be mutual, or the
stricter side quietly produces the poorer evidence and never sees it, because
its own artifacts look complete from the inside.

Nothing is loosened: a record must still SAY it is Step-0 under one of the
known spellings, and a turn record carrying a ``github_commit`` is still
ignored - otherwise the first move of the game could impersonate the
declaration.
"""

from __future__ import annotations

import pytest

from police_thief.infra.email.report_blocks import opponent_commit

OURS = "a5a304eb7d9c82607dcaadd3e5193c006d2d40c0"
THEIRS = "46d78a6da6c0d1e1c06bb551de9a2a7b729b6f86"


def disclosure(*payloads: dict) -> dict:
    """A disclosure of sealed records, in the shape the mutual audit hands us."""
    return {"records": [{"commit": "0" * 64, "nonce": "ab" * 16, "payload": payload}
                        for payload in payloads]}


def turn(step: int) -> dict:
    """An ordinary turn record - never a source of the declared commit."""
    return {"type": "turn", "step": step, "move": "move:E"}


def test_our_own_spelling_still_reads() -> None:
    """The regression guard: widening must not break the shape we already ship."""
    assert opponent_commit(
        disclosure({"type": "system_spec", "github_commit": OURS}, turn(1))) == OURS


def test_the_step_zero_spelling_reads_too() -> None:
    """MOAAMOHA's shape, which we used to file as ``unknown``."""
    assert opponent_commit(
        disclosure({"record_type": "step_zero", "github_commit": THEIRS}, turn(1))) == THEIRS


def test_a_marker_on_the_wrapper_rather_than_the_payload_reads() -> None:
    """Placement varies as well as spelling; both scopes are searched."""
    wrapped = {"records": [{"record_type": "step_zero", "commit": "0" * 64,
                            "payload": {"github_commit": THEIRS}}]}
    assert opponent_commit(wrapped) == THEIRS


def test_a_turn_record_carrying_a_commit_is_ignored() -> None:
    """Nothing is loosened - only a record that DECLARES itself Step-0 counts.

    Otherwise a peer's first move could impersonate the declaration, and the
    SHA we file for them would be whatever appeared earliest in the stream.
    """
    assert opponent_commit(
        disclosure({"type": "turn", "step": 1, "github_commit": THEIRS})) == "unknown"


def test_a_step_zero_with_no_commit_does_not_become_a_false_answer() -> None:
    """An honestly absent SHA stays absent; scanning continues past the blank."""
    assert opponent_commit(disclosure({"type": "system_spec", "github_commit": ""},
                                      {"record_type": "step_zero",
                                       "github_commit": THEIRS})) == THEIRS


@pytest.mark.parametrize("empty", [None, {}, {"records": []}, {"records": [turn(1)]}])
def test_nothing_to_read_is_reported_as_unknown(empty) -> None:
    """The one honest answer when the opponent sealed no declaration at all."""
    assert opponent_commit(empty) == "unknown"
