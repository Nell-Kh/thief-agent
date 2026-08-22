"""Best-effort, opt-in wire-level protocol trace.

Turned on ONLY when the environment variable ``PT_WIRE_TRACE`` names a file; when
it is unset this module is inert and a run is byte-for-byte what it was before -
so nothing here can change how a match plays, it can only record what happened.

Why it exists: a sub-game that stalls after negotiation used to leave no
machine-readable account of *which* protocol call did or did not cross the wire.
The FastMCP/uvicorn access log shows only ``POST /mcp`` - not the JSON-RPC tool
name, not the sub-game, not the step - so "did their first turn arrive?" could
not be answered from disk (G010 g03, 2026-08-22, uoh-ay26's protocol-trace
request). Each side writes one JSONL line per protocol event:

    {"ts": "<utc-iso>", "dir": "in|out", "tool": "...", "subgame": N,
     "peer": "<url>", "step": N, "sender": "...", "result": ..., "error": ...}

which reads directly as the ``timestamp | side | role | subgame | tool | peer |
result/error`` table both teams asked for. A trace failure is swallowed: the
game must never break because a log line could not be written.
"""

from __future__ import annotations

import datetime
import json
import os
import threading
from typing import Any

#: Resolved once, at import, from the launching shell's environment. Empty = off.
_BASE = os.environ.get("PT_WIRE_TRACE", "").strip()
#: One file per process, so the two rule-1 halves never interleave into one file.
_PATH = f"{_BASE}.{os.getpid()}.jsonl" if _BASE else ""
_LOCK = threading.Lock()


def enabled() -> bool:
    """True when a trace file is configured for this process."""
    return bool(_PATH)


def path() -> str:
    """The per-process trace file path, or ``""`` when tracing is off."""
    return _PATH


def record(direction: str, tool: str, subgame: int | None = None, *,
           peer: str = "", step: Any = None, sender: Any = None,
           result: Any = None, error: Any = None) -> None:
    """Append one protocol event. Never raises; a broken trace stays silent.

    ``direction`` is ``"in"`` (a tool an opponent called on us) or ``"out"`` (a
    call we made to them). ``result`` is trimmed to a short repr so a full turn
    payload never bloats the trace - the sealed log already holds those.
    """
    if not _PATH:
        return
    try:
        line = json.dumps({
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "dir": direction,
            "tool": tool,
            "subgame": subgame,
            "peer": peer,
            "step": step,
            "sender": sender,
            "result": _short(result),
            "error": None if error is None else str(error),
        }, default=str, separators=(",", ":"))
        with _LOCK, open(_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:  # noqa: BLE001 - a trace must never break the game
        pass


def _short(value: Any) -> Any:
    """A compact, JSON-safe stand-in for a possibly-large result object."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    return text if len(text) <= 200 else text[:200] + "...(truncated)"
