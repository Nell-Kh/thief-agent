"""Settlement consensus: the one hash two rival teams must compute byte-for-byte.

The league's audit joins both teams' result reports on ``mutual_agreement.sha256``
(kit SPEC section 6): equal hashes settle the series, different hashes zero both
teams under rule 35. Two conventions make the join possible and both live here.

First, the *serialization* is the release's second canonical form - ``json.dumps``
with ``sort_keys=True, ensure_ascii=False`` and the DEFAULT spaced separators,
unlike the compact form under every commit. Second, the *scope* is trimmed to
exactly what two honest teams must agree on: the game id, the derived aggregate,
and the per-sub-game rows stripped of every per-side field (timestamps, tokens,
log names) a conformant opponent may legitimately report differently.

The consensus signature over the whole emailed report follows the same spaced
form and is computed sign-then-insert: the Hebrew signature key is excluded
from its own preimage.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ...constants import CANONICAL_SEPARATORS
from ...shared.interop_profile import DEFAULT, InteropProfile

#: The reference report_writer's signature field - the key itself is part of the wire format.
SIGNATURE_KEY = "חתימת_קונסנזוס_משותפת"  # noqa: E501

#: The row fields inside the consensus preimage - pair-observable, never per-side.
SCOPE_ROW_KEYS = ("sub_game_number", "roles", "result", "winner_group", "tie", "score")


#: ``json.dumps`` default spacing - the kit's settlement form.
SPACED_SEPARATORS = (", ", ": ")


def serialize_spaced(payload: Any, profile: InteropProfile = DEFAULT) -> str:
    """The settlement serialization: sorted keys, raw Hebrew, dialect spacing.

    Under the kit dialect this is ``json.dumps``' default spacing ``(", ", ": ")``
    - deliberately NOT the compact form under the commit-reveal hashes, and
    pinned by the kit's ``report_consensus`` vector. Under the book dialect the
    project's one canonical form applies throughout, compact. A report signed in
    the other spacing fails settlement at the exact moment both teams must
    agree, which is rule #35 and a zero for both.
    """
    separators = SPACED_SEPARATORS if profile.settlement_spaced else CANONICAL_SEPARATORS
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=separators)


def consensus_signature(report: dict[str, Any], profile: InteropProfile = DEFAULT) -> str:
    """SHA-256 over the settlement serialization of ``report``."""
    return hashlib.sha256(serialize_spaced(report, profile).encode("utf-8")).hexdigest()


def sign_report(report: dict[str, Any]) -> dict[str, Any]:
    """Sign-then-insert: hash the report, then add the signature under its key.

    The signature key is excluded from its own preimage, so a verifier pops it,
    re-serializes spaced, re-hashes, and compares. Raises if the report already
    carries a signature - re-signing a signed report silently changes the hash.
    """
    if SIGNATURE_KEY in report:
        raise ValueError("report is already signed - refusing to sign twice")
    signed = dict(report)
    signed[SIGNATURE_KEY] = consensus_signature(report)
    return signed


def verify_signed_report(signed: dict[str, Any]) -> bool:
    """Re-derive a signed report's consensus signature and compare."""
    if SIGNATURE_KEY not in signed:
        return False
    body = {key: value for key, value in signed.items() if key != SIGNATURE_KEY}
    return consensus_signature(body) == signed[SIGNATURE_KEY]


def series_aggregate(
    sub_games: list[dict[str, Any]], tie_score: int, profile: InteropProfile = DEFAULT
) -> dict[str, Any]:
    """Derive the aggregate from the rows - derived, never declared (SPEC section 6).

    ``ties`` counts only tie-SCORED rows; a zeroed row (timeout, technical loss)
    is a sanction credited to nobody, which keeps the accounting identity
    ``won_a + won_b + ties + zeroed == num_sub_games``. The +10 diversity award
    NEVER enters the totals - the league table applies it from the flag.

    On a series tie the App. F award is either ADDED to each side's total or
    REPLACES it, per ``profile.tie_award``. App. F table 17 is ambiguous and the
    kit does not settle it - ``report_consensus`` pins the settlement
    serialization and says nothing about aggregate semantics - so two lawful
    teams can disagree here under either dialect. ``total_score`` sits inside
    the settlement scope, so a disagreement forks ``mutual_agreement.sha256``
    and zeroes both teams under rule #35. Hence it is declared at the handshake.

    Args:
        sub_games: kit-shaped rows, each carrying ``score`` per group id.
        tie_score: the App. F tie award from the signed contract, never hardcoded.
        profile: the declared dialect, deciding the tie-award reading.
    """
    groups: list[str] = sorted({group for row in sub_games for group in row["score"]})
    totals = {g: sum(int(row["score"][g]) for row in sub_games) for g in groups}
    won = {g: sum(1 for row in sub_games if row.get("winner_group") == g) for g in groups}
    ties = sum(1 for row in sub_games if row.get("tie"))
    series_tie = len(groups) == 2 and totals[groups[0]] == totals[groups[1]]
    if series_tie:
        totals = {
            g: (total + tie_score if profile.tie_award_adds else tie_score)
            for g, total in totals.items()
        }
    winner = None if series_tie else max(totals, key=lambda g: totals[g])
    return {
        "total_score": totals,
        "sub_games_won": won,
        "ties": ties,
        "winner_group": winner,
        "series_tie": series_tie,
    }


def mutual_agreement_scope(
    game_id: str, sub_games: list[dict[str, Any]], aggregate: dict[str, Any]
) -> dict[str, Any]:
    """The trimmed consensus preimage - everything both teams must agree on.

    Each row keeps ONLY the pair-observable fields; per-side facts (timestamps,
    tokens, log file names, audit flags) are cut, because a whole-body scope is
    per-side by construction and two conformant teams could never match it.
    """
    return {
        "game_id": game_id,
        "aggregate": aggregate,
        "sub_games": [{key: row[key] for key in SCOPE_ROW_KEYS} for row in sub_games],
    }


def mutual_agreement_hash(scope: dict[str, Any], profile: InteropProfile = DEFAULT) -> str:
    """The settlement hash: the dialect's settlement form over the trimmed scope.

    Proven live cross-implementation under the kit dialect (SPEC section 6): the
    spaced-form hash of this exact scope matched byte-for-byte between two
    independent teams. A book-dialect pair matches on the compact form instead.
    What never works is a pair that has not agreed which.
    """
    return consensus_signature(scope, profile)
