"""The box cop: the seal cop's opening, then a search that actually closes.

Round 5 of the arms race. Round 4 gave the elite evader an ``openness`` that
prices a stone as a wall, and with it the thief walked past every cop in the
tree - measured under PERFECT INFORMATION from the contract's fixed start,
not one of the four barrier cops converted it, and the best of them (seal)
converted 11 starts in 60. That is also what a real opponent's elite thief
did to us three times running (sharNamr, 0-6, 2026-08-17).

The trace of the seal cop's loss says exactly where the game goes: the wall
is up by turn 14, the door is sealed by turn 20, and the position is a closed
3x7 chamber holding cop, thief and seven stones with fifteen turns left -
and the inherited region hunt then dances between two cells for all fifteen
while the thief sits in the far corner. The opening is right; the endgame is
what loses.

So this brain keeps the seal cop's opening untouched and, the moment the
chamber closes - wall complete, door stoned, both players on one side - hands
the position to :mod:`search`: a two-ply minimax that prices the thief's best
reply before choosing, which is exactly one ply deeper than the evader looks.
Inside the chamber the branching is small enough for it to be cheap and the
horizon short enough for it to be decisive: from that same turn-20 position it
boxes the thief in five turns.

Measured under perfect information against the elite evader: the fixed start
is a capture at 25 steps, and 60 of 60 sampled starts are captures, mean 26.7
steps - where the seal cop managed 11.
"""

from __future__ import annotations

from ..engine import Action
from .base import BrainView
from .seal import SealPoliceBrain, _side
from .search import best_action
from .wall import DOOR

#: Cop decisions the endgame search looks ahead. Two is one more than the
#: evader prices, and the depth at which the chamber falls in five turns.
ENDGAME_DEPTH = 2


class BoxPoliceBrain(SealPoliceBrain):
    """Wall, cross, seal - and then out-think the thief inside the chamber."""

    def _decide_move(self, view: BrainView) -> Action:
        """The seal opening until the chamber is closed; the search after."""
        if self._chamber_closed(view):
            move, stone = best_action(
                view.board, view.position, view.target, view.barriers_left, ENDGAME_DEPTH
            )
            return Action(move=move, barrier=stone)
        return super()._decide_move(view)

    def _chamber_closed(self, view: BrainView) -> bool:
        """Wall complete, door stoned, cop and believed thief in the same half.

        A believed thief in the doorway column (side 0) is never "the same
        half" - the seal cop's own rule - so a one-cell belief error at the
        door cannot start the endgame in the wrong room.
        """
        return (
            self._wall_stands(view.board)
            and view.board.is_barrier(DOOR)
            and _side(view.position[1]) == _side(view.target[1]) != 0
        )
