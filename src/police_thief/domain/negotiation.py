"""Pre-game negotiation in the league's interoperable handshake shape.

The signed object is the flat 14-key terms set (the reference's own
extraction, pinned by the class interop kit); everything else - role,
sub-game index, locked-model hashes, the games-count declaration, the Step-0
commitment - rides BESIDE the terms, never inside them, because adding a key
to the signed set breaks the signature. Refusal follows the kit's promoted
truth tables: a value that disagrees refuses; an omission never does, in
either direction - the unmodified reference peer declares nothing, and
refusing silence is a self-inflicted forfeit.
"""

from __future__ import annotations

from typing import Any

from ..shared.config import ConfigManager
from ..shared.interop import negotiate_extras, sign_terms, terms_from_contract
from .crypto import new_nonce
from .identity_block import git_commit_field, identity_block
from .model_locks import check_models, model_advisories
from .negotiation_errors import TermsRejectedError


def build_terms(
    config: ConfigManager,
    *,
    peer_id: str,
    games_played: int,
    sub_game: int,
    step0_commit: str,
    git_commit_hash: str = "",
) -> dict[str, Any]:
    """This peer's negotiation greeting: signed terms plus declarations."""
    # Every key below rides BESIDE `terms`, never inside it, so the signature
    # each conformant peer verifies is byte-for-byte unchanged. That includes
    # `git_commit_hash` (the 40-hex commit of the code playing, which uoh-ay26
    # read at the top level) and the dialect block, which now carries the
    # CONFIGURED profile rather than the module default - declaring one scope
    # and validating against another is a peer that refuses its own partner.
    terms = terms_from_contract(config.contract)
    nonce = new_nonce()
    greeting: dict[str, Any] = {
        "terms": terms,
        "nonce": nonce,
        "signature": sign_terms(terms, nonce),
        "group_id": peer_id,
        "counted_games_played": int(games_played),
        "step0_commit": step0_commit,
        "identity": identity_block(config, peer_id),
        **git_commit_field(git_commit_hash),
    }
    greeting.update(negotiate_extras(config.role, sub_game, config.interop))
    return greeting


def validate_terms(
    theirs: dict[str, Any],
    *,
    our_terms: dict[str, Any],
    our_extras: dict[str, Any],
    expect_role: str,
) -> dict[str, Any]:
    """Accept or refuse an opponent's greeting.

    Refusals, each naming what disagreed: terms not value-equal to ours, a
    signature that does not verify over the received terms, a locked-model
    family BOTH sides declare with different hashes, a pairing declaration
    naming the wrong sub-game or our own role. Everything absent is silence,
    and silence never refuses.

    Raises:
        TermsRejectedError: naming exactly what disagreed.
    """
    if not isinstance(theirs, dict) or not isinstance(theirs.get("terms"), dict):
        raise TermsRejectedError("greeting must carry a terms object")
    if theirs["terms"] != our_terms:
        differing = [
            key
            for key in set(our_terms) | set(theirs["terms"])
            if our_terms.get(key) != theirs["terms"].get(key)
        ]
        raise TermsRejectedError(f"terms mismatch on {sorted(differing)}")
    nonce, signature = str(theirs.get("nonce", "")), str(theirs.get("signature", ""))
    if not nonce or sign_terms(theirs["terms"], nonce) != signature:
        raise TermsRejectedError("terms signature does not verify")
    check_models(theirs, our_extras)
    _check_dialect(theirs, our_extras)
    _check_pairing(theirs, our_extras, expect_role)
    return _lift_identity(theirs)


def _lift_identity(theirs: dict[str, Any]) -> dict[str, Any]:
    """Accept the group id at the top level OR under ``identity`` (the kit's rule).

    The kit's own peer reads ``raw.get("group_id") or raw["identity"]["group_id"]``
    and sends BOTH, so our sparring never met a greeting with only the nested
    form - the first real opponent (moamteam, 2026-08-15) sent only that, and
    we refused a valid partner as "group_id None" at kickoff. Silence on the
    top-level key is not a disagreement; the nested field is the same fact.
    """
    if theirs.get("group_id"):
        return theirs
    identity = theirs.get("identity")
    nested = identity.get("group_id") if isinstance(identity, dict) else None
    return {**theirs, "group_id": nested} if nested else theirs


def _check_dialect(theirs: dict[str, Any], ours: dict[str, Any]) -> None:
    """Refuse a stated disagreement about which reading of the book we speak.

    Deliberately stricter than :func:`_check_models`, which tolerates silence.
    A locked-model family that one side omits is a peer that simply never
    published a hash; a dialect difference is four byte-level forks - the commit
    seal, the scent clamp, the settlement form, the terms shape - each of which
    fails the mutual audit in BOTH directions and zeroes both teams under rules
    #19/#35. Refusing a stated difference converts that into a question with an
    answer, so it is still tolerant of silence (an unmodified reference peer
    declares nothing) but never of contradiction.
    """
    for field, label in (
        ("interop_profile", "interop dialect"),
        ("tie_award", "tie-award semantics"),
        ("turn_order", "turn order within a full turn"),
        ("settlement_scope", "settlement preimage scope"),
    ):
        their_value, our_value = theirs.get(field), ours.get(field)
        if isinstance(their_value, str) and their_value and their_value != our_value:
            raise TermsRejectedError(
                f"{label} mismatch: we speak {our_value!r}, they declare "
                f"{their_value!r}. Agree one before playing - every step of the "
                f"audit depends on it (see [interop] in the per-peer TOML)."
            )


def _check_pairing(theirs: dict[str, Any], ours: dict[str, Any], expect_role: str) -> None:
    """The kit's pairing truth table: wrong index or same side refuses.

    A value that cannot be compared is treated as silence - refusing over a
    peer's type or spelling choice turns a cosmetic difference into a loss.
    """
    their_game = theirs.get("sub_game_number")
    if isinstance(their_game, int) and their_game != ours.get("sub_game_number"):
        raise TermsRejectedError(
            f"sub-game mismatch: we are playing {ours.get('sub_game_number')}, "
            f"they declare {their_game}"
        )
    their_role = theirs.get("role")
    if isinstance(their_role, str) and their_role not in ("", expect_role):
        raise TermsRejectedError(f"role clash: both sides claim {their_role!r}")


#: Re-exported so every existing importer of this module keeps working: the
#: split is an internal seam, not a change to the handshake's public surface.
__all__ = [
    "TermsRejectedError",
    "build_terms",
    "model_advisories",
    "validate_terms",
]
