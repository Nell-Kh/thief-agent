"""Standalone joining blocks used when assembling a lifecycle report.

``links_block`` names the four artifacts of one game (rulebook ch. 9.3.3);
``group_block`` is one team's signed declaration entry; ``league_block``
records whether this report is armed as "counted"; ``now_iso`` and
``opponent_commit`` fill two per-row fields the driver used to leave empty.
All of them are built by the caller and threaded into the payload builders
in :mod:`reports`.
"""

from __future__ import annotations

import datetime
from typing import Any

from ...constants import AGENT_REPORT_ADDRESS
from ...shared.config_io import sha256_of
from .naming import declaration_file_name, result_file_name


def _is_armed(counted: bool, recipient: str) -> bool:
    """A counted claim only sticks when addressed to the binding league recipient.

    Rule #51 sends every report to one address; rules #37/#38 forbid ever
    lying about counted status. Gating arming on the recipient makes a
    misconfigured ``[email] recipient`` fail safe: whatever the caller
    believed, a report addressed anywhere else is never counted.
    """
    return counted and recipient == AGENT_REPORT_ADDRESS


def league_block(counted: bool, recipient: str) -> dict[str, Any]:
    """Armed only for a counted series actually addressed to the binding recipient."""
    armed = _is_armed(counted, recipient)
    if counted and not armed:
        reason = "counted-blocked: recipient is not the binding league address"
    else:
        reason = "counted" if armed else "friendly"
    return {"counted": armed, "reason": reason}


def links_block(game_id: str, github: dict[str, Any]) -> dict[str, Any]:
    """The four artifact names plus both teams' repositories - one joining block."""
    return {
        "declaration": declaration_file_name(game_id),
        "config": f"config_{game_id}_g<NN>.json",
        "log": f"log_{game_id}_g<NN>.json",
        "result": result_file_name(game_id),
        "github": github,
    }


def group_block(**fields: Any) -> dict[str, Any]:
    """One team's declaration block, hashed hash-then-insert over its canonical form.

    The ``signature`` key keeps its name because that is the wire format the
    league reads, but it is a **checksum, not a signature**: an unkeyed SHA-256
    over data that travels in the same document, so any party can recompute it.
    It detects a block corrupted or edited in transit; it cannot prove who wrote
    one. Book ch. 5.5 asks for signing under a pre-supplied key, which this
    project does not implement - stated plainly in README section 8 rather than
    left to be inferred from the field name.

    Expected fields: group_id, group_name, members, repos, mcp_servers, llm_model,
    hardware_spec, github_commit, counted_games_played (the PRIOR count), code_version.
    """
    block = dict(fields)
    block["hardware_spec_sha256"] = sha256_of(block["hardware_spec"])
    block["signature"] = "sha256:" + sha256_of(block)
    return block


def now_iso() -> str:
    """This instant, UTC, seconds precision - the report's timestamp form.

    Every row we ever filed carried ``started_at``/``ended_at`` as the empty
    string, because the driver had nothing to put there and nobody had looked.
    An opponent's rows carry real instants (sharNamr, 2026-08-17), and a row
    that cannot say when it was played is a row that cannot be reconciled
    against theirs by anything but position.
    """
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


#: The spellings of the Step-0 record seen on the wire. Ours is
#: ``type: "system_spec"``; MOAAMOHA (2026-08-18) seal ``record_type:
#: "step_zero"`` and accept both spellings on THEIR side - which is how the
#: asymmetry surfaced: a tolerant peer reads us correctly while we file
#: ``"unknown"`` for them, and only one of the two reports has the hole.
STEP_ZERO_MARKERS: tuple[tuple[str, str], ...] = (
    ("type", "system_spec"),
    ("record_type", "step_zero"),
)


def _step_zero_commit(record: dict[str, Any]) -> str:
    """``record``'s ``github_commit`` if it declares itself Step-0, else ``""``.

    Both scopes are searched because the marker's PLACEMENT varies as well as
    its spelling: some peers put it on the sealed payload, some on the record
    that wraps it. ``payload`` wins on a collision, since that is the half the
    commit-reveal digest actually covers - a value read from the wrapper is
    unproven, and we would rather report the proven one.
    """
    payload = record.get("payload") or {}
    fields = {**record, **payload}
    if not any(fields.get(key) == value for key, value in STEP_ZERO_MARKERS):
        return ""
    return str(fields.get("github_commit") or "")


def opponent_commit(disclosure: dict[str, Any] | None) -> str:
    """The opponent's git SHA, read out of the Step-0 record it just revealed.

    Rule #53 asks both sides to record the commit each sub-game was played on,
    and we filed ``"unknown"`` for the opponent in every row ever written -
    while the answer sat inside the disclosure we had just audited. Every
    conformant peer seals a Step-0 record carrying its own ``github_commit``,
    and the mutual audit hands us that record with its nonce, so the value is
    not merely known but *proven*.

    Derived rather than asked for, deliberately: sharNamr play their two roles
    from two repositories and had changed both between sending us their interop
    sheet and playing the match, so a hardcoded answer would have filed a
    confidently wrong SHA in place of an honestly absent one.
    """
    for record in (disclosure or {}).get("records", []):
        commit = _step_zero_commit(record)
        if commit:
            return commit
    return "unknown"
