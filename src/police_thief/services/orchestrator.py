"""The Orchestrator: a single gateway to every subsystem of a peer.

Instead of each module knowing every other one - which breeds tangled mutual
dependency - all coordination passes through this one component. It owns the
MCP client, the inbound handler, the phase machine, the deadline tracker and the
watchdog, and it hands the game rules to the SDK. It contains **no** decision
logic and **no** low-level communication of its own: its job is to coordinate,
not to execute (rulebook ch. 8.3).

Read-only access to the wired subsystems is a separate concern, mixed in from
:class:`~.orchestrator_accessors.OrchestratorAccessors`.
"""

from __future__ import annotations

from typing import Any

from ..constants import PHASE_TECHNICAL_LOSS
from ..domain.negotiation import build_terms
from ..domain.state import GameState
from ..infra.mcp_client import PeerUnreachableError
from ..infra.transport import Transport
from ..shared.config import ConfigManager
from .deadline import DeadlineExpiredError
from .orchestrator_accessors import OrchestratorAccessors
from .recovery import Recovery
from .wiring import build_subsystems


class Orchestrator(OrchestratorAccessors):
    """Coordinates one peer's subsystems behind a single entry point."""

    def __init__(self, config: ConfigManager, transport: Transport) -> None:
        """Wire the subsystems for one peer.

        Args:
            config: the loaded configuration for this role.
            transport: how messages reach the opponent.
        """
        self._config = config
        self._state: GameState | None = None
        self._recovery = Recovery()
        parts = build_subsystems(config, transport, self._persist, self._recovery.shutdown)
        self._sdk = parts.sdk
        self._phases = parts.phases
        self._client = parts.client
        self._inbound = parts.inbound
        self._watchdog = parts.watchdog

    def start_match(
        self,
        peer_id: str,
        games_played: int,
        sub_game: int = 1,
        step0_commit: str = "unsealed",
        git_commit_hash: str = "",
    ) -> dict[str, Any]:
        """Open a match: create the board and negotiate terms with the opponent.

        The terms carry our contract digest, scent-model lock, declared game
        count, Step-0 commitment and - when the tree is committed - the 40-hex
        git commit of the code playing, so any lock mismatch stops play before
        the first move.
        """
        self._state = self._sdk.new_game()
        self._watchdog.beat()
        terms = build_terms(
            self._config,
            peer_id=peer_id,
            games_played=games_played,
            sub_game=sub_game,
            step0_commit=step0_commit,
            git_commit_hash=git_commit_hash,
        )
        return self._client.negotiate(terms)

    def heartbeat(self) -> str:
        """Report liveness to the watchdog and get its verdict."""
        self._watchdog.beat()
        return self._watchdog.check()

    def guard(self) -> str:
        """Ask the watchdog whether the loop has frozen, without beating."""
        return self._watchdog.check()

    def fail(self, reason: str) -> None:
        """Take the emergency exit: technical loss, announced and recorded.

        A peer that cannot continue must announce a result rather than hang, so
        this is always reachable, from any phase.
        """
        self._phases.fail()
        if self._state is not None:
            self._sdk.forfeit(self._state, reason)

    def run_guarded(self, action: Any) -> Any:
        """Run a step of the turn, converting a stall into a technical loss.

        Any failure to reach the opponent - exhausted retries or an expired
        deadline - ends the turn cleanly instead of leaving it hanging.
        """
        try:
            return action()
        except (PeerUnreachableError, DeadlineExpiredError) as error:
            self.fail(str(error))
            return None

    @property
    def lost(self) -> bool:
        """Whether this peer has reached the terminal technical-loss phase."""
        return self._phases.state == PHASE_TECHNICAL_LOSS

    def _persist(self) -> None:
        """Watchdog callback: keep the state so the match can be recovered."""
        self._recovery.persist(self._state)
