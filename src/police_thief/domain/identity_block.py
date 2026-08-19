"""Who this peer is, in the shape the kit's own peer reads (``identity``).

Split out of :mod:`negotiation` under the 150-line rule.
"""

from __future__ import annotations

from typing import Any

from ..shared.config import ConfigManager


def identity_block(config: ConfigManager, peer_id: str) -> dict[str, Any]:
    """Our group id, name, members and repositories, for the greeting.

    Rulebook 9.3.3 makes BOTH teams' repository links a mandatory report
    field, but a report may only carry what the opponent actually declared -
    and we declared nothing. yamanagh (2026-08-19) correctly refused to paste
    ours in from a chat message: a graded artifact must record what crossed
    the wire, not what someone was told. The gap was ours, not theirs.

    Rides beside the signed terms, never inside them, so the signature is
    unchanged for every peer that already verifies it.
    """
    game = config.private("game")
    return {
        "group_id": peer_id,
        "group_name": str(game.get("group_name", "")),
        "members": list(game.get("members", [])),
        "repos": dict(game.get("repos", {})),
    }
