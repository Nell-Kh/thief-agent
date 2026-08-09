"""Tests for the pre-send result self-audit - a wrong report never leaves the door."""

from __future__ import annotations

import pytest

from police_thief.infra.email.report_blocks import links_block
from police_thief.infra.email.reports import result_payload
from police_thief.infra.email.result_check import (
    ResultInconsistencyError,
    validate_result_payload,
)
from police_thief.services.series_guard import technical_loss_row

A, B = "yanell11", "rivals"
LINKS = links_block("yanell11-vs-rivals", {A: {}, B: {}})


def row(n: int, winner: str | None, sa: int, sb: int, *, tie: bool = False) -> dict:
    """One result row shaped as the settlement scope expects."""
    return {
        "sub_game_number": n, "roles": {A: "police", B: "thief"},
        "started_at": "", "ended_at": "", "result": "capture",
        "winner_group": winner, "tie": tie, "steps": 6,
        "github_commit": {A: "x", B: "y"}, "tokens": {A: 0, B: 0},
        "score": {A: sa, B: sb}, "log_files": {A: "l", B: "l"}, "audit": {},
    }


def build(rows: list[dict]) -> dict:
    """A result payload assembled from the given rows."""
    return result_payload(
        game_uid="u", game_id="yanell11-vs-rivals", links=LINKS, timezone="Asia/Jerusalem",
        group_ids=[A, B], sub_games=rows, tie_score=2, games_played={A: 0, B: None},
        first_meeting=True, recipient="rmisegal+uoh26finalgame@gmail.com", counted=True,
    )


def test_a_freshly_built_result_passes_its_own_audit() -> None:
    validate_result_payload(build([row(1, A, 20, 5), row(2, A, 20, 5)]), tie_score=2)


def test_a_series_with_a_technical_loss_row_still_reconciles() -> None:
    """Commit-1's dead-sub-game row must not break the row-accounting identity."""
    rows = [
        row(1, A, 20, 5),
        technical_loss_row(sub_game_number=2, us=A, opponent=B, role="thief",
                           expect_role="police", game_id="yanell11-vs-rivals",
                           github_commit="x", reason="timeout"),
        row(3, A, 20, 5),
    ]
    validate_result_payload(build(rows), tie_score=2)  # must not raise


def test_a_tampered_total_is_caught() -> None:
    result = build([row(1, A, 20, 5)])
    result["final_result"]["total_score"][A] = 999
    with pytest.raises(ResultInconsistencyError, match="total_score"):
        validate_result_payload(result, tie_score=2)


def test_a_wrong_winner_is_caught() -> None:
    result = build([row(1, A, 20, 5)])
    result["final_result"]["winner_group"] = B
    with pytest.raises(ResultInconsistencyError, match="winner_group"):
        validate_result_payload(result, tie_score=2)


def test_a_stale_settlement_hash_is_caught() -> None:
    result = build([row(1, A, 20, 5)])
    result["mutual_agreement"]["sha256"] = "0" * 64
    with pytest.raises(ResultInconsistencyError, match="mutual_agreement"):
        validate_result_payload(result, tie_score=2)


def test_a_miscounted_sub_game_total_is_caught() -> None:
    result = build([row(1, A, 20, 5), row(2, A, 20, 5)])
    result["num_sub_games"] = 5
    with pytest.raises(ResultInconsistencyError, match="num_sub_games"):
        validate_result_payload(result, tie_score=2)


def test_a_drifted_token_total_is_caught() -> None:
    result = build([row(1, A, 20, 5)])
    result["final_result"]["tokens_total_series"][A] = 12345
    with pytest.raises(ResultInconsistencyError, match="tokens_total_series"):
        validate_result_payload(result, tie_score=2)
