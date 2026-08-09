"""Determinism sweep (guidelines verification pass, TODO 8.18.9).

Two independent claims, both load-bearing for a judge-less league: (1) two
fresh brains, replayed from the same start against the same opponent, must
reach the identical trajectory - a brain is a pure function of state, not of
an instance's incidental history (§6 of the README); (2) replaying one saved
log twice through independent :class:`ReplaySession` objects must produce
byte-identical scenes and verdicts - the Replay Viewer must never be a source
of nondeterminism itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.audit import VERDICT_OK
from police_thief.domain.brain.enhanced import EnhancedThiefBrain
from police_thief.domain.brain.region import RegionPoliceBrain
from police_thief.domain.logbook import Logbook
from police_thief.domain.replay import ReplaySession
from police_thief.domain.sealing import turn_record
from police_thief.domain.state import GameState
from police_thief.sdk import SimulationSdk
from police_thief.services.runtime import LocalMatchRunner
from police_thief.shared.config import ConfigManager
from police_thief.shared.config_io import canonical_json


def _play_once(config_dir: Path) -> GameState:
    """Play one full match from the fixed start and return its trajectory."""
    config = ConfigManager.load("police", config_dir)
    sdk = SimulationSdk(config)
    runner = LocalMatchRunner(
        sdk,
        police_brain=RegionPoliceBrain("cop", config.contract),
        thief_brain=EnhancedThiefBrain("thief", config.contract),
    )
    return runner.play()


def test_two_full_matches_from_the_same_start_reach_the_same_trajectory(
    config_dir: Path,
) -> None:
    """Fresh brains, same start, same opponent: identical outcome, every step."""
    first = _play_once(config_dir)
    second = _play_once(config_dir)

    assert first.history == second.history  # step-by-step move log, byte-equal
    assert first.cop == second.cop
    assert first.thief == second.thief
    assert first.barriers_used == second.barriers_used
    assert first.outcome == second.outcome


@pytest.fixture
def played_log() -> Logbook:
    """A three-turn sealed log built from a scripted, non-random trajectory."""
    book = Logbook("determinism", 1, "thief")
    walls: list[tuple[int, int]] = []
    for step, (position, move) in enumerate(
        [((2, 3), "N"), ((2, 4), "E"), ((2, 5), "E")], start=1
    ):
        if step == 2:
            walls.append((4, 4))
        book.append(
            turn_record(
                step=step, role="thief", grid_size=7, position=position,
                barriers=frozenset(walls), move=move, intent="truth",
                hint=f"hint {step}", tokens_step=0, tokens_total=0,
            )
        )
    return book


def test_replaying_the_same_log_twice_is_byte_identical(played_log: Logbook) -> None:
    """Two independent ReplaySession walks over one log agree at every step."""
    scenes_a: list[dict] = []
    session_a = ReplaySession(played_log)
    for _ in range(len(session_a.turns)):
        scenes_a.append(session_a.scene())
        session_a.forward()
    scenes_a.append(session_a.scene())

    scenes_b: list[dict] = []
    session_b = ReplaySession(played_log)
    for _ in range(len(session_b.turns)):
        scenes_b.append(session_b.scene())
        session_b.forward()
    scenes_b.append(session_b.scene())

    assert canonical_json(scenes_a) == canonical_json(scenes_b)
    assert session_a.overall_verdict() == session_b.overall_verdict() == VERDICT_OK
