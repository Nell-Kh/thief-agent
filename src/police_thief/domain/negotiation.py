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

#: The locked-model families we compare under the both-declare-or-tolerate rule.
MODEL_FAMILIES = ("scent_model_sha256", "wire_shape_sha256", "info_mode_sha256")

#: Families whose divergence forks bytes that are SEALED, hashed or audited, so
#: a stated difference must refuse: the wire shape decides what a turn message
#: even is, and the information mode decides what a legal move may be computed
#: from. Playing on through either produces a mutual audit that fails in both
#: directions, which is rule #19/#35 and a zero for both teams.
REFUSING_FAMILIES = ("wire_shape_sha256", "info_mode_sha256")

#: Families whose divergence is ADVISORY: it is real, it is worth saying out
#: loud, and it refuses nothing.
#:
#: ``scent_model_sha256`` is the only one, and the reason is a fact about our
#: own sealing rather than a courtesy. The scent grid is not in the commit
#: preimage (:func:`domain.sealing.turn_record` seals step, role, state,
#: position, move, intent, hint and tokens - not the field), it is not among
#: the fourteen signed terms, and it is not in the settlement scope. So two
#: peers on different scent models cannot fail each other's audit, cannot fork
#: the ``game_uid`` and cannot fork ``mutual_agreement.sha256``. The only cost
#: is that each side reads the other's trail through its own kernel - and we
#: measured that cost against NajAmjad's ``subtractive_chebyshev_v1`` at zero:
#: 11 of 11 locations, once :mod:`domain.emitter` stopped assuming our clamp.
#:
#: Refusing here was strictly more than the harm. It would also have been a
#: forfeit we chose: najamjad declare their model and do not read ours, so the
#: refusal was ours alone and the game simply would not have happened.
ADVISORY_FAMILIES = ("scent_model_sha256",)


class TermsRejectedError(RuntimeError):
    """Raised when the opponent's greeting must be refused."""


def build_terms(
    config: ConfigManager,
    *,
    peer_id: str,
    games_played: int,
    sub_game: int,
    step0_commit: str,
) -> dict[str, Any]:
    """This peer's negotiation greeting: signed terms plus declarations."""
    terms = terms_from_contract(config.contract)
    nonce = new_nonce()
    greeting: dict[str, Any] = {
        "terms": terms,
        "nonce": nonce,
        "signature": sign_terms(terms, nonce),
        "group_id": peer_id,
        "counted_games_played": int(games_played),
        "step0_commit": step0_commit,
    }
    greeting.update(negotiate_extras(config.role, sub_game))
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
    _check_models(theirs, our_extras)
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
    ):
        their_value, our_value = theirs.get(field), ours.get(field)
        if isinstance(their_value, str) and their_value and their_value != our_value:
            raise TermsRejectedError(
                f"{label} mismatch: we speak {our_value!r}, they declare "
                f"{their_value!r}. Agree one before playing - every step of the "
                f"audit depends on it (see [interop] in the per-peer TOML)."
            )


def _check_models(theirs: dict[str, Any], ours: dict[str, Any]) -> None:
    """Refuse only when BOTH peers declare a SEALING family and the hashes differ.

    An advisory family (see :data:`ADVISORY_FAMILIES`) is reported by
    :func:`model_advisories` and refuses nothing.
    """
    for family in REFUSING_FAMILIES:
        their_hash, our_hash = theirs.get(family), ours.get(family)
        if their_hash is not None and our_hash is not None and their_hash != our_hash:
            raise TermsRejectedError(f"{family} mismatch: locked models differ")


def model_advisories(theirs: dict[str, Any], ours: dict[str, Any]) -> list[str]:
    """Locked-model differences worth announcing but not worth refusing.

    Returned rather than logged so the caller decides where it belongs: a
    difference nobody is ever told about is how two teams end a series each
    believing the other agreed with them.
    """
    notes = []
    for family in ADVISORY_FAMILIES:
        their_hash, our_hash = theirs.get(family), ours.get(family)
        if their_hash is not None and our_hash is not None and their_hash != our_hash:
            notes.append(
                f"{family}: they declare {their_hash[:12]}..., we declare "
                f"{our_hash[:12]}... - the field is unsealed and unhashed, so this "
                f"refuses nothing; each side reads the other's trail through its "
                f"own kernel"
            )
    return notes


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
