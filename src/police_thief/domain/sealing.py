"""Builders of the records that get sealed - Step-0 and every game turn.

Field names follow the reference implementation's sealed records so the two
sides of a league match audit each other without translation. The Step-0
record additionally carries ``github_commit`` - the exact commit hash of the
code playing this game, a mandatory declaration (rulebook ch. 5.5): code may
change between games, but every game must record precisely what ran.

State-string encoding/decoding (the ``state`` field's own micro-format) lives
in :mod:`state_summary` - this module only builds and seals whole records.
"""

from __future__ import annotations

from typing import Any

from .board import Cell
from .crypto import seal


def step0_record(
    spec: dict[str, Any],
    model: str,
    code_version: str,
    github_commit: str,
    group_name: str,
    sub_game_number: int,
    token_budget: int,
) -> dict[str, Any]:
    """The pre-game declaration: hardware, model, code identity, budget.

    Sealed before the first move; its commitment makes the declared spec and
    the declared commit hash impossible to rewrite afterwards.
    """
    return {
        "step": 0,
        "type": "system_spec",
        "spec": spec,
        "model": model,
        "code_version": code_version,
        "github_commit": github_commit,
        "group_name": group_name,
        "sub_game_number": sub_game_number,
        "token_budget": token_budget,
    }


def turn_record(
    *,
    step: int,
    role: str,
    grid_size: int,
    position: Cell,
    barriers: frozenset[Cell],
    move: str,
    intent: str,
    hint: str,
    tokens_step: int,
    tokens_total: int,
    capture_claim: list[int] | None = None,
    claim_response: dict[str, Any] | None = None,
    win_claim: dict[str, Any] | None = None,
    barrier_placed: list[int] | None = None,
) -> dict[str, Any]:
    """One turn's full truth, sealed before the turn message is sent.

    The position and move live ONLY here - the wire carries just the hash -
    which is what makes the end-of-game audit meaningful.

    The public declarations that ALSO travel on the wire - a capture claim, the
    answer to one, a survival claim, the cell a barrier was placed on - are
    sealed here too, so the disclosed log an opponent audits carries the same
    claims it received in cleartext, now bound by the commitment and
    reveal-verifiable (rulebook 3.4.4/3.4.5, rule #21). uoh-ay26 (G010,
    2026-08-24) audited three of our captures, found the barrier-trap legal but
    the capture claim absent from the sealed evidence - it was on our wire and
    never logged. Each field is included ONLY when present, so a turn that
    declares nothing keeps its original preimage byte-for-byte, and a peer
    recomputes the commit over exactly the fields the record carries.
    """
    from .state_summary import state_summary

    record: dict[str, Any] = {
        "step": step,
        "role": role,
        "type": "turn",
        "state": state_summary(grid_size, position, barriers),
        "position": list(position),
        "move": f"move:{move}",
        "intent": intent,
        "hint": hint,
        "tokens_step": tokens_step,
        "tokens_total": tokens_total,
    }
    for key, value in (
        ("capture_claim", capture_claim),
        ("claim_response", claim_response),
        ("win_claim", win_claim),
        ("barrier_placed", barrier_placed),
    ):
        if value is not None:
            record[key] = value
    return record


def sealed(payload: dict[str, Any]) -> dict[str, Any]:
    """Seal any record built by this module (a thin, explicit alias)."""
    return seal(payload)


def revealed_move(record_payload: dict[str, Any]) -> str:
    """The bare move letter out of a revealed record's ``move:X`` field."""
    value = str(record_payload.get("move", ""))
    return value.split(":", 1)[1] if ":" in value else value


def revealed_position(record_payload: dict[str, Any]) -> Cell:
    """The ``(row, col)`` position out of a revealed record."""
    row, col = record_payload["position"]
    return (int(row), int(col))
