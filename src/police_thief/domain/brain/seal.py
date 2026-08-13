"""The seal cop: wall the board, cross the door, and lock it behind you.

Round three of the arms race, forced by the first live blind measurement.
The wall cop's guarantee ("1900/1900 captures") was measured with the
thief's true position; under belief - the only condition a league match is
played in - our own evader beat it six times out of six by camping the
doorway. The diagnostic run showed the belief was nearly perfect (mean
error under one cell): the cop KNEW where the thief was and still oscillated
two cells from the door forever, because every greedy metric plateaued and
every dance-breaking stone would have cut the only path to the target.

The cure is commitment, not information. Once the wall stands and the
believed thief is across it: march to the door, step through, and spend one
stone ON the door. The board becomes a closed 7x3 chamber holding both
players and the remaining quota - and inside a chamber with no door to
preserve, the inherited region hunt's dance breaker can finally cut every
orbit. Sealing is only attempted when the belief puts the thief on OUR side
of the wall (never while it sits in the doorway), so a one-cell belief
error cannot lock the cop into an empty half.
"""

from __future__ import annotations

from ...constants import MOVE_STAY
from ..board import Board
from ..engine import Action
from .base import BrainView
from .pathfind import distance_field, step_toward
from .region_geometry import UNREACHABLE, _reach
from .wall import DOOR, WALL_COLUMN, WallPoliceBrain, wall_progress

#: The number of stones the finished wall holds (six rows, one door).
WALL_STONES = 6


def _side(column: int) -> int:
    """Which half a column lies in: -1 left of the wall, +1 right, 0 on it."""
    if column < WALL_COLUMN:
        return -1
    return 1 if column > WALL_COLUMN else 0


class SealPoliceBrain(WallPoliceBrain):
    """Wall builder that finishes the job by locking the door behind itself."""

    def _decide_move(self, view: BrainView) -> Action:
        """Trap, build, campaign for the door, then hunt - in that order."""
        if view.barriers_left > 0 and self._can_trap(view):
            return Action(move=MOVE_STAY, barrier=view.target)
        if self._wall_stands(view.board) and view.board.is_free(DOOR):
            campaign = self._door_campaign(view)
            if campaign is not None:
                return campaign
        return super()._decide_move(view)

    def _can_trap(self, view: BrainView) -> bool:
        """A trap this brain takes must also survive being wrong (see below)."""
        return super()._can_trap(view) and self._safe_trap(view)

    def _safe_trap(self, view: BrainView) -> bool:
        """Whether a MISSED trap at the believed cell still leaves a hunt.

        The trap is a one-cell gamble on the belief. The live diagnostic
        showed its worst failure: a one-cell belief error next to the
        doorway made the missed stone the seventh wall of the left half,
        stranding the cop away from the thief for the rest of the game.
        A trap is safe only if, with the stone down, every free neighbour
        of the trapped cell (each spot the thief actually occupies when the
        belief was one off) is still reachable - a miss then costs a stone,
        never the game.
        """
        trial = Board(view.board.size, set(view.board.barriers) | {view.target})
        reach = distance_field(trial, view.position)
        return all(
            _reach(reach, cell) < UNREACHABLE
            for cell in trial.free_neighbours(view.target)
        )

    def _wall_stands(self, board: Board) -> bool:
        """Whether all six wall stones are placed (the door alone open)."""
        return wall_progress(board) >= WALL_STONES

    def _door_campaign(self, view: BrainView) -> Action | None:
        """Cross to the believed thief's half and seal the door - or defer.

        Returns None whenever the position is ambiguous (the believed thief
        sits in the doorway column) or already resolved (both on one side,
        door behind us but out of reach): the region hunt owns those turns.
        """
        ours = _side(view.position[1])
        theirs = _side(view.target[1])
        if theirs == 0:
            return None  # a doorway thief is the trap rule's business
        if ours == 0:
            # standing in the doorway: step onto the thief's side of the board
            move = step_toward(view.board, view.position, view.target)
            return Action(move=move) if move != MOVE_STAY else None
        if ours == theirs:
            gap = abs(view.position[0] - DOOR[0]) + abs(view.position[1] - DOOR[1])
            if gap == 1 and view.barriers_left > 0:
                return Action(move=MOVE_STAY, barrier=DOOR)
            return None  # same half, door out of reach: hunt
        move = step_toward(view.board, view.position, DOOR)
        return Action(move=move) if move != MOVE_STAY else None
