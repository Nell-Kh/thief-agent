"""Thieves that do NOT ship, built to break the shipped cop.

The tournament asks whether the cop converts OUR thieves. That is the wrong
question for the claim "as strong as possible": a cop tuned against three
archetypes may be beaten by the fourth. These are the fourth - each written to
attack one assumption the box cop's plan rests on:

* :class:`SearchThief` - looks as far ahead as the cop does (two plies) and
  maximises the same eval the cop minimises; the mirror image.
* :class:`DoorCamper` - loves the doorway and the cop's own side of the wall,
  the two places the seal opening does not want the thief.
* :class:`Sticker` - hugs the wall column so the halving never separates them.
* :class:`DistanceRunner` - ignores region entirely; pure flight and mobility.

None of them are shipped, none are tuned to be beatable, and the test that
plays them (``test_red_team_cop.py``) is the regression guard for round 5.
"""

from __future__ import annotations

from police_thief.constants import MOVE_STAY
from police_thief.domain.brain.base import BrainBase, BrainView
from police_thief.domain.brain.evade import (
    DISTANCE_CAP,
    W_DISTANCE,
    W_MOBILITY,
    W_OPENNESS,
    W_REGION,
    EvadeThiefBrain,
    openness,
    worst_case_region,
)
from police_thief.domain.brain.pathfind import distance_field
from police_thief.domain.brain.region_geometry import UNREACHABLE, _reach, region_size
from police_thief.domain.brain.search import apply_cop, captured, cop_actions
from police_thief.domain.brain.wall import DOOR, WALL_COLUMN
from police_thief.domain.rules import destination, legal_moves

#: The stone budget the adversaries assume the cop still holds when it is not told.
ASSUMED_STONES = 14


def thief_value(board, cop, thief) -> int:
    """The mirror of the cop's search eval, plus openness - higher is better for the thief."""
    if captured(board, cop, thief):
        return -(10**6)
    distance = _reach(distance_field(board, cop), thief)
    distance = 50 if distance >= UNREACHABLE else distance
    return (
        100 * region_size(board, cop, thief)
        + 10 * len(board.free_neighbours(thief))
        + 4 * min(distance, DISTANCE_CAP)
        + 4 * openness(board, thief)
    )


def _thief_search(board, cop, thief, stones, depth, alpha=-(10**9), beta=10**9) -> int:
    """Minimax from the thief's side: thief moves (max), cop replies (min)."""
    if captured(board, cop, thief):
        return -(10**6)
    if depth == 0:
        return thief_value(board, cop, thief)
    best = -(10**9)
    for move in legal_moves(board, thief):
        cell = destination(thief, move)
        if cell == cop:
            continue
        worst = 10**9
        for action in cop_actions(board, cop, stones):
            after, cop_next = apply_cop(board, cop, action)
            if captured(after, cop_next, cell):
                worst = -(10**6)
                break
            left = stones - (1 if action[1] else 0)
            worst = min(worst, _thief_search(after, cop_next, cell, left, depth - 1, alpha, beta))
            if worst <= alpha:
                break
        best = max(best, worst)
        alpha = max(alpha, best)
        if best >= beta:
            break
    return best


class SearchThief(BrainBase):
    """Two-ply minimax thief - the cop's own weapon turned around."""

    DEPTH = 2

    def _pick_move(self, view: BrainView) -> str:
        """The move whose worst case over the cop's replies is best."""
        best_key: tuple[int, str] | None = None
        best_move = MOVE_STAY
        for move in legal_moves(view.board, view.position):
            cell = destination(view.position, move)
            if cell == view.target:
                continue
            worst = 10**9
            for action in cop_actions(view.board, view.target, ASSUMED_STONES):
                after, cop_next = apply_cop(view.board, view.target, action)
                if captured(after, cop_next, cell):
                    worst = -(10**6)
                    break
                worst = min(worst, _thief_search(after, cop_next, cell, ASSUMED_STONES,
                                                 self.DEPTH - 1))
            key = (worst, str(move))
            if best_key is None or key > best_key:
                best_key, best_move = key, move
        return best_move


class DoorCamper(EvadeThiefBrain):
    """The evader, plus a taste for the doorway and the cop's side of the wall."""

    BONUS = 12

    def _pick_move(self, view: BrainView) -> str:
        """Evade's blend with the door and the cop's half priced as prizes."""
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
            if (cell[1] - WALL_COLUMN) * (view.target[1] - WALL_COLUMN) > 0:
                score += self.BONUS
            if cell == DOOR:
                score += self.BONUS
            key = (score, str(move))
            if best_key is None or key > best_key:
                best_key, best_move = key, move
        return best_move


class Sticker(BrainBase):
    """Hugs the wall column: distance from the cop, mobility, never a side."""

    def _pick_move(self, view: BrainView) -> str:
        """Best of distance, mobility and openness, penalised for leaving column 3."""
        best_key: tuple[int, str] | None = None
        best_move = MOVE_STAY
        cop_field = distance_field(view.board, view.target)
        for move in legal_moves(view.board, view.position):
            cell = destination(view.position, move)
            if cell == view.target:
                continue
            score = (
                10 * min(_reach(cop_field, cell), 8)
                + 3 * len(view.board.free_neighbours(cell))
                - 4 * abs(cell[1] - WALL_COLUMN)
                + 2 * openness(view.board, cell)
            )
            key = (score, str(move))
            if best_key is None or key > best_key:
                best_key, best_move = key, move
        return best_move


class DistanceRunner(BrainBase):
    """Pure flight: the worst-case distance after any cop reply, then mobility."""

    def _pick_move(self, view: BrainView) -> str:
        """Maximise the minimum distance the cop can force next turn."""
        best_key: tuple[int, str] | None = None
        best_move = MOVE_STAY
        for move in legal_moves(view.board, view.position):
            cell = destination(view.position, move)
            if cell == view.target:
                continue
            worst = 10**9
            for action in cop_actions(view.board, view.target, ASSUMED_STONES):
                after, cop_next = apply_cop(view.board, view.target, action)
                if captured(after, cop_next, cell):
                    worst = -1
                    break
                distance = _reach(distance_field(after, cop_next), cell)
                distance = 60 if distance >= UNREACHABLE else distance
                worst = min(worst, distance * 10 + len(after.free_neighbours(cell)))
            key = (worst, str(move))
            if best_key is None or key > best_key:
                best_key, best_move = key, move
        return best_move


ADVERSARIES = {
    "search2": SearchThief,
    "doorcamper": DoorCamper,
    "sticker": Sticker,
    "distrunner": DistanceRunner,
}
