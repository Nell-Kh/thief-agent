"""The append-only match log: local evidence, public commitments, full audit.

Each peer keeps every sealed record - payload, nonce, commitment - locally.
During play only the commitments are public. At game end the whole book is
handed to the opponent for the mutual audit, and saved as
``log_<game_id>_g<NN>.json`` (rulebook Appendix F.3 naming), which is also what
the Replay Viewer loads and re-verifies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..constants import LOG_FILE
from .crypto import seal


class Logbook:
    """One mini-game's sealed history for one peer."""

    def __init__(self, game_id: str, sub_game: int, role: str) -> None:
        """Open an empty book for one mini-game."""
        self.game_id = game_id
        self.sub_game = sub_game
        self.role = role
        self._records: list[dict[str, Any]] = []
        self.result: dict[str, Any] | None = None

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Seal a record and append it; returns the sealed record.

        Appending is the only mutation the book supports - records are never
        edited or removed, which is what makes the audit meaningful.
        """
        record = seal(payload)
        self._records.append(record)
        return record

    @property
    def records(self) -> list[dict[str, Any]]:
        """The full sealed records (payload + nonce + commit), local only."""
        return list(self._records)

    def commitment_for(self, step: int) -> str | None:
        """The commitment hash of the record sealed for ``step``, if any."""
        for record in self._records:
            if record["payload"].get("step") == step:
                return record["commit"]
        return None

    def public_view(self) -> list[dict[str, Any]]:
        """What may be shown during play: step numbers and commitments only."""
        return [
            {"step": record["payload"].get("step"), "commit": record["commit"]}
            for record in self._records
        ]

    def audit_payload(self, result_claim: dict[str, Any] | None = None) -> dict[str, Any]:
        """The end-of-game disclosure: every payload and nonce, plus our claim."""
        return {
            "sender": self.role,
            "records": self.records,
            "result_claim": str((result_claim or self.result or {}).get("type", "undecided")),
            "result_detail": result_claim or self.result or {},
        }

    def close(self, result: dict[str, Any]) -> None:
        """Record the final result claim."""
        self.result = result

    def file_name(self) -> str:
        """The mandated log file name for this mini-game."""
        return LOG_FILE.format(game_id=self.game_id, mini=self.sub_game)

    def save(self, directory: str | Path) -> Path:
        """Write the full book to disk and return the path."""
        target = Path(directory) / self.file_name()
        target.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "game_id": self.game_id,
            "sub_game": self.sub_game,
            "role": self.role,
            "result": self.result,
            "records": self._records,
        }
        target.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> Logbook:
        """Read a saved book back - the Replay Viewer's entry point.

        Two envelopes carry the same sealed records, and the viewer must open
        both. :meth:`save` writes the local one (``sub_game``/``role``/
        ``result``); the series driver writes the league lifecycle one
        (``sub_game_number``, with the role and outcome nested under
        ``summary`` - see :func:`police_thief.infra.email.reports.log_payload`).
        Reading only the local keys is what made the mandatory viewer refuse
        every log an actual match had ever produced, while the demo log written
        by ``scripts/capture_replay_viewer.py`` opened fine and hid it. The
        records themselves are identical under either envelope, so the
        commitments verify the same way once the book is open.

        Only the identifying pair is required. The role is NOT: it names the
        writer in :meth:`audit_payload` and nothing the viewer draws, and the
        earliest self-play artifacts omit it entirely. Refusing to verify a
        log's commitments over a field verification never reads would be the
        same mistake in a smaller form, so a missing role loads as ``""``.

        Raises:
            ValueError: when the file identifies no sub-game under either
                envelope, i.e. it is not a match log at all.
        """
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        summary = document.get("summary") or {}
        sub_game = document.get("sub_game", document.get("sub_game_number"))
        if sub_game is None:
            sub_game = summary.get("sub_game_number")
        if sub_game is None:
            raise ValueError(f"{Path(path).name}: not a match log (no sub-game number)")
        role = document.get("role") or summary.get("role") or ""
        book = cls(document["game_id"], int(sub_game), str(role))
        book._records = list(document.get("records", []))
        book.result = document.get("result") or summary or None
        return book
