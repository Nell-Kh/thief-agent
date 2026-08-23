"""Wire-level protocol trace — on by default.

Writes one JSONL line per protocol event to ``logs/wire_g010.<pid>.jsonl`` under
the repo root. ``PT_WIRE_TRACE=<path>`` overrides the location; ``PT_WIRE_TRACE=0``
(or ``off``/``false``/``none``) disables it. It used to be opt-in via the env var,
but across four G010 replays the variable was never set and every g04 stall went
un-traced, so the default is now ON — the trace is the only thing that answers
"did their turn reach us, get dropped, or never arrive?" from disk.

Each line: ``{ts, dir:in|out, tool, subgame, peer, step, sender, result|error}``,
which reads directly as the ``timestamp | side | role | subgame | tool | peer |
result/error`` table both teams want. A trace failure is swallowed: the game must
never break because a log line could not be written.
"""

from __future__ import annotations

import datetime
import json
import os
import threading
from pathlib import Path
from typing import Any

_OFF = {"0", "off", "false", "no", "none"}
_ENV = os.environ.get("PT_WIRE_TRACE", "").strip()

if _ENV.lower() in _OFF:
    _BASE = ""
elif _ENV:
    _BASE = _ENV
else:
    # Default ON. Repo root is three parents up from src/police_thief/infra/.
    try:
        _root = Path(__file__).resolve().parents[3]
        _logs = _root / "logs"
        _logs.mkdir(parents=True, exist_ok=True)
        _BASE = str(_logs / "wire_g010")
    except Exception:  # noqa: BLE001 - tracing must never break startup
        _BASE = ""

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
