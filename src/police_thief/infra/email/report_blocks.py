"""Standalone joining blocks used when assembling a lifecycle report.

``links_block`` names the four artifacts of one game (rulebook ch. 9.3.3);
``group_block`` is one team's signed declaration entry; ``league_block``
records whether this report is armed as "counted". All three are built by
the caller and threaded into the payload builders in :mod:`reports`.
"""

from __future__ import annotations

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
