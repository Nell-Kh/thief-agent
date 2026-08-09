"""The interop dialect: which of two lawful readings of the book we speak.

The rulebook's front matter says its code samples illustrate rather than bind,
and its academic-freedom clause lets a team resolve a contradiction either way
provided the choice is declared. Four places in this project took the second
road, following the class interop kit (``copthief-league-protocol``) and the
reference implementation it pins rather than the book's printed formulae:

===================  ==============================  ==========================
fork                 kit                             book
===================  ==============================  ==========================
commit seal          ``sha256(canonical(p)|nonce)``  nonce inside the JSON
scent update         clamped to ``emit_intensity``   ``max(0, ...)`` only
settlement form      spaced separators               compact separators
signed terms         14 keys, ``setting="Haifa"``    13 keys, ``"New York"``
===================  ==============================  ==========================

Neither column is wrong. What *is* wrong is picking one silently: two lawful
implementations that disagree here each conclude the other forged its log, and
rule #19/#35 then score BOTH teams zero. So the choice lives in one named place,
travels in the handshake (``negotiate_extras``), and refuses on mismatch - a
disagreement becomes a message you answer before kickoff instead of a mutual
zero you discover at the audit.

The tie award is deliberately NOT in the table above. The kit does not settle it
either: ``report_consensus`` pins the settlement *serialization* and says
nothing about aggregate semantics, so add-vs-substitute forks the settlement
hash under either dialect. It is therefore a separate declared axis, defaulting
to the reading this project has always used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

#: Follow the class interop kit and the reference peer it pins. The default:
#: our vendored vectors pass byte-for-byte under it and it is what the teams
#: currently offering games speak.
PROFILE_KIT: Final[str] = "kit"

#: Follow the rulebook's printed formulae literally (ch. 4.3, ch. 5.3.1).
PROFILE_BOOK: Final[str] = "book"

PROFILES: Final[tuple[str, ...]] = (PROFILE_KIT, PROFILE_BOOK)

#: Series tie: add the App. F award on top of the accumulated sub-game totals.
TIE_AWARD_ADD: Final[str] = "add"

#: Series tie: the award replaces the accumulated totals outright.
TIE_AWARD_SUBSTITUTE: Final[str] = "substitute"

TIE_AWARDS: Final[tuple[str, ...]] = (TIE_AWARD_ADD, TIE_AWARD_SUBSTITUTE)

#: Who acts first within a full turn. The book genuinely does not fix one, so
#: this is a free choice - but it is not a LOCAL one. Two peers on opposite
#: orders shake hands, play, and then disagree about the board, which is a
#: hash-clean log with a divergent history. Declared so the disagreement
#: surfaces at the handshake; ``domain.engine`` applies it.
TURN_ORDER: Final[str] = "cop_first"


class InteropProfileError(ValueError):
    """Raised when a configured dialect or tie-award value is not recognised."""


@dataclass(frozen=True)
class InteropProfile:
    """One resolved dialect - every fork answered, nothing left implicit."""

    name: str
    tie_award: str

    @property
    def nonce_inside_payload(self) -> bool:
        """Whether the commit hashes the nonce inside the JSON (book ch. 5.3.1).

        Kit/reference appends it: ``sha256(canonical(payload) + "|" + nonce)``.
        The book's printed sample puts it in the object that gets serialized.
        Every step of every log depends on this one bit agreeing.
        """
        return self.name == PROFILE_BOOK

    @property
    def clamp_scent_to_emit(self) -> bool:
        """Whether scent is clamped above at ``emit_intensity``.

        The book prints ``tau' = max(0, (1-rho)*tau + delta)`` - one clamp, at
        zero. The kit's registered ``multiplicative_book_v1`` also clamps above,
        which bites immediately (``0.9*0.9 + 0.9 = 1.71 -> 0.9``) and shows up
        in the ``smell_grid`` that crosses the wire every turn.
        """
        return self.name == PROFILE_KIT

    @property
    def settlement_spaced(self) -> bool:
        """Whether the settlement hash uses spaced JSON separators.

        The kit's ``report_consensus`` vector pins the spaced form as the
        release's second canonical form; everything under a commit hash is
        compact. A team signing the wrong one fails settlement at the exact
        moment both teams must agree.
        """
        return self.name == PROFILE_KIT

    @property
    def terms_carry_min_center_intensity(self) -> bool:
        """Whether ``min_center_intensity`` is part of the signed terms.

        It is not an Appendix B field. The kit adds it and pins it in the
        ``terms_signature`` vector; a book-conformant peer signs 13 keys, and
        ``validate_terms`` compares the whole object, so the count must match.
        """
        return self.name == PROFILE_KIT

    @property
    def default_setting(self) -> str:
        """The arena a peer assumes when the pair has not negotiated one.

        App. F: a negotiable parameter defaults to the printed example absent
        explicit agreement, i.e. ``"New York"``. The kit's own fixtures ship
        ``"Haifa"``, so the two dialects genuinely disagree about the default.
        """
        return "Haifa" if self.name == PROFILE_KIT else "New York"

    @property
    def tie_award_adds(self) -> bool:
        """Whether a series tie ADDS the award to the totals rather than replacing them."""
        return self.tie_award == TIE_AWARD_ADD

    def declaration(self) -> dict[str, str]:
        """What we announce at the handshake so a mismatch refuses.

        Rides beside the signed terms, never inside them: the signed set is flat
        and closed, and adding a key there would break the signature for every
        peer that computes it correctly.
        """
        return {
            "interop_profile": self.name,
            "tie_award": self.tie_award,
            "turn_order": TURN_ORDER,
        }


def resolve(name: str | None = None, tie_award: str | None = None) -> InteropProfile:
    """Build a profile from configured strings, refusing anything unrecognised.

    Args:
        name: ``"kit"`` or ``"book"``; ``None``/empty selects the kit default.
        tie_award: ``"add"`` or ``"substitute"``; ``None``/empty selects ``add``.

    Raises:
        InteropProfileError: on an unrecognised value. A typo must not quietly
            fall back to a default - that reintroduces the silent divergence
            this module exists to prevent.
    """
    resolved_name = (name or PROFILE_KIT).strip().lower()
    resolved_tie = (tie_award or TIE_AWARD_ADD).strip().lower()
    if resolved_name not in PROFILES:
        raise InteropProfileError(
            f"unknown [interop].profile {name!r}; expected one of {PROFILES}"
        )
    if resolved_tie not in TIE_AWARDS:
        raise InteropProfileError(
            f"unknown [interop].tie_award {tie_award!r}; expected one of {TIE_AWARDS}"
        )
    return InteropProfile(name=resolved_name, tie_award=resolved_tie)


#: The dialect assumed by any caller that has no configuration in hand - the
#: pure functions in :mod:`domain.crypto` and friends keep working unchanged.
DEFAULT = resolve()
