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


def commit_aliases(git_commit_hash: str) -> dict[str, str]:
    """The playing commit under BOTH spellings a conformant verifier may read.

    A well-formed 40-hex commit is returned as ``git_commit_hash`` AND
    ``github_commit``; a malformed value (an uncommitted tree yields
    ``"uncommitted"``) returns nothing, since this protocol tolerates silence
    but refuses a malformed declaration.

    Two spellings because two are in the wild: this project seals
    ``github_commit`` into Step-0, while uoh-ay26's mutual-signoff gate reads
    ``git_commit_hash``. Sending both, rather than guessing which the peer
    checks, is the difference between a signed series and a g01 that captured
    cleanly yet never mutually signed (G010, 2026-08-22).
    """
    value = str(git_commit_hash or "")
    if not GIT_COMMIT_RE.match(value):
        return {}
    return {"git_commit_hash": value, "github_commit": value}


def git_commit_field(git_commit_hash: str) -> dict[str, str]:
    """Back-compat alias: the commit spellings for the greeting top level."""
    return commit_aliases(git_commit_hash)


def identity_block(
    config: ConfigManager, peer_id: str, git_commit_hash: str = ""
) -> dict[str, Any]:
    """Our group id, name, members, repositories and playing commit.

    Rulebook 9.3.3 makes BOTH teams' repository links a mandatory report
    field, but a report may only carry what the opponent actually declared -
    and we declared nothing. yamanagh (2026-08-19) correctly refused to paste
    ours in from a chat message: a graded artifact must record what crossed
    the wire, not what someone was told. The gap was ours, not theirs.

    The playing commit rides here too (both spellings), not only at the greeting
    top level, because a peer that reads it FROM the identity object saw an
    empty field otherwise (uoh-ay26 G010 g01). All of it rides beside the signed
    terms, never inside them, so the signature is unchanged.
    """
    game = config.private("game")
    return {
        "group_id": peer_id,
        "group_name": str(game.get("group_name", "")),
        "members": list(game.get("members", [])),
        "repos": dict(game.get("repos", {})),
        **commit_aliases(git_commit_hash),
    }
