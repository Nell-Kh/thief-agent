"""Pre-game agreement check: find a handshake refusal before it costs a match.

Two peers sign the flat 14-key terms, and :func:`negotiation.validate_terms`
refuses the whole series on any value that disagrees. That refusal is correct
but expensive: it lands at kickoff, with both teams waiting and a tunnel
already open, and the message names the key only after the greeting crosses
the wire. Every value in that set comes from a file both sides can read
*beforehand*, so the same disagreement can be found in seconds the night
before instead.

The comparison covers exactly what the handshake compares - no more, so a
cosmetic difference in an unsigned field never reads as a blocker, and no
less, so nothing that refuses can hide. What this module cannot see is the
locked-model declarations (they ride beside the terms, not inside the config
file) and the role split; both are named in the report as questions for the
opponent rather than silently assumed agreed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..constants import AGENT_REPORT_ADDRESS, EMAIL_MODE_SEND
from .contract import build_contract
from .interop import terms_from_contract
from .interop_profile import InteropProfile

#: Sentinel for a term one side does not carry at all - distinct from a value
#: that is present and merely different, because the fixes differ.
ABSENT = "<absent>"


def counted_series_blockers(recipient: str, mode: str) -> list[str]:
    """Why this configuration cannot score a counted series, in plain words.

    Two settings decide whether a won series is worth anything, and both fail
    *silently*: a report addressed anywhere but the binding league address never
    arms (``report_blocks._is_armed``), and a report built in ``draft`` mode is
    never delivered at all. Either one turns six clean sub-games into nothing,
    and neither announces itself - the series simply plays, reports, and scores
    zero. Both were true in this repository at once.

    Returns:
        A list of blocker descriptions, empty when the configuration can score.
        Callers about to play a COUNTED series must refuse on a non-empty list;
        a friendly ignores it, which is exactly what makes a friendly safe.
    """
    blockers: list[str] = []
    if recipient != AGENT_REPORT_ADDRESS:
        blockers.append(
            f"recipient is {recipient!r}, not the binding league address "
            f"{AGENT_REPORT_ADDRESS!r} - the report would never arm as counted "
            f"(rule #51). Fix [email].recipient in the per-peer TOML."
        )
    if mode != EMAIL_MODE_SEND:
        blockers.append(
            f"email mode is {mode!r}, so the report is parked in Drafts and the "
            f"lecturer receives nothing - a counted game must be reported for "
            f"real (rule #32). Set [email].mode = \"send\" for a counted series."
        )
    return blockers


@dataclass(frozen=True)
class TermDifference:
    """One signed term the two peers do not agree on."""

    key: str
    ours: Any
    theirs: Any

    def __str__(self) -> str:
        """A one-line report row naming both sides' values."""
        return f"{self.key}: ours={self.ours!r} theirs={self.theirs!r}"


def terms_from_raw(
    raw: dict[str, Any], profile: InteropProfile | None = None
) -> dict[str, Any]:
    """The flat signed terms implied by a raw ``game.json`` mapping.

    Raises:
        ConfigError: if the mapping is missing a key the contract demands -
            which is itself a finding, since our peer would fail to start on
            that file at all.
    """
    contract = build_contract(raw)
    return (
        terms_from_contract(contract, profile)
        if profile is not None
        else terms_from_contract(contract)
    )


def compare_signed_terms(
    ours: dict[str, Any], theirs: dict[str, Any]
) -> list[TermDifference]:
    """Every disagreement in the signed set, in stable key order.

    A key missing from one side is reported as :data:`ABSENT` rather than
    skipped: an absent term still fails the equality the handshake runs, and
    it points at a different fix (add the field) than a wrong value.
    """
    return [
        TermDifference(key, ours.get(key, ABSENT), theirs.get(key, ABSENT))
        for key in sorted(set(ours) | set(theirs))
        if ours.get(key, ABSENT) != theirs.get(key, ABSENT)
    ]


def would_handshake(differences: list[TermDifference]) -> bool:
    """Whether the signed terms agree - the one thing this file can decide."""
    return not differences


def dialect_lines(profile: InteropProfile, setting: str) -> list[str]:
    """What we speak, and whether the arena matches the dialect's own default.

    ``setting`` is a negotiable term, and App. F says a negotiable parameter
    defaults to the printed example - ``"New York"`` - absent explicit
    agreement. The kit's fixtures ship ``"Haifa"`` instead, so the two dialects
    disagree about what an unnegotiated opponent will be holding. The shared
    ``game.json`` always states one explicitly, which IS the explicit agreement
    App. F asks for; this only warns when that statement contradicts the
    dialect we are about to declare, because then the likeliest peer refuses.
    """
    lines = [
        f"  interop dialect        : {profile.name} "
        f"(seal, scent clamp, settlement form, terms shape)",
        f"  tie-award semantics    : {profile.tie_award} "
        f"(the book is ambiguous and the kit does not settle it)",
    ]
    if setting != profile.default_setting:
        lines.append(
            f"  NOTE: setting is {setting!r} but the {profile.name} default is "
            f"{profile.default_setting!r} - a peer that has not negotiated the "
            f"arena with us will refuse on this term."
        )
    return lines


def report_lines(
    differences: list[TermDifference], our_models: dict[str, Any], expect_role: str
) -> list[str]:
    """The human-facing verdict: blockers first, then what only they can answer.

    The locked-model hashes and the role split are deliberately *questions*,
    never assumptions - a model family both peers declare differently refuses
    exactly like a term does, and it is not in either config file.
    """
    lines: list[str] = []
    if differences:
        lines.append(f"BLOCKER - the handshake would refuse on {len(differences)} term(s):")
        lines += [f"  {difference}" for difference in differences]
        lines.append("  Fix the disagreeing value(s) on ONE side before playing.")
    else:
        lines.append("OK - all 14 signed terms agree; the terms check would pass.")
    lines.append("")
    lines.append("Cannot be read from a config file - confirm with the opponent:")
    lines.append(f"  scent model we declare : {our_models.get('scent_model_sha256', '?')}")
    lines.append("    (a family BOTH sides declare with different hashes refuses)")
    lines.append(f"  our role in sub-game 1 : {expect_role} - theirs must be the complement")
    lines.append("  their exact group_id   - a wrong --opponent-group-id aborts the series")
    return lines
