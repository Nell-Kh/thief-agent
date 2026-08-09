"""Crash recovery for a series: rows already settled must survive the laptop.

Split from :mod:`series_guard` (the 150-line rule). That module decides which
failures a sub-game may absorb; this one makes sure the sub-games that *did*
finish are still there after a crash, a sleep or a closed terminal.

The distinction matters because the stakes differ. Containment protects the
schedule; checkpointing protects evidence. A series against a real opponent
cannot be replayed - those games happened once - so losing five settled rows at
sub-game six is not an inconvenience, it is a counted game that no longer has a
log to submit.

Nothing here is a league artifact. The checkpoint is evidence for us; the four
documents the league reads are written by :mod:`infra.email.naming`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: Local crash-recovery file. Deliberately NOT one of the four lifecycle
#: artifacts - it is evidence for us, never a document the league reads.
CHECKPOINT_NAME = "rows_checkpoint.json"


def checkpoint_path(artifacts: str | Path) -> Path:
    """Where a series keeps its recoverable row log."""
    return Path(artifacts) / CHECKPOINT_NAME


def save_rows(artifacts: str | Path, rows: list[dict[str, Any]]) -> Path:
    """Persist every settled row so a crash cannot erase games already played.

    The rows exist only in memory until the series ends, so a laptop that
    sleeps, a closed terminal or a killed process at sub-game 5 of 6 loses
    five real games against a real opponent - and unlike a local rehearsal,
    those cannot be replayed. Written atomically (temp file, then replace):
    a crash *during* the write leaves the previous good checkpoint intact
    rather than a half-written file, which is the failure mode that makes
    naive checkpointing worse than none.
    """
    path = checkpoint_path(artifacts)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    return path


def load_rows(artifacts: str | Path) -> list[dict[str, Any]]:
    """Rows recovered from a previous run, or an empty list if there are none.

    A corrupt or unreadable checkpoint returns empty rather than raising:
    recovery is a bonus path, and it must never be the thing that stops a
    series from starting.
    """
    path = checkpoint_path(artifacts)
    if not path.exists():
        return []
    try:
        recovered = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return recovered if isinstance(recovered, list) else []


def archive_previous_run(artifacts: str | Path) -> Path | None:
    """Move a previous run's folder aside instead of deleting it.

    A re-run used to ``rmtree`` the directory, which is exactly backwards
    after a crash: the one moment you re-run is the moment the wreckage of
    the last attempt is the only record of games that were really played.
    Returns the archive path, or None when there was nothing to preserve.
    """
    directory = Path(artifacts)
    if not directory.exists() or not any(directory.iterdir()):
        return None
    index = 1
    while True:
        archive = directory.with_name(f"{directory.name}.superseded-{index}")
        if not archive.exists():
            directory.rename(archive)
            return archive
        index += 1
