"""A peer gets every second of the deadline both sides signed.

The driver waited 60 seconds for an opponent's turn while
``config/police/game.toml`` declared ``turn_timeout_seconds = 180`` - the
rulebook's own field, the number we publish to every opponent at the handshake.
So the deadline we advertised and the deadline we enforced were different
numbers, and the shorter one was the secret.

nis-yar1 (2026-08-17) stated a 180-second turn deadline in their opening letter.
Their thief negotiated cleanly and then did not deliver its opening turn inside
60 seconds. We scored sub-game 1 a technical loss against an opponent doing
nothing wrong, advanced to sub-game 2, and spent the rest of the series
refusing their greetings - correctly, on our own terms - because they were
still playing sub-game 1 while we had moved on. One number, six sub-games.

The lesson is not "60 was too small". It is that a timeout shorter than the
declared one does not protect us from a slow peer; it manufactures the failure
it exists to survive, and then desynchronises everything behind it. So the wait
is READ FROM THE CONTRACT, and ``--turn-wait`` may only raise it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from _series_lib import TURN_WAIT_TIMEOUT  # noqa: E402
from _series_subgame import turn_wait_for  # noqa: E402

from police_thief.shared.config import ConfigManager  # noqa: E402


def test_the_wait_is_the_deadline_our_own_config_declares() -> None:
    """Not a constant in the driver - the number we publish to opponents."""
    config = ConfigManager.load("police")
    declared = float(config.private_value("network", "turn_timeout_seconds", 0))
    assert declared > 0, "our config must declare a turn deadline at all"
    assert turn_wait_for(config, SimpleNamespace(turn_wait=0.0)) == declared


def test_an_opponent_with_a_longer_deadline_raises_ours() -> None:
    """``--turn-wait`` accommodates a peer who declared more time than we did."""
    config = ConfigManager.load("police")
    assert turn_wait_for(config, SimpleNamespace(turn_wait=600.0)) == 600.0


def test_the_override_can_never_shorten_the_signed_deadline() -> None:
    """The one direction that must be impossible: quitting on a compliant peer."""
    config = ConfigManager.load("police")
    declared = float(config.private_value("network", "turn_timeout_seconds", 0))
    assert turn_wait_for(config, SimpleNamespace(turn_wait=5.0)) == declared
    assert turn_wait_for(config, SimpleNamespace()) == declared


def test_the_fallback_is_not_shorter_than_the_deadline_we_ship() -> None:
    """A config with no declared deadline must not fall back to something meaner."""
    declared = float(ConfigManager.load("police").private_value(
        "network", "turn_timeout_seconds", 0))
    assert declared <= TURN_WAIT_TIMEOUT, (
        f"the fallback wait {TURN_WAIT_TIMEOUT} is below the {declared}s we declare - "
        f"that is the nis-yar1 failure with the numbers moved around"
    )
