"""The lifecycle JSON payloads of one league game, in the league's joined shape.

One shared ``game_uid`` threads through all four files (rulebook ch. 9.3.3) so
files from different games can never mix. The shapes follow the cross-team
convention (kit schema 1.1): the declaration holds everything fixed across the
series, the config artifact carries the flat negotiated terms so an auditor
can RE-DERIVE the ``game_uid``, the log carries the sealed records, and the
result carries the ``mutual_agreement`` settlement hash both teams must match
byte-for-byte.

The ``links``/``group`` joining blocks that feed these payloads live in
:mod:`report_blocks`.
"""

from __future__ import annotations

from typing import Any

from ...shared.config_io import sha256_of
from ...shared.interop_profile import DEFAULT, InteropProfile
from .consensus import (
    mutual_agreement_hash,
    mutual_agreement_scope,
    series_aggregate,
    settlement_confirmed,
)
from .naming import config_file_name
from .report_blocks import _is_armed, league_block

SCHEMA_VERSION = "1.1"


def settlement_game_id(game_id: str, profile: InteropProfile = DEFAULT) -> str:
    """The ``game_id`` as it appears INSIDE the settlement preimage.

    Under the kit scope it is the artifact's own id, unchanged. Under the uid
    scope uoh-ay26 place the bare series label there (``"G010"``) - the uid
    beside it already carries the pair-and-label identity - so the trailing
    label is lifted out of ``<a>-vs-<b>-<label>``.

    A ``game_id`` with no label (the unlabelled derivation) has nothing to lift
    and is returned whole; that pair must agree a label before settling, which
    is exactly what ``--series-label`` exists to make them do.
    """
    if profile.scope_carries_aggregate:
        return game_id
    _, separator, label = game_id.partition("-vs-")
    if not separator or "-" not in label:
        return game_id
    return label.split("-", 1)[1]


def _base(
    game_uid: str, game_id: str, links: dict[str, Any], counted: bool, recipient: str
) -> dict[str, Any]:
    """The joining fields every lifecycle artifact opens with."""
    return {
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "game_uid": game_uid,
        "links": links,
        "league": league_block(counted, recipient),
    }


def declaration_payload(
    *, game_uid: str, game_id: str, links: dict[str, Any], timezone: str, started_at: str,
    num_sub_games: int, max_tokens_per_game: int, groups: list[dict[str, Any]],
    recipient: str, counted: bool = True,
) -> dict[str, Any]:
    """The pre-game declaration: everything fixed across the series, frozen.

    No end time by design - nothing in it is known only after the games.
    """
    return {
        **_base(game_uid, game_id, links, counted, recipient),
        "declaration_type": "pre_game_declaration",
        "report_type": "declaration",
        "timezone": timezone,
        "game_started_at": started_at,
        "num_sub_games": num_sub_games,
        "max_tokens_per_game": max_tokens_per_game,
        "groups": {"group_1": groups[0], "group_2": groups[1]},
    }


def config_payload(
    game_uid: str, game_id: str, mini: int, terms: dict[str, Any],
    links: dict[str, Any], recipient: str, counted: bool = True,
) -> dict[str, Any]:
    """The locked terms, hash inline - carrying them lets an auditor RE-DERIVE the uid."""
    return {
        **_base(game_uid, game_id, links, counted, recipient),
        "sub_game_number": mini,
        "config_name": config_file_name(game_id, mini),
        "terms": terms,
        "config_sha256": sha256_of(terms),
    }


def log_payload(
    game_uid: str, game_id: str, mini: int, links: dict[str, Any],
    summary: dict[str, Any], records: list[dict[str, Any]], recipient: str,
    counted: bool = True,
) -> dict[str, Any]:
    """One sub-game's sealed history (payloads, nonces, commits) in the joined shape."""
    return {
        **_base(game_uid, game_id, links, counted, recipient),
        "sub_game_number": mini,
        "summary": summary,
        "records": records,
    }


def result_payload(
    *, game_uid: str, game_id: str, links: dict[str, Any], timezone: str,
    group_ids: list[str], sub_games: list[dict[str, Any]], tie_score: int,
    games_played: dict[str, int | None], first_meeting: bool, recipient: str,
    counted: bool = True, profile: InteropProfile = DEFAULT,
) -> dict[str, Any]:
    """The final result report - the mandatory JSON mailed to the league address.

    Everything aggregate is DERIVED from the rows exactly once, so the consensus
    preimage and ``final_result`` can never drift apart. The +10 diversity award
    stays a flag - it never enters the totals, and never fires on a report whose
    counted claim did not arm (recipient mismatch). ``games_played`` holds each
    group's own inclusive count; an opponent's untold count rides as ``None``.
    """
    aggregate = series_aggregate(sub_games, tie_score=tie_score, profile=profile)
    winner = aggregate["winner_group"]
    armed = _is_armed(counted, recipient)
    return {
        **_base(game_uid, game_id, links, counted, recipient),
        "report_type": "final_game_result",
        "timezone": timezone,
        "groups": group_ids,
        "num_sub_games": len(sub_games),
        "sub_games": sub_games,
        "final_result": {
            **aggregate,
            "tokens_total_series": {
                g: sum(int(row["tokens"][g]) for row in sub_games) for g in group_ids
            },
            "games_played_including_this": games_played,
            "first_meeting_between_groups": first_meeting,
            "diversity_reward_applied": {
                g: bool(armed and first_meeting and g == winner) for g in group_ids
            },
        },
        "mutual_agreement": {
            "sha256": mutual_agreement_hash(
                mutual_agreement_scope(
                    settlement_game_id(game_id, profile),
                    sub_games,
                    aggregate,
                    game_uid=game_uid,
                    profile=profile,
                ),
                profile,
            ),
            "confirmed": settlement_confirmed(sub_games),
        },
    }
