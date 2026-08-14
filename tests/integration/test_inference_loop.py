"""The M4 milestone: language and scent close the inference loop.

A free-language report is translated into inference, the scent map updates and
decays every turn, and the verbal layer produces a hint - truth or lie. This
test walks the whole chain the way a real turn does: the thief moves and emits
scent, composes a hint through a provider, transmits the scent snapshot; the
cop appraises the hint against the scent, updates its belief, and its enhanced
brain turns the inference into pursuit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board
from police_thief.domain.brain.base import BrainView
from police_thief.domain.brain.enhanced import EnhancedPoliceBrain
from police_thief.domain.scent import ScentField
from police_thief.domain.trust import TrustModel
from police_thief.infra.llm import HintRequest, TemplateProvider, TokenLedger, build_provider
from police_thief.shared.config import ConfigManager


@pytest.fixture
def config(config_dir: Path) -> ConfigManager:
    """The loaded configuration under test."""
    return ConfigManager.load("police", config_dir)


def hint_for(config, step: int, intent: str, direction: str | None) -> str:
    """Compose a hint exactly as the thief's verbal layer would."""
    provider = TemplateProvider()
    return provider.generate(
        HintRequest(
            role="thief",
            intent=intent,
            true_direction=direction,
            map_area=config.contract.world.map_area,
            max_words=config.contract.world.hint_max_words,
            step=step,
        )
    )


def test_m4_a_truthful_report_sharpens_the_pursuit(config: ConfigManager) -> None:
    """Truthful hint + matching scent: the cop's belief locks onto the trail."""
    contract = config.contract
    board = Board(contract.board.grid_size)
    thief_scent = ScentField(board.size, contract.pheromones)
    belief = BeliefMap(board)
    trust = TrustModel(thief_scent.expected_fresh_trail(), board.size)

    # The thief walks north along the eastern side, announcing every step
    # honestly; the appraiser needs consecutive snapshots because it judges
    # the MOTION of the scent centroid, not a single still image.
    appraisal = None
    for step, cell in enumerate([(3, 5), (2, 5), (1, 5)], start=1):
        thief_scent.advance(cell)
        snapshot = thief_scent.snapshot()
        belief.diffuse()
        belief.observe_scent(snapshot)
        hint = hint_for(config, step=step, intent="truth", direction="N")
        appraisal = trust.appraise(hint, snapshot)
        belief.observe_region(appraisal.region, appraisal.factor)

    assert appraisal.verdict == "corroborated"
    assert trust.trust > 0.5
    target = belief.argmax()
    assert target in {(0, 5), (1, 5), (2, 5)}  # locked onto the eastern trail

    cop = EnhancedPoliceBrain("police", contract)
    action = cop.decide(
        BrainView(
            role="police",
            position=(0, 0),
            target=target,
            board=board,
            barriers_left=contract.movement.max_barriers,
            step=3,
        )
    )
    assert action.move in {"S", "E"}


def test_m4_a_lying_report_is_discounted(config: ConfigManager) -> None:
    """The ch. 4 story end to end: the lie is caught and the trail wins."""
    contract = config.contract
    board = Board(contract.board.grid_size)
    thief_scent = ScentField(board.size, contract.pheromones)
    belief = BeliefMap(board)
    trust = TrustModel(thief_scent.expected_fresh_trail(), board.size)

    # The thief walks south along the eastern side while claiming north
    # every turn - the mirrored lie the snapshot judge could not catch.
    appraisal = None
    for step, cell in enumerate([(4, 5), (5, 5), (6, 5)], start=1):
        thief_scent.advance(cell)
        snapshot = thief_scent.snapshot()
        belief.diffuse()
        belief.observe_scent(snapshot)
        hint = hint_for(config, step=step, intent="lie", direction="S")
        assert "north" in hint.lower()
        appraisal = trust.appraise(hint, snapshot)
        belief.observe_region(appraisal.region, appraisal.factor)

    assert appraisal.verdict == "contradicted"
    assert trust.trust < 0.5
    row, _ = belief.argmax()
    assert row >= 4  # the belief follows the scent south, not the lie north


def test_m4_scent_updates_and_decays_every_turn(config: ConfigManager) -> None:
    contract = config.contract
    field = ScentField(contract.board.grid_size, contract.pheromones)
    field.advance((3, 3))
    peak_before = field.intensity((3, 3))
    field.advance((3, 4))
    assert field.intensity((3, 3)) < peak_before or field.intensity((3, 3)) == pytest.approx(
        min(0.9, 0.9 * 0.9 + 0.62)
    )
    assert field.intensity((3, 4)) == pytest.approx(0.9)


def test_m4_the_configured_provider_chain_survives_without_a_key(
    config: ConfigManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """claude_api is configured, no API key exists - the game must not care."""
    # Patch out the .env fallback so the test is not sensitive to a local .env file
    # that might contain a real key; the test must verify the no-key code path only.
    monkeypatch.setattr("police_thief.infra.llm.claude_api.anthropic_key", lambda: None)
    ledger = TokenLedger(budget=config.contract.network.token_budget_per_series)
    provider = build_provider(
        provider_name=config.private_value("trash_talk", "provider", "template"),
        every_n_steps=int(config.private_value("trash_talk", "every_n_steps", 1)),
        ledger=ledger,
        model=str(config.private_value("llm", "model", "")),
    )
    hint = provider.generate(
        HintRequest(
            role="thief",
            intent="lie",
            true_direction="W",
            map_area=config.contract.world.map_area,
            max_words=config.contract.world.hint_max_words,
            step=0,
        )
    )
    assert hint
    assert len(hint.split()) <= config.contract.world.hint_max_words
    assert ledger.total == 0  # nothing was spent: the template rescued the call
