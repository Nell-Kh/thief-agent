"""Shared pytest fixtures.

Fixtures load the *shipped* configuration files so the test suite also proves
that ``config/game.json`` itself stays consistent with the rulebook's Mandatory
Parameters Table.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from police_thief.shared.config_io import read_json, read_toml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"


@pytest.fixture
def config_dir() -> Path:
    """Path of the shipped ``config/`` directory."""
    return CONFIG_DIR


@pytest.fixture
def raw_shared() -> dict[str, Any]:
    """The shipped shared contract, freshly parsed for each test."""
    return read_json(CONFIG_DIR / "game.json")


@pytest.fixture
def raw_private_police() -> dict[str, Any]:
    """The shipped private configuration of the police peer."""
    return read_toml(CONFIG_DIR / "police" / "game.toml")


@pytest.fixture
def raw_private_thief() -> dict[str, Any]:
    """The shipped private configuration of the thief peer."""
    return read_toml(CONFIG_DIR / "thief" / "game.toml")


@pytest.fixture
def config_copy(tmp_path: Path) -> Path:
    """A writable copy of ``config/`` for tests that mutate configuration."""
    destination = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, destination)
    return destination


class FakeClock:
    """A hand-cranked monotonic clock, so timing tests never sleep."""

    def __init__(self) -> None:
        """Start the shared fake clock at zero."""
        self.now = 0.0

    def __call__(self) -> float:
        """Return the current fake time, standing in for ``time.monotonic``."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the clock forward."""
        self.now += seconds


@pytest.fixture
def fake_clock() -> FakeClock:
    """A monotonic clock the test drives by hand."""
    return FakeClock()


@pytest.fixture
def network_config(config_dir: Path):
    """The contract's network timings."""
    from police_thief.shared.config import ConfigManager

    return ConfigManager.load("police", config_dir).contract.network


@pytest.fixture
def rate_limits(config_dir: Path):
    """The contract's gatekeeper limits."""
    from police_thief.shared.config import ConfigManager

    return ConfigManager.load("police", config_dir).contract.rate_limiter
