"""Two-ply adversarial search over the cop's actions and the thief's replies.

Round 5 of the arms race, and the first brain in the tree that looks past its
own move. Every cop before it scored the position it would *create* - the
region cop greedily, the wall and seal cops by plan - and the elite evader
answers all of them the same way: it prices the cop's best reply before it
moves (one ply of pessimism), so a cop that plans zero plies ahead is always
seen coming. Measured under perfect information from the sealed 3x7 chamber
the seal cop reaches, the region hunt failed to box the evader in fifteen
turns; this search boxes it in five.

The value of a position is taken from the cop's side and MINIMISED: the thief
answers each cop action with the reply that maximises it (the classic minimax
shape, alpha-beta pruned). ``depth`` counts cop decisions, so ``depth=2`` is
cop - thief - cop - thief - evaluate. On the open board that is too wide to
be worth its cost and too shallow to see a wall pay off, which is why
:mod:`box` reaches for it only once the chamber is closed and the branching is
small.
"""

from __future__ import annotations

from ...constants import MOVE_STAY
from ..board import Board, Cell
from ..rules import barrier_placements, destination, is_trapped, legal_moves, legal_steps
from .pathfind import distance_field
from .region_geometry import UNREACHABLE, _reach, region_size

#: The value of a captured thief - beats every non-terminal position.
CAPTURE = -(10**6)

#: An action: the move, plus the stone it drops (``None`` for a plain step).
CopAction = tuple[str, Cell | None]

#: Region weighs most, then the thief's exits, then how far it is; a cop cut
#: off from the hunt entirely is priced as far away as the board allows.
W_REGION, W_EXITS, CUT_OFF_DISTANCE = 100, 10, 50


def captured(board: Board, cop: Cell, thief: Cell) -> bool:
    """Whether the position is already a capture (overlap, stone, or boxed in)."""
    return cop == thief or board.is_barrier(thief) or is_trapped(board, thief)


def evaluate(board: Board, cop: Cell, thief: Cell) -> int:
    """The cop's estimate of a quiet position - lower is better for the cop."""
    if captured(board, cop, thief):
        return CAPTURE
    distance = _reach(distance_field(board, cop), thief)
    if distance >= UNREACHABLE:
        distance = CUT_OFF_DISTANCE
    return (
        W_REGION * region_size(board, cop, thief)
        + W_EXITS * len(board.free_neighbours(thief))
        + distance
    )


def cop_actions(board: Board, cop: Cell, stones_left: int) -> list[CopAction]:
    """Every displacing step, then every stone the cop may drop while staying."""
    actions: list[CopAction] = [(move, None) for move in legal_steps(board, cop)]
    if stones_left > 0:
        actions.extend(
            (MOVE_STAY, cell) for cell in barrier_placements(board, cop) if cell != cop
        )
    return actions


def apply_cop(board: Board, cop: Cell, action: CopAction) -> tuple[Board, Cell]:
    """The board and cop cell after ``action``; a stone yields a fresh board."""
    move, stone = action
    after = Board(board.size, set(board.barriers) | {stone}) if stone else board
    return after, destination(cop, move)


def thief_replies(board: Board, cop: Cell, thief: Cell) -> list[Cell]:
    """Where the thief may go next - never onto the cop, which is a capture."""
    cells = [destination(thief, move) for move in legal_moves(board, thief)]
    return [cell for cell in cells if cell != cop]


def search(
    board: Board, cop: Cell, thief: Cell, stones_left: int, depth: int,
    alpha: int = -(10**9), beta: int = 10**9,
) -> int:
    """Minimax value with ``depth`` cop decisions still to make."""
    if captured(board, cop, thief):
        return CAPTURE
    if depth == 0:
        return evaluate(board, cop, thief)
    best = 10**9
    for action in cop_actions(board, cop, stones_left):
        after, cop_next = apply_cop(board, cop, action)
        if captured(after, cop_next, thief):
            return CAPTURE
        left = stones_left - (1 if action[1] else 0)
        worst = -(10**9)
        replies = thief_replies(after, cop_next, thief)
        if not replies:
            worst = CAPTURE
        for thief_next in replies:
            worst = max(worst, search(after, cop_next, thief_next, left, depth - 1, alpha, beta))
            if worst >= beta:
                break
        best = min(best, worst)
        beta = min(beta, best)
        if best <= alpha:
            break
    return best


def best_action(
    board: Board, cop: Cell, thief: Cell, stones_left: int, depth: int
) -> CopAction:
    """The cop action whose worst-case value is lowest; a step beats an equal stone."""
    ranked: list[tuple[tuple[int, int, str], CopAction]] = []
    for action in cop_actions(board, cop, stones_left):
        after, cop_next = apply_cop(board, cop, action)
        if captured(after, cop_next, thief):
            return action
        left = stones_left - (1 if action[1] else 0)
        replies = thief_replies(after, cop_next, thief)
        worst = CAPTURE if not replies else max(
            search(after, cop_next, thief_next, left, depth - 1) for thief_next in replies
        )
        ranked.append(((worst, 1 if action[1] else 0, str(action)), action))
    return min(ranked)[1] if ranked else (MOVE_STAY, None)
