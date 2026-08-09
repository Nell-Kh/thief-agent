"""Capture a real Live GUI screenshot during a self-play match (TODO 9.3.1).

Plays a genuine two-runtime match - the same pattern as
``tests/integration/test_two_peers.py`` - against the real shipped
``config/``, driving the police side's :class:`LiveWindow` after every turn.
The capture is taken once the belief heatmap has committed to a real argmax,
a few steps in, so the screenshot shows the "T?" belief marker, the police's
own position, and placed barriers - never the thief's true cell (rules #8/#9).
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

from police_thief.gui.live import LiveWindow  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402
from police_thief.shared.config import ConfigManager  # noqa: E402

SAFETY_CAP = 90
MIN_STEP_TO_CAPTURE = 5
OUT = ROOT / "docs" / "img" / "live_gui_belief_heatmap.png"


def deliver(receiver: MatchRuntime, sender: MatchRuntime, message) -> None:
    """Hand a message over, and route back any immediate reply (a concession)."""
    reply = receiver.on_turn(message)
    if reply is not None:
        sender.on_turn(reply)


def grab_window(window: LiveWindow, out: Path) -> None:
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
    """Play a real two-runtime match and screen-grab the police live window."""
    config_dir = ROOT / "config"
    police = MatchRuntime(
        ConfigManager.load("police", config_dir), game_id="gui-demo", sub_game=1,
        github_commit="localdemo",
    )
    thief = MatchRuntime(
        ConfigManager.load("thief", config_dir), game_id="gui-demo", sub_game=1,
        github_commit="localdemo",
    )

    window = LiveWindow(role="police", grid_size=police.view.board.size)
    window.refresh(police.view)

    captured = False
    for _ in range(SAFETY_CAP):
        if thief.ended and police.ended:
            break
        if not thief.ended:
            deliver(police, thief, thief.play_turn())
            window.refresh(police.view)
        if police.ended and thief.ended:
            break
        if not police.ended:
            deliver(thief, police, police.play_turn())
            window.refresh(police.view)

        if (
            not captured
            and police.view.step >= MIN_STEP_TO_CAPTURE
            and police.view.belief.argmax() is not None
        ):
            grab_window(window, OUT)
            captured = True
            print(f"captured -> {OUT} at step {police.view.step}")

    if not captured:
        window.refresh(police.view)
        grab_window(window, OUT)
        print(f"captured (fallback, final frame) -> {OUT}")

    window.root.destroy()


if __name__ == "__main__":
    main()
