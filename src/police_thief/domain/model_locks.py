"""Locked-model declarations: which differences refuse, and which only speak.

Split out of :mod:`negotiation` under the 150-line rule, along a seam that was
already there. Everything in ``negotiation`` is about the terms two peers SIGN;
this is about the physics they each declare beside those terms, and the two
fail differently - a signed-terms disagreement is always a refusal, while a
declared-model difference is a refusal, an announcement or nothing at all
depending on which family it lands in.
"""

from __future__ import annotations

from typing import Any

from .negotiation_errors import TermsRejectedError

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


def check_models(theirs: dict[str, Any], ours: dict[str, Any]) -> None:
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
