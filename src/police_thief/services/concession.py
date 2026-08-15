"""The trapped side's concession: the loss, sealed and truthfully announced.

Split out of :mod:`turn_taking` - conceding and answering a capture claim are
both "declare the truth when caught" (rule #21), not part of composing a
regular move turn.
"""

from __future__ import annotations

from ..constants import MOVE_STAY
from ..domain.logbook import Logbook
from ..domain.sealing import turn_record
from ..domain.state_summary import turn_payloads
from ..domain.turnmsg import TurnMessage, encode_scent
from .world_view import WorldView


def concession_message(*, view: WorldView, book: Logbook) -> TurnMessage:
    """The trapped thief's final message: the loss, sealed and announced.

    A trapping barrier (or a matching capture claim) ends the game on the
    thief's side of the wire - but the cop cannot see the thief's cell, so
    without this message the winner would never learn it won (SPEC 3.1).

    The final is A REAL TURN, played as ``STAY`` at the NEXT step number - the
    reference's own send path advances there, and so does the kit's peer. This
    file used to re-announce the current step with a fresh seal, which puts two
    different commitments on one step: under commit-reveal that is equivocation,
    and a conformant opponent must refuse it. sharNamr's peer did, three sub-games
    running (2026-08-15) - our concession was rejected, they never learned they
    had won, and both sides scored zero on a capture they had earned. One commit
    per step, always.
    """
    view.step += 1
    view.my_scent.advance(view.position)
    record = book.append(
        turn_record(
            step=view.step,
            role=view.role,
            grid_size=view.board.size,
            position=view.position,
            barriers=view.board.barriers,
            move=MOVE_STAY,
            intent="truth",
            hint="",
            tokens_step=0,
            tokens_total=_tokens_so_far(book),
        )
    )
    view.note("conceding the mini-game to the police")
    return TurnMessage(
        step=view.step,
        sender=view.role,
        hint="",
        smell_grid=encode_scent(view.my_scent.snapshot()),
        commit=record["commit"],
        claim_response={"claim": list(view.position), "caught": True},
    )


def _tokens_so_far(book: Logbook) -> int:
    """The running token total, carried forward so the ledger never rewinds."""
    turns = turn_payloads(book.records)
    return int(turns[-1].get("tokens_total", 0)) if turns else 0


def answer_claim(view: WorldView) -> dict | None:
    """The thief's truthful answer to the cop's last capture claim."""
    if view.role != "thief" or view.pending_claim is None:
        return None
    claim = view.pending_claim
    view.pending_claim = None
    caught = tuple(claim) == view.position
    return {"claim": claim, "caught": caught}
