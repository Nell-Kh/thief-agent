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

Scoped by ``game_id`` rather than by directory, because ``results/`` itself
holds several series flat in one folder: grouping by directory would report two
unrelated series as one forked identity, which is a false alarm that teaches
people to ignore the alarm.

sharNamr ran their version of this over their own history and found two series
ALREADY REPORTED to the lecturer whose ``log_files`` name evidence that is not
on disk. They told us to run it over ours. We did, and it found a stale local
demo from before the joining block existed - untracked, never filed, but the
same defect class. That is what the check is for.
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


def _series() -> list[tuple[Path, str]]:
    """Every ``(directory, game_id)`` pair we have artifacts for."""
    if not RESULTS.is_dir():
        return []
    found: set[tuple[Path, str]] = set()
    for path in RESULTS.rglob("result_*.json"):
        payload = _read(path)
        if isinstance(payload, dict) and payload.get("game_id"):
            found.add((path.parent, str(payload["game_id"])))
    return sorted(found, key=lambda pair: (str(pair[0]), pair[1]))


def _read(path: Path) -> Any:
    """A JSON artifact, or ``None`` if it is unreadable.

    A half-written file is some other test's problem; this one is about what a
    complete artifact SAYS, not about whether every file parses.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _identities(directory: Path, game_id: str) -> dict[str, tuple[str, str]]:
    """``file name -> (game_id, game_uid)`` for one series' lifecycle artifacts."""
    identities: dict[str, tuple[str, str]] = {}
    for path in sorted(directory.glob("*.json")):
        if not path.name.startswith(FAMILIES) or game_id not in path.name:
            continue
        payload = _read(path)
        if isinstance(payload, dict) and "game_uid" in payload:
            identities[path.name] = (str(payload.get("game_id")), str(payload["game_uid"]))
    return identities


@pytest.mark.parametrize("directory,game_id", _series(), ids=lambda v: str(v))
def test_every_artifact_in_a_series_agrees_on_the_series_identity(
    directory: Path, game_id: str
) -> None:
    """One series, one ``game_id``, one ``game_uid`` - across all four families."""
    identities = _identities(directory, game_id)
    if not identities:
        pytest.skip(f"no lifecycle artifacts for {game_id}")
    distinct = set(identities.values())
    assert len(distinct) == 1, (
        f"{game_id} in {directory} holds {len(distinct)} different identities: "
        + "; ".join(f"{name} -> {identity}" for name, identity in sorted(identities.items()))
    )


@pytest.mark.parametrize("directory,game_id", _series(), ids=lambda v: str(v))
def test_every_recorded_uid_is_a_uuid_and_not_a_bare_digest(
    directory: Path, game_id: str
) -> None:
    """A 32-hex digest in the uid field is the exact way sharNamr's Cop log drifted."""
    for name, (_id, uid) in _identities(directory, game_id).items():
        assert len(uid) == 36 and uid.count("-") == 4, (
            f"{directory / name} records game_uid {uid!r}, which is not a UUID - "
            f"a truncated config hash reads as an identity until someone compares two files"
        )


@pytest.mark.parametrize("directory,game_id", _series(), ids=lambda v: str(v))
def test_every_log_a_report_points_at_actually_exists(directory: Path, game_id: str) -> None:
    """The failure sharNamr found in their own filed reports, checked against ours.

    Their ``result_G008.json`` named ``log_G008_g01.json`` in ``log_files`` while
    the file on disk was ``log_game-772de8f029e4_g01.json``. The report is valid
    JSON, the evidence exists, and an auditor following the link finds nothing -
    which under a rulebook that scores audit trails is indistinguishable from
    having no evidence at all. Cheap to check, impossible to notice by eye.
    """
    result = _read(directory / f"result_{game_id}.json")
    if not isinstance(result, dict):
        pytest.skip(f"no result file for {game_id}")
    missing = [
        name
        for row in result.get("sub_games", [])
        for name in (row.get("log_files") or {}).values()
        if name and not (directory / str(name)).exists()
    ]
    assert not missing, (
        f"result_{game_id}.json points at log files that are not on disk: "
        f"{sorted(set(missing))} - an auditor following log_files finds nothing"
    )
