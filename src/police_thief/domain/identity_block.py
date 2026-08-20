"""Who this peer is, in the shape the kit's own peer reads (``identity``).

Split out of :mod:`negotiation` under the 150-line rule.
"""

from __future__ import annotations

import re
from typing import Any

from ..shared.config import ConfigManager

#: A 40-character lowercase git commit hash, and nothing else.
#:
#: uoh-ay26 (2026-08-20) require the greeting to carry a top-level
#: ``git_commit_hash`` in exactly this shape and validate it on arrival. It is
#: NOT ``step0_commit``, which is the commit-reveal commitment over the sealed
#: Step-0 record - the two are different hashes of different things and travel
#: as separate keys. The same value is sealed into Step-0 as ``github_commit``.
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


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


def git_commit_field(git_commit_hash: str) -> dict[str, str]:
    """``{"git_commit_hash": ...}`` when it is well formed, else nothing.

    Which code is playing is part of who this peer is, so it lives beside the
    rest of the identity. An uncommitted tree yields ``"uncommitted"`` upstream:
    omitted rather than sent, because this protocol tolerates silence in both
    directions and a malformed declaration is refused where an absent one is not.
    """
    value = str(git_commit_hash or "")
    return {"git_commit_hash": value} if GIT_COMMIT_RE.match(value) else {}
