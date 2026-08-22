"""Receive-side law: each peer enforces the physics on the other.

There is no referee in this game (rulebook ch. 9): the only police force is
the opponent. Every incoming turn message is therefore checked against the
signed contract BEFORE any inference runs - step continuity, scent physics,
barrier legality and quota, claim shapes, role permissions. A violation ends
the mini-game immediately as a technical loss (the game is void; the
violator's report will not survive the mutual audit either), which is
strictly better than the alternative: crashing on hostile input and eating
the technical loss ourselves via the watchdog.
"""

from __future__ import annotations

import math

from ..constants import ROLE_POLICE, ROLE_THIEF
from ..domain.turnmsg import TurnMessage
from ..shared.schema import GameContract
from .world_view import WorldView


def protocol_violation(
    view: WorldView, message: TurnMessage, contract: GameContract
) -> str | None:
    """The first rule this message breaks, or None if it is lawful."""
    checks = (
        _check_step,
        _check_scent,
        _check_barrier,
        _check_claims,
    )
    for check in checks:
        reason = check(view, message, contract)
        if reason is not None:
            return reason
    return None


def _check_step(view: WorldView, message: TurnMessage, contract: GameContract) -> str | None:
    """Steps must advance by exactly one; only a win/concession may repeat.

    Monotonicity is what makes ``message.step`` trustworthy everywhere else -
    without it, a thief could open with ``step=35`` and a survival claim.
    """
    expected = view.opponent_step + 1
    if message.step == expected:
        return None

    if message.step in view.opponent_commits and message.commit == view.opponent_commits[message.step]:
        return None

    is_zero_step_final = (
        message.claim_response is not None
        and message.claim_response.get("caught") is True
    )
    is_legacy_final = (
        message.win_claim is not None
        and message.win_claim.get("type") == "capture"
    )

    if message.step == view.opponent_step and (is_zero_step_final or is_legacy_final):
        return None  # a concession re-announces the current step

    return f"step {message.step} out of order (expected {expected})"


def _check_scent(view: WorldView, message: TurnMessage, contract: GameContract) -> str | None:
    """Scent values must be finite, non-negative, physically possible, on-board.

    The anti-forgery ceiling is the UNCLAMPED accumulation fixed point,
    ``emit / decay`` (``0.9 / 0.1 = 9.0``), NOT the emission clamp ``emit``
    (0.9). The scent clamp is a lawful dialect fork (``interop_profile``): a kit
    peer clamps a re-emitted cell at ``emit``, a book peer lets it accumulate
    toward ``emit/decay``. Both are legal, ``scent_model_sha256`` is advisory,
    and :mod:`domain.emitter` already reads a foreign unclamped field through
    our own kernel. This gate had contradicted all of that - capping at ``emit``
    turned a lawful book-model opponent's field into a "forged field" technical
    loss (uoh-ay26, G010 g01: ``scent value 1.14 breaks the locked model``).
    Capping at the physical maximum still rejects what is genuinely impossible -
    NaN, negative, off-board, or a value no lawful model can reach - while
    accepting every field either dialect can legally produce.
    """
    size = contract.board.grid_size
    decay = contract.pheromones.decay
    ceiling = (contract.pheromones.center_intensity / decay) if decay > 0.0 \
        else contract.pheromones.center_intensity
    cap = ceiling + 1e-9
    for key, value in message.smell_grid.items():
        number = float(value)
        if not math.isfinite(number) or number < 0.0 or number > cap:
            return f"scent value {value!r} at {key} breaks the locked model"
        row_text, col_text = str(key).split(",")
        row, col = int(row_text), int(col_text)
        if not (0 <= row < size and 0 <= col < size):
            return f"scent cell {key} is off the {size}x{size} board"
    return None


def _check_barrier(view: WorldView, message: TurnMessage, contract: GameContract) -> str | None:
    """Barriers: police only, on the board, within the signed quota."""
    if message.barrier_placed is None:
        return None
    if message.sender != ROLE_POLICE:
        return "only the police may place barriers"
    row, col = message.barrier_placed
    size = contract.board.grid_size
    if not (0 <= row < size and 0 <= col < size):
        return f"barrier at {(row, col)} is off the board"
    cell = (row, col)
    is_new = view.board.is_free(cell)
    if is_new and view.opponent_barriers + 1 > contract.movement.max_barriers:
        return (
            f"barrier quota exceeded ({view.opponent_barriers + 1} placed, "
            f"{contract.movement.max_barriers} allowed)"
        )
    return None


def _check_claims(view: WorldView, message: TurnMessage, contract: GameContract) -> str | None:
    """Capture claims are police-only; claim answers are thief-only; shapes hold."""
    size = contract.board.grid_size
    if message.capture_claim is not None:
        if message.sender != ROLE_POLICE:
            return "only the police may make capture claims"
        row, col = message.capture_claim
        if not (0 <= row < size and 0 <= col < size):
            return f"capture claim {(row, col)} is off the board"
    if message.claim_response is not None:
        if message.sender != ROLE_THIEF:
            return "only the thief may answer capture claims"
        if not isinstance(message.claim_response, dict):
            return "claim response must be an object"
    if message.win_claim is not None and not isinstance(message.win_claim, dict):
        return "win claim must be an object"
    return None
