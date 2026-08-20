"""Processing the opponent's turn message: inference, events, endings.

This is the receiving half of a turn: fold the transmitted scent into the
belief, judge the hint against it, apply the public events (a declared barrier,
a capture claim, its truthful answer, a survival claim), and decide whether the
mini-game just ended. The turn token travels with the message - once this
function returns, it is our turn.
"""

from __future__ import annotations

from ..domain.emitter import locate_emitter
from ..domain.turnmsg import TurnMessage, decode_scent
from ..shared.schema import GameContract
from .enforcement import protocol_violation
from .world_view import WorldView

#: Belief multiplier for a scent-verified capture claim - a near-pin that
#: still leaves mass elsewhere, so a clever forged claim cannot blind us.
CLAIM_PIN_FACTOR = 25.0

#: Belief multiplier for the fitted emitter cell. Strong, because the fit is
#: exact against a conformant model - but not absolute, so a peer on another
#: reading of the book pulls our belief rather than breaking it.
EMITTER_PIN_FACTOR = 20.0


def receive_turn(view: WorldView, message: TurnMessage, contract: GameContract) -> None:
    """Fold one opponent turn into this peer's world view.

    The law comes first: a message that breaks the signed physics ends the
    game as a technical loss before a single belief cell is touched.
    """
    violation = protocol_violation(view, message, contract)
    if violation is not None:
        view.settle({"type": "technical_loss", "violator": message.sender,
                     "how": violation}, message.step)
        view.note(f"protocol violation by {message.sender}: {violation}")
        return
    if message.step in view.opponent_commits:
        if message.commit == view.opponent_commits[message.step]:
            return
    else:
        view.opponent_commits[message.step] = message.commit
    view.opponent_step = max(view.opponent_step, message.step)
    scent = decode_scent(message.smell_grid)
    view.belief.diffuse()
    view.belief.observe_scent(scent)
    emitter = locate_emitter(view.last_scent, scent, contract.pheromones, view.board.size)
    if emitter is not None:
        view.belief.observe_region([emitter], EMITTER_PIN_FACTOR)
    view.last_scent = scent
    appraisal = view.trust.appraise(message.hint, scent)
    if appraisal.region:
        view.belief.observe_region(appraisal.region, appraisal.factor)
    view.note(f"opponent step {message.step}: hint {appraisal.verdict}")
    _apply_barrier(view, message)
    _apply_capture_claim(view, message, contract, scent)
    _apply_claim_response(view, message, contract)
    _apply_win_claim(view, message, contract)


def _apply_barrier(view: WorldView, message: TurnMessage) -> None:
    """A publicly declared barrier becomes part of our board too."""
    if message.barrier_placed is None:
        return
    cell = (message.barrier_placed[0], message.barrier_placed[1])
    if view.board.is_free(cell):
        view.board.place_barrier(cell)
        view.opponent_barriers += 1
        view.note(f"opponent declared a barrier at {cell}")
        if cell == view.position and view.role == "thief":
            view.settle({"type": "capture", "winner": "police",
                         "how": "trapping barrier"}, message.step)


def _apply_capture_claim(
    view: WorldView, message: TurnMessage, contract: GameContract, scent: dict
) -> None:
    """The cop announced its cell; the thief must answer truthfully next turn.

    If the claim matches our cell, the game is over - the truth duty is
    absolute, and the audit would expose a lie anyway. And the claim cuts
    both ways: it names the cop's own cell, so when the cop's scent in the
    very same message burns fresh at the claimed spot, the claim is verified
    ground truth and our belief about the cop pins to it. An unverified
    claim (a possible lie) moves nothing.
    """
    if message.capture_claim is None or view.role != "thief":
        return
    view.pending_claim = list(message.capture_claim)
    claim = (int(message.capture_claim[0]), int(message.capture_claim[1]))
    view.claim_gaps.append(
        abs(claim[0] - view.position[0]) + abs(claim[1] - view.position[1])
    )
    fresh = contract.pheromones.center_intensity * (1.0 - contract.pheromones.decay)
    if scent.get(claim, 0.0) >= 0.5 * fresh:
        view.belief.observe_region([claim], CLAIM_PIN_FACTOR)
        view.note(f"cop's claim at {claim} verified by its own scent - belief pinned")
    if tuple(message.capture_claim) == view.position:
        view.settle({"type": "capture", "winner": "police",
                     "how": "capture claim"}, message.step)
        view.note("caught - answering truthfully")


def _apply_claim_response(view: WorldView, message: TurnMessage, contract: GameContract) -> None:
    """The thief's truthful answer resolves the cop's last claim."""
    if message.claim_response is None or view.role != "police":
        return
    caught = bool(message.claim_response.get("caught"))
    claim = message.claim_response.get("claim")
    if caught:
        # Remember WHAT was claimed and whether it merely echoed our own
        # broadcast cell: the audit corroborates it later rather than taking a
        # self-declared capture at its word (kit F-1/F-2).
        if isinstance(claim, list) and len(claim) == 2:
            view.final_claim = [int(claim[0]), int(claim[1])]
            view.final_claim_is_answer = tuple(view.final_claim) == tuple(view.position)
        # OUR step, not the answering turn's: the capture happened when we
        # claimed the cell, and we have not moved since. The thief settles the
        # same event at the step our claim carried, so both land on one number.
        view.settle({"type": "capture", "winner": "police",
                     "how": "capture claim"}, view.step)
    elif isinstance(claim, list) and len(claim) == 2:
        # Negative evidence the reference throws away: that cell is ruled out.
        view.belief.exclude((int(claim[0]), int(claim[1])))
        view.note(f"claim at {tuple(claim)} answered: not there")


#: Concession spellings a trapped thief may use for rule #47. ``capture`` is
#: this project's own and the reference's; ``boxed_in`` is uoh-ay26's published
#: spelling (2026-08-20) and MUST be accepted, because the failure is silent:
#: an unrecognised type fell through every branch below, so their enclosed
#: thief stopped playing while we recorded no capture at all, and the two sides
#: carried different results for that sub-game into an audit rule #35 zeroes
#: both teams over. An unknown type is now noted rather than swallowed.
CONCESSION_TYPES = ("capture", "boxed_in")


def _apply_win_claim(view: WorldView, message: TurnMessage, contract: GameContract) -> None:
    """A survival claim or a concession, each accepted only from the right side.

    Survival must clear the signed threshold; a capture concession is only
    meaningful coming from the thief - it is the losing side giving up a win
    it could otherwise silently deny, so no further proof is demanded here
    (the sealed logbook and the mutual audit carry the proof).
    """
    if message.win_claim is None:
        return
    claim_type = message.win_claim.get("type")
    if claim_type == "survival" and message.sender == "thief":
        if message.step >= contract.movement.survival_threshold:
            view.settle({"type": "survival", "winner": "thief"}, message.step)
        else:
            view.note("premature survival claim ignored")
    elif (
        claim_type in CONCESSION_TYPES
        and message.sender == "thief"
        and view.role == "police"
        and view.result is None
    ):
        view.settle({"type": "capture", "winner": "police", "how": "conceded"}, view.step)
        view.note(f"the thief conceded the capture ({claim_type})")
    else:
        # Never silent: an unrecognised or misdirected claim is a disagreement
        # about the outcome, and the audit is far too late to discover one.
        view.note(f"unhandled win_claim {claim_type!r} from {message.sender!r} ignored")
