"""Every artifact of one series must agree on what the series is called.

sharNamr found this defect in their own repository on 2026-08-17 and told us
rather than letting it reach a graded submission: their result file carried the
agreed ``game_uid``, their Cop log carried ``config_sha256[:32]``, and their
Thief log carried the *unlabelled* derivation - three different answers to one
question, in the four files an auditor actually opens. The aggregate was right
and the evidence underneath it was wrong, which is the worst shape a defect can
take because nothing in the score ever shows it.

They asked us to check for the same shape. We are clean - one
``derive_game_ids`` call is threaded through every payload builder - but
"we are clean" is a claim about today, and the only reason THEIR files drifted
is that nothing was watching. So this is a law now:

    within one results directory, every declaration, config, log and result
    file agrees on ``game_id`` and on ``game_uid``.

It reads whatever real artifacts are on disk rather than constructing any, so
it is worth exactly as much as the series we have actually played - and it
costs nothing when there are none.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS = REPO_ROOT / "results"

#: Artifact families named in rulebook ch. 9.3.3 - the four files of one game.
FAMILIES = ("declaration_", "config_", "log_", "result_")


def _artifact_dirs() -> list[Path]:
    """Every directory holding at least one result file, ``results/`` included."""
    if not RESULTS.is_dir():
        return []
    found = {path.parent for path in RESULTS.rglob("result_*.json")}
    return sorted(found)


def _identities(directory: Path) -> dict[str, tuple[str, str]]:
    """``file name -> (game_id, game_uid)`` for every lifecycle artifact present."""
    identities: dict[str, tuple[str, str]] = {}
    for path in sorted(directory.glob("*.json")):
        if not path.name.startswith(FAMILIES):
            continue
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:  # a half-written artifact is a different test's problem
            continue
        if isinstance(payload, dict) and "game_uid" in payload:
            identities[path.name] = (str(payload.get("game_id")), str(payload["game_uid"]))
    return identities


@pytest.mark.parametrize("directory", _artifact_dirs(), ids=lambda p: p.name)
def test_every_artifact_in_a_series_agrees_on_the_series_identity(directory: Path) -> None:
    """One series, one ``game_id``, one ``game_uid`` - across all four families."""
    identities = _identities(directory)
    if not identities:
        pytest.skip(f"no lifecycle artifacts in {directory}")
    distinct = set(identities.values())
    assert len(distinct) == 1, (
        f"{directory} holds {len(distinct)} different series identities: "
        + "; ".join(f"{name} -> {identity}" for name, identity in sorted(identities.items()))
    )


@pytest.mark.parametrize("directory", _artifact_dirs(), ids=lambda p: p.name)
def test_every_recorded_uid_is_a_uuid_and_not_a_bare_digest(directory: Path) -> None:
    """A 32-hex digest in the uid field is the exact way sharNamr's Cop log drifted."""
    for name, (_game_id, uid) in _identities(directory).items():
        assert len(uid) == 36 and uid.count("-") == 4, (
            f"{directory / name} records game_uid {uid!r}, which is not a UUID - "
            f"a truncated config hash reads as an identity until someone compares two files"
        )
