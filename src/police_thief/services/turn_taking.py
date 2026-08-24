"""Composing this peer's turn: decide, seal, and build the wire message.

The strategy brain decides the move (never the language model), the verbal
layer composes the hint under the signed word cap, the full truth is sealed
into the logbook, and only the public parts leave the machine: the commitment
hash, the hint, the scent grid, and the events the rules require to be open.

Conceding and answering a capture claim live in :mod:`concession`.
"""

from __future__ import annotations

from ..domain.board import Cell
from ..domain.brain.base import BrainBase
from ..domain.brain.pathfind import distance
from ..domain.logbook import Logbook
from ..domain.rules import validate_barrier, validate_move
from ..domain.sealing import turn_record
from ..domain.turnmsg import TurnMessage, encode_scent
from ..infra.llm import HintProvider, HintRequest, TokenLedger
from ..infra.llm.base import STYLE_DIRECTIONAL
from ..shared.schema import GameContract
from .concession import answer_claim
from .deception import DeceptionPolicy
from .world_view import WorldView

#: Lie about our direction when the believed opponent is this close (BFS).
LIE_RANGE = 3


def choose_intent(view: WorldView) -> str:
    """Deterministic deception policy: lie when the hunt is close.

    The intent flag is sealed into the commitment either way - the choice is
    binding and auditable.
    """
    gap = distance(view.board, view.position, view.belief.argmax())
    return "lie" if 0 <= gap <= LIE_RANGE else "truth"


def take_turn(
    *,
    view: WorldView,
    contract: GameContract,
    brain: BrainBase,
    provider: HintProvider,
    ledger: TokenLedger,
    book: Logbook,
    policy: DeceptionPolicy | None = None,
) -> TurnMessage:
    """Play this peer's turn locally and return the message to send.

    Raises:
        IllegalMoveError / IllegalBarrierError: if the brain proposed an
            action the physics refuse - caught here, before anything leaves
            the machine, because each side enforces the rules on itself first.
    """
    action = brain.decide(view.brain_view(contract))
    barrier: Cell | None = action.barrier
    if barrier is not None:
        validate_barrier(
            board=view.board,
            cop=view.position,
            cell=barrier,
            move=action.move,
            used=view.barriers_used,
            quota=contract.movement.max_barriers,
        )
        view.board.place_barrier(barrier)
        view.barriers_used += 1
    view.position = validate_move(view.board, view.position, action.move)
    view.step += 1
    view.my_scent.advance(view.position)
    if policy is not None:
        _sync_claim_gaps(view, policy)
        intent, style = policy.choose()
    else:
        intent, style = choose_intent(view), STYLE_DIRECTIONAL
    direction = action.move if action.move != "STAY" else None
    tokens_before = ledger.total
    hint = provider.generate(
        HintRequest(
            role=view.role,
            intent=intent,
            true_direction=direction,
            map_area=contract.world.map_area,
            max_words=contract.world.hint_max_words,
            step=view.step,
            style=style,
        )
    )
    # Compute the public declarations ONCE, seal them, then send the identical
    # values on the wire - so the disclosed log carries the same capture claim /
    # answer / survival claim / barrier the opponent saw in cleartext, bound by
    # the commit (uoh-ay26 G010 audit, 2026-08-24: claim on the wire, absent from
    # the sealed evidence).
    survived = view.step >= contract.movement.survival_threshold
    barrier_placed = list(barrier) if barrier is not None else None
    capture_claim = list(view.position) if view.role == "police" else None
    claim_response = answer_claim(view)
    win_claim = {"type": "survival"} if view.role == "thief" and survived else None
    record = book.append(
        turn_record(
            step=view.step,
            role=view.role,
            grid_size=view.board.size,
            position=view.position,
            barriers=view.board.barriers,
            move=action.move,
            intent=intent,
            hint=hint,
            tokens_step=ledger.total - tokens_before,
            tokens_total=ledger.total,
            capture_claim=capture_claim,
            claim_response=claim_response,
            win_claim=win_claim,
            barrier_placed=barrier_placed,
        )
    )
    view.note(f"step {view.step}: played {action.move} ({intent})")
    return TurnMessage(
        step=view.step,
        sender=view.role,
        hint=hint,
        smell_grid=encode_scent(view.my_scent.snapshot()),
        commit=record["commit"],
        barrier_placed=barrier_placed,
        capture_claim=capture_claim,
        claim_response=claim_response,
        win_claim=win_claim,
    )


def _sync_claim_gaps(view: WorldView, policy: DeceptionPolicy) -> None:
    """Feed claim distances collected by the receive side into the policy."""
    while view.claim_gaps:
        policy.observe_claim_gap(view.claim_gaps.pop(0))
