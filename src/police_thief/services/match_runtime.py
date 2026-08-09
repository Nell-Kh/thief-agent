"""The networked peer: one whole mini-game over the ADR-7 wire.

Ties every layer together for one role: negotiation with Step-0 sealed first,
the alternating turn loop (the thief moves first, as in the reference
implementation), scent and belief inference on every received message, and the
closing mutual audit. The strategy module is consulted exactly where the
rulebook demands - after the incoming hint is decoded, before the outgoing
commitment is packed.

End-of-game audit reporting and scoring are a separate concern, mixed in
from :class:`~.match_reporting.MatchReporting`.
"""

from __future__ import annotations

from typing import Any

from ..domain.logbook import Logbook
from ..domain.rules import is_trapped
from ..domain.sealing import step0_record
from ..domain.turnmsg import TurnMessage
from ..infra.llm import TokenLedger, build_provider
from ..shared.config import ConfigManager
from ..shared.sysinfo import hardware_spec
from ..shared.version import __version__
from .concession import concession_message
from .deception import policy_from_config
from .match_reporting import MatchReporting
from .runtime import configured_brain
from .turn_receiving import receive_turn
from .turn_taking import take_turn
from .world_view import WorldView


def _verbal_rate_limit(path: str = "config/rate_limits.json") -> int | None:
    """The verbal layer's requests-per-minute ceiling, from configuration.

    Closes the gap that left `config/rate_limits.json`'s ``anthropic`` block
    read by no code path: a configured limit that controlled nothing. Returns
    ``None`` when the file or the entry is absent, so a checkout without the
    config still plays - unlimited, but never crashing on a missing limit.
    """
    from ..shared.config_io import ConfigError, read_json

    try:
        services = read_json(path)["rate_limits"]["services"]
    except (ConfigError, KeyError, TypeError):
        return None
    entry = services.get("anthropic") or services.get("default") or {}
    limit = entry.get("requests_per_minute")
    return int(limit) if limit else None


class MatchRuntime(MatchReporting):
    """One peer's engine for a complete networked mini-game."""

    def __init__(
        self, config: ConfigManager, game_id: str, sub_game: int, github_commit: str
    ) -> None:
        """Assemble the peer's world, brain, verbal chain and logbook."""
        self.config = config
        self.contract = config.contract
        self.view = WorldView.open(config.role, self.contract)
        self.brain = configured_brain(config, config.role)
        self.ledger = TokenLedger(budget=self.contract.network.token_budget_per_series)
        self.provider = build_provider(
            provider_name=str(config.private_value("trash_talk", "provider", "template")),
            every_n_steps=int(config.private_value("trash_talk", "every_n_steps", 1)),
            ledger=self.ledger,
            model=str(config.private_value("llm", "model", "")),
            timeout_sec=float(config.private_value("llm", "step_deadline_seconds", 10)),
            requests_per_minute=_verbal_rate_limit(),
        )
        self.book = Logbook(game_id, sub_game, config.role)
        self.policy = policy_from_config(config)
        self._conceded = False
        self.step0 = self.book.append(
            step0_record(
                spec=hardware_spec(),
                model=str(config.private_value("llm", "model", "template")),
                code_version=__version__,
                github_commit=github_commit,
                group_name=str(config.private_value("game", "group_name", "unknown")),
                sub_game_number=sub_game,
                token_budget=self.contract.network.token_budget_per_series,
            )
        )

    @property
    def step0_commit(self) -> str:
        """The Step-0 commitment offered at negotiation."""
        return str(self.step0["commit"])

    @property
    def ended(self) -> bool:
        """Whether this peer considers the mini-game decided."""
        return self.view.ended

    @property
    def result(self) -> dict[str, Any] | None:
        """The result this peer will claim at the audit."""
        return self.view.result

    def play_turn(self) -> TurnMessage:
        """Compose and locally apply this peer's turn; caller sends the message."""
        message = take_turn(
            view=self.view,
            contract=self.contract,
            brain=self.brain,
            provider=self.provider,
            ledger=self.ledger,
            book=self.book,
            policy=self.policy,
        )
        if (
            self.view.role == "thief"
            and self.view.step >= self.contract.movement.survival_threshold
            and self.view.result is None
        ):
            self.view.result = {"type": "survival", "winner": "thief"}
        return message

    def on_turn(self, message: TurnMessage) -> TurnMessage | None:
        """Fold an opponent's turn message into our world.

        Returns:
            A final concession message when this turn just ended the game
            against us - the thief's cell was walled (rule 46), the thief is
            boxed in with no legal step (rule 47), or a capture claim landed.
            Rules 46/47 are facts only the thief can observe (kit SPEC §3.1):
            a thief that stays silent here forks the game - it settles CAPTURE
            locally while the cop, having learned nothing, waits out the clock
            and settles TIMEOUT, the exact contradictory-report shape that
            zeroes both teams. The caller must deliver the reply.
        """
        receive_turn(self.view, message, self.contract)
        if self.view.role != "thief" or self._conceded:
            return None
        if self.view.result is None and is_trapped(self.view.board, self.view.position):
            self.view.result = {"type": "capture", "winner": "police", "how": "boxed in (rule 47)"}
            self.view.note("every exit is a barrier - conceding the rule-47 capture")
        if (self.view.result or {}).get("winner") == "police":
            self._conceded = True
            return concession_message(view=self.view, book=self.book)
        return None
