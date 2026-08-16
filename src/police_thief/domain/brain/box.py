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
wall stands, hands the position to :mod:`search`: a two-ply minimax that
prices the thief's best reply before choosing, which is exactly one ply
deeper than the evader looks. With the board halved the branching is small
enough for it to be cheap and the horizon short enough for it to be decisive:
from the seal cop's own turn-20 chamber it boxes the thief in five turns, and
handed the crossing and the door as well it is a step faster still.

Where the hand-off sits was measured, not chosen. Handing over BEFORE the
wall is complete is catastrophic - 0 of 40 starts - because a two-ply horizon
cannot see what a wall is worth and so never finishes one; handing over only
once the door is stoned leaves the seal cop's door campaign in charge of the
crossing and costs about a step. The structure is built by plan; the moment it
exists, the search owns the position.

Measured under perfect information against the elite evader: the fixed start
is a capture at 24 steps, 60 of 60 sampled starts are captures (mean 25.7,
worst 30), where the seal cop managed 11 of 60. Red-teamed against thieves
built to break it - a two-ply search thief, a door camper, a wall-hugger, a
pure distance runner - it converts every start of every one.
"""

from __future__ import annotations

from ..engine import Action
from .base import BrainView
from .seal import SealPoliceBrain, _side
from .search import best_action

#: Cop decisions the endgame search looks ahead. Two is one more than the
#: evader prices, and the depth at which the chamber falls in five turns;
#: three was measured no faster and several times the cost.
ENDGAME_DEPTH = 2


class BoxPoliceBrain(SealPoliceBrain):
    """Wall, cross, seal - and then out-think the thief inside the chamber."""

    def _decide_move(self, view: BrainView) -> Action:
        """The seal opening until the wall stands; the search after."""
        if self._search_owns(view):
            move, stone = best_action(
                view.board, view.position, view.target, view.barriers_left, ENDGAME_DEPTH
            )
            return Action(move=move, barrier=stone)
        return super()._decide_move(view)

    def _search_owns(self, view: BrainView) -> bool:
        """The wall stands and the believed thief is not in the doorway column.

        A believed thief in the wall column (side 0) is ambiguous - it may be
        in the door, or a one-cell belief error beside it - and the seal cop's
        adjacent-trap rule owns that case; the search takes every other.
        """
        return self._wall_stands(view.board) and _side(view.target[1]) != 0
