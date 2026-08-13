"""The region cop: shrink the thief's safe region until nothing is left.

Born in the phase-8 research notebook. The pinch cop (``enhanced.py``)
converts 0/72 starts even with perfect information - pure pursuit on a grid
with equal speeds is a parity dance, and reactive pinches never fire at the
diagonal where the dance settles. The cure is to stop chasing the thief and
start strangling its *options*: every turn, minimize the number of cells the
thief can reach before the cop (its safe region), tie-broken by the thief's
exit count and then by closing distance. A barrier must starve the region by
:attr:`RegionPoliceBrain.MIN_SHRINK` cells in the mid-game - quota is finite -
but once the region is down to :attr:`RegionPoliceBrain.ENDGAME` cells, any
exit sealed is progress the thief can never undo. Result on the same 72
starts: 72 captures, mean 9 steps, ~1 barrier.

The region-size metric and its BFS helpers live in :mod:`region_geometry`.
"""

from __future__ import annotations

from ...constants import MOVE_STAY
from ..board import Board, Cell
from ..engine import Action
from ..rules import barrier_placements, destination, legal_steps
from .base import BrainView
from .blind import BlindPoliceBrain
from .pathfind import distance_field
from .region_geometry import UNREACHABLE, ScoreKey, _anchored, _reach, region_size

__all__ = ["UNREACHABLE", "RegionPoliceBrain", "ScoreKey", "region_size"]


class RegionPoliceBrain(BlindPoliceBrain):
    """Greedy minimizer of the thief's safe region, exits and distance."""

    #: Mid-game gate: a barrier must shrink the region by this many cells.
    MIN_SHRINK = 3

    #: Region size at which every sealed exit is worth a barrier.
    ENDGAME = 4

    def __init__(self, role: str, contract) -> None:
        """Bind the brain and start the repetition memory empty."""
        super().__init__(role, contract)
        self._seen: set[tuple[Cell, Cell, int]] = set()

    def _decide_move(self, view: BrainView) -> Action:
        """Trap when adjacent; otherwise the option with the best score key.

        A repeated ``(cop, thief, stones)`` state is the signature of the
        parity dance - two equal-speed walkers orbiting a pillar forever. The
        answer is always the same: buy a stone. One anchored barrier cuts the
        orbit ring and the region hunt converts what pursuit never could.
        """
        if view.barriers_left > 0 and self._can_trap(view):
            return Action(move=MOVE_STAY, barrier=view.target)
        state = (view.position, view.target, len(view.board.barriers))
        repeated = state in self._seen
        self._seen.add(state)
        if repeated and view.barriers_left > 0:
            stone = self._dance_breaker(view)
            if stone is not None:
                return Action(move=MOVE_STAY, barrier=stone)
        options = self._move_options(view) + self._barrier_options(view)
        return min(options)[1]

    def _dance_breaker(self, view: BrainView) -> Cell | None:
        """The best cycle-cutting stone: anchored, hunt-preserving, region-min."""
        best_key: tuple[int, str] | None = None
        best: Cell | None = None
        for cell in barrier_placements(view.board, view.position):
            if cell in (view.position, view.target) or not _anchored(view.board, cell):
                continue
            trial = Board(view.board.size, set(view.board.barriers) | {cell})
            if _reach(distance_field(trial, view.position), view.target) >= UNREACHABLE:
                continue  # never wall ourselves away from the hunt
            key = (region_size(trial, view.position, view.target), str(cell))
            if best_key is None or key < best_key:
                best_key, best = key, cell
        return best

    def _move_options(self, view: BrainView) -> list[tuple[ScoreKey, Action]]:
        """Every displacing step, scored on the board as it stands.

        A move never changes the thief's exits, so the current exit count is
        the tie-break; ``STAY`` is deliberately absent - a cop that neither
        moves nor builds is donating a turn to the parity dance.
        """
        exits_now = len(view.board.free_neighbours(view.target))
        options: list[tuple[ScoreKey, Action]] = []
        for move in legal_steps(view.board, view.position):
            position = destination(view.position, move)
            size = region_size(view.board, position, view.target)
            distance = _reach(distance_field(view.board, view.target), position)
            options.append(((size, exits_now, distance, 0, str(move)), Action(move=move)))
        return options

    def _barrier_options(self, view: BrainView) -> list[tuple[ScoreKey, Action]]:
        """Every worthwhile placement, scored on a trial board.

        Worthwhile means a :attr:`MIN_SHRINK` region cut, or - inside the
        endgame - any reduction of the thief's exit count. The barrier flag in
        the key makes an equally-scored move win: quota is the scarcer coin.
        """
        if view.barriers_left <= 0:
            return []
        here = region_size(view.board, view.position, view.target)
        exits_now = len(view.board.free_neighbours(view.target))
        options: list[tuple[ScoreKey, Action]] = []
        for cell in barrier_placements(view.board, view.position):
            if cell in (view.position, view.target):
                continue
            trial = Board(view.board.size, set(view.board.barriers) | {cell})
            size = region_size(trial, view.position, view.target)
            cut_off = _reach(distance_field(trial, view.position), view.target) >= UNREACHABLE
            if cut_off and trial.free_neighbours(view.target):
                # A stone that cuts us off from the hunt is only ever right
                # when it BOXES the thief outright (rule 47: no free exit
                # left). Anything less is self-exile: the believed pocket may
                # be wrong by a cell, and a cop that cannot reach its prey
                # hands the thief the rest of the clock - the exact loss a
                # missed doorway trap inflicted in the first live blind run.
                continue
            exits = len(trial.free_neighbours(view.target))
            worthwhile = size <= here - self.MIN_SHRINK or (
                here <= self.ENDGAME and exits < exits_now
            )
            if not worthwhile:
                continue
            distance = _reach(distance_field(trial, view.target), view.position)
            options.append(
                ((size, exits, distance, 1, str(cell)), Action(move=MOVE_STAY, barrier=cell))
            )
        return options
