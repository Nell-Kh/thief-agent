"""One peer's local truth during a networked match.

This is everything a peer legally knows: its own position, the public barriers,
the step counter - and its *inferences*: the opponent's absorbed scent, the
belief map, the trust model. The opponent's true position appears nowhere here;
that is the whole game.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..domain.belief import BeliefMap
from ..domain.board import Board, Cell
from ..domain.brain.base import BrainView
from ..domain.scent import ScentField
from ..domain.trust import TrustModel
from ..shared.schema import GameContract


@dataclass
class WorldView:
    """Local truth plus inference state for one peer."""

    role: str
    board: Board
    position: Cell
    my_scent: ScentField
    belief: BeliefMap
    trust: TrustModel
    step: int = 0
    barriers_used: int = 0
    result: dict[str, Any] | None = None
    pending_claim: list[int] | None = None
    #: The cell an opponent named in its ``caught: true`` final, and whether that
    #: merely echoed the cell we broadcast (an *answer*) or named another one (a
    #: *concession*). Kept so the mutual audit can corroborate the claim instead
    #: of believing it - see :func:`domain.audit.verify_concession`.
    final_claim: list[int] | None = None
    final_claim_is_answer: bool = False
    #: The opponent's scent field as of its previous turn - the baseline the
    #: emitter fit differences against (domain/emitter.py).
    last_scent: dict[Cell, float] | None = None
    opponent_step: int = 0
    opponent_barriers: int = 0
    opponent_commits: dict[int, str] = field(default_factory=dict)
    claim_gaps: list[int] = field(default_factory=list)
    history: list[str] = field(default_factory=list)

    @classmethod
    def open(cls, role: str, contract: GameContract) -> WorldView:
        """A fresh view at the contract's opening setup for ``role``."""
        board = Board(contract.board.grid_size)
        start = contract.board.cop_start if role == "police" else contract.board.thief_start
        my_scent = ScentField(board.size, contract.pheromones)
        return cls(
            role=role,
            board=board,
            position=start,
            my_scent=my_scent,
            belief=BeliefMap(board),
            trust=TrustModel(my_scent.expected_fresh_trail(), board.size),
        )

    @property
    def ended(self) -> bool:
        """Whether this peer considers the mini-game decided."""
        return self.result is not None

    def barriers_left(self, contract: GameContract) -> int:
        """Barriers the cop may still place."""
        return max(0, contract.movement.max_barriers - self.barriers_used)

    def brain_view(self, contract: GameContract) -> BrainView:
        """The window the strategy brain receives: target = belief argmax."""
        return BrainView(
            role=self.role,
            position=self.position,
            target=self.belief.argmax(),
            board=self.board,
            barriers_left=self.barriers_left(contract),
            step=self.step,
        )

    def note(self, entry: str) -> None:
        """Append a line to the human-readable narrative."""
        self.history.append(entry)
