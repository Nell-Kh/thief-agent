"""The open-field thief: survive by keeping options, distance and open sky.

The other half of the phase-8 arms race. The enhanced thief's lexicographic
scoring loses to the region cop in ~9 steps; every strict priority order
tried in the notebook loses too. What works is a *blend*: weigh together the
worst-case safe region after the cop's best reply (max-min, one ply), the
true-path distance from the believed cop, the cell's openness (distance from
the nearest edge - walls are where strangulation begins), and its mobility.
Against the region cop this thief survives 60/72 starts (mean 30 of 35
steps) where the enhanced thief survived none; against pursuit-style cops
it still survives everything.

Round 4 of the arms race (2026-08-16) put it back in front of the barrier
cops too, by fixing what ``openness`` measured rather than by adding a term:
a stone is a wall, and pricing it as one keeps the thief out of the doorway
a wall cop leaves for it. Measured through the real blind pipeline from the
contract's fixed start, it now SURVIVES ALL SIX cops in the tree - blind,
enhanced, region, wall, hybrid and seal - where the shipped weights survived
three.
"""

from __future__ import annotations

from ...constants import MOVE_STAY
from ..board import Board, Cell
from ..rules import barrier_placements, destination, legal_moves
from .base import BrainView
from .blind import BlindThiefBrain
from .pathfind import distance_field
from .region import _reach, region_size

#: Weight of the worst-case own safe region (max-min over cop replies).
W_REGION = 1

#: Weight of the true-path distance from the believed cop.
W_DISTANCE = 4

#: Weight of open air - distance from the nearest edge OR BARRIER.
W_OPENNESS = 4

#: Weight of mobility - the number of free neighbouring cells.
W_MOBILITY = 2

#: Distance beyond this earns nothing more - being "far" saturates.
DISTANCE_CAP = 8


def openness(board: Board, cell: Cell) -> int:
    """Distance to the nearest wall - an edge OR a placed barrier.

    This measured only the board edge until 2026-08-16, which made it blind to
    the very thing the strategy exists to avoid. A cop that builds a wall with
    one door leaves that door at the board's centre, and an edge-only reading
    scores the doorway as the most open cell there is: traced under belief, the
    thief drifted into the doorway, was sealed into the half the cop had
    entered, and was hunted down in a closed chamber. Counting a placed stone
    as a wall - which is what it is - is what turned that game around.
    """
    row, col = cell
    nearest = min(row, col, board.size - 1 - row, board.size - 1 - col)
    for stone in board.barriers:
        nearest = min(nearest, max(abs(stone[0] - row), abs(stone[1] - col)) - 1)
    return nearest


def worst_case_region(board: Board, cell: Cell, cop: Cell) -> int:
    """Our safe region from ``cell`` after the cop's most damaging reply.

    One ply of pessimism: the cop may step anywhere legal or drop any legal
    barrier. Pricing the *reply* rather than the present is what lets the
    thief walk out of traps one turn before they close.
    """
    worst = region_size(board, cop, cell)
    for move in legal_moves(board, cop):
        worst = min(worst, region_size(board, destination(cop, move), cell))
    for stone in barrier_placements(board, cop):
        if stone in (cell, cop):
            continue
        trial = Board(board.size, set(board.barriers) | {stone})
        worst = min(worst, region_size(trial, cop, cell))
    return worst


class EvadeThiefBrain(BlindThiefBrain):
    """Maximize the weighted blend of region, distance, openness, mobility."""

    def _pick_move(self, view: BrainView) -> str:
        """The best-scoring legal move; never step onto the believed cop."""
        best_key: tuple[int, str] | None = None
        best_move = MOVE_STAY
        cop_field = distance_field(view.board, view.target)
        for move in legal_moves(view.board, view.position):
            cell = destination(view.position, move)
            if cell == view.target:
                continue
            score = (
                W_REGION * worst_case_region(view.board, cell, view.target)
                + W_DISTANCE * min(_reach(cop_field, cell), DISTANCE_CAP)
                + W_OPENNESS * openness(view.board, cell)
                + W_MOBILITY * len(view.board.free_neighbours(cell))
            )
            key = (score, str(move))
            if best_key is None or key > best_key:
                best_key, best_move = key, move
        return best_move
