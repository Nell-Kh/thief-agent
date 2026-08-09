"""Capture a real Replay Viewer screenshot showing "Verified OK" (TODO 9.3.2).

Plays a genuine two-runtime match (the ``test_two_peers.py`` pattern) against
the real shipped ``config/``, saves the police side's sealed logbook to
``logs/`` in the on-disk format :class:`Logbook.load` expects, then opens the
real :class:`ReplayWindow` on that saved file, steps it to the final turn, and
screen-grabs the window - proving the green stamp comes from the domain
layer's own re-verification (:mod:`police_thief.domain.replay`), not a mock.
"""

from __future__ import annotations

import contextlib
import ctypes
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

with contextlib.suppress(AttributeError, OSError):
    # Windows-only: make Tk's logical pixels match ImageGrab's physical ones.
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE

from PIL import ImageGrab  # noqa: E402

from police_thief.domain.audit import VERDICT_OK  # noqa: E402
from police_thief.gui.replay import ReplayWindow  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402
from police_thief.shared.config import ConfigManager  # noqa: E402

SAFETY_CAP = 90
OUT = ROOT / "docs" / "img" / "replay_verified_ok.png"
LOG_DIR = ROOT / "logs"


def deliver(receiver: MatchRuntime, sender: MatchRuntime, message) -> None:
    """Hand a message over, and route back any immediate reply (a concession)."""
    reply = receiver.on_turn(message)
    if reply is not None:
        sender.on_turn(reply)


def play_out(police: MatchRuntime, thief: MatchRuntime) -> None:
    """Alternate turns - thief first - delivering each message to the other."""
    for _ in range(SAFETY_CAP):
        if thief.ended and police.ended:
            return
        if not thief.ended:
            deliver(police, thief, thief.play_turn())
        if police.ended and thief.ended:
            return
        if not police.ended:
            deliver(thief, police, police.play_turn())
    raise RuntimeError("the match did not terminate inside the safety cap")


def grab_window(window: ReplayWindow, out: Path) -> None:
    """Bring the real Tk window to the front and screen-capture its bounds."""
    window.root.attributes("-topmost", True)
    window.root.update()
    time.sleep(0.4)
    x0, y0 = window.root.winfo_rootx(), window.root.winfo_rooty()
    x1, y1 = x0 + window.root.winfo_width(), y0 + window.root.winfo_height()
    out.parent.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(bbox=(x0, y0, x1, y1)).save(out)
    window.root.attributes("-topmost", False)


def main() -> None:
    """Play a real match, save its logbook, and screen-grab the replay viewer."""
    config_dir = ROOT / "config"
    police = MatchRuntime(
        ConfigManager.load("police", config_dir), game_id="replay-demo", sub_game=1,
        github_commit="localdemo",
    )
    thief = MatchRuntime(
        ConfigManager.load("thief", config_dir), game_id="replay-demo", sub_game=1,
        github_commit="localdemo",
    )
    play_out(police, thief)
    police.book.close(police.result or {"type": "undecided"})
    log_path = police.book.save(LOG_DIR)
    print(f"played to {police.result} after {police.view.step} steps; saved -> {log_path}")

    window = ReplayWindow(str(log_path))
    # Step to the last recorded turn.
    while True:
        before = window.session.index
        window._forward()  # noqa: SLF001 - driving the real widget, not re-deriving logic
        if window.session.index == before:
            break
    window._draw()  # noqa: SLF001

    overall = window.session.overall_verdict()
    print(f"overall verdict: {overall}")
    if overall != VERDICT_OK:
        raise RuntimeError(f"expected {VERDICT_OK}, got {overall} - not a valid capture")

    grab_window(window, OUT)
    print(f"captured -> {OUT}")
    window.root.destroy()


if __name__ == "__main__":
    main()
