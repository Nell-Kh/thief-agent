"""A fail-closed self-audit of our own result before it is ever mailed.

The league joins two teams' reports and zeroes both on a rule-35 contradiction,
so the most avoidable way to lose is to mail a report whose own numbers do not
reconcile - a total that is not the sum of its rows, a winner that is not the
higher total, a ``mutual_agreement`` hash that does not match the rows it
claims to cover. ``result_payload`` derives all of these, so a consistent build
passes untouched; this guard exists for the build that is *not* consistent - a
hand-assembled row, a future refactor, a mixed series carrying a technical-loss
row - catching it here, before the send, instead of at the audit that scores it.
"""

from __future__ import annotations

from typing import Any

from ...shared.interop_profile import DEFAULT, InteropProfile
from .consensus import (
    mutual_agreement_hash,
    mutual_agreement_scope,
    series_aggregate,
    settlement_confirmed,
)


class ResultInconsistencyError(ValueError):
    """Raised when a result payload's own numbers do not reconcile."""


def validate_result_payload(
    result: dict[str, Any], tie_score: int, profile: InteropProfile = DEFAULT
) -> None:
    """Re-derive every aggregate from the rows and refuse any mismatch.

    Args:
        result: a payload from :func:`reports.result_payload`.
        tie_score: the App. F tie award from the signed contract.

    Raises:
        ResultInconsistencyError: on the first identity that fails - a wrong
            total, a wrong winner, a broken row-accounting identity, a token
            sum that drifts, or a settlement hash that does not match the rows.
    """
    rows = result["sub_games"]
    groups = result["groups"]
    final = result["final_result"]

    if result["num_sub_games"] != len(rows):
        raise ResultInconsistencyError(
            f"num_sub_games {result['num_sub_games']} != {len(rows)} rows"
        )

    expected = series_aggregate(rows, tie_score=tie_score, profile=profile)
    for key in ("total_score", "sub_games_won", "ties", "winner_group", "series_tie"):
        if final.get(key) != expected[key]:
            raise ResultInconsistencyError(
                f"{key}: report says {final.get(key)!r}, rows derive {expected[key]!r}"
            )

    won = sum(expected["sub_games_won"][g] for g in groups)
    zeroed = sum(1 for row in rows if row.get("winner_group") is None and not row.get("tie"))
    if won + expected["ties"] + zeroed != len(rows):
        raise ResultInconsistencyError(
            f"row accounting broken: won {won} + ties {expected['ties']} + zeroed {zeroed} "
            f"!= {len(rows)} sub-games"
        )

    for group in groups:
        summed = sum(int(row["tokens"][group]) for row in rows)
        if final["tokens_total_series"].get(group) != summed:
            raise ResultInconsistencyError(
                f"tokens_total_series[{group}] {final['tokens_total_series'].get(group)} "
                f"!= row sum {summed}"
            )

    scope = mutual_agreement_scope(result["game_id"], rows, expected)
    recomputed = mutual_agreement_hash(scope, profile)
    claimed = result.get("mutual_agreement", {}).get("sha256")
    if claimed != recomputed:
        raise ResultInconsistencyError(
            f"mutual_agreement.sha256 {claimed} does not match the rows ({recomputed})"
        )

    confirmed = bool(result.get("mutual_agreement", {}).get("confirmed"))
    if confirmed != settlement_confirmed(rows):
        raise ResultInconsistencyError(
            f"mutual_agreement.confirmed is {confirmed}, but the rows derive "
            f"{settlement_confirmed(rows)} - a report may never claim an agreement "
            f"its own audit results do not support (rules #35/#38)"
        )
