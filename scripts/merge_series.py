"""Join the two halves of a rule-1 split into the one report a series has.

Rule 1 makes us run the cop and the thief as two completely separate processes,
so neither of them ever holds the whole series: each plays three windows and
writes three rows. A report is six. This is where the two halves meet, and it is
the ONLY place a six-row result is built - a locked process files nothing at all
(:func:`_series_windows.split_notice`), because three rows presented as a match
is the contradiction rules 33-35 void for both teams.

The join is deliberately a **file** join. The two processes share no memory, no
module holding live state and no variables - that is the property §2.4.2 is
protecting, and a merge that read anything out of a running peer would satisfy
the letter of "two processes" while breaking the thing the rule exists for. Both
halves are finished and on disk before this runs; it opens two directories and
nothing else.

Usage, after both halves have settled::

    uv run python scripts/merge_series.py \\
        results/friendly_<game_id>_police results/friendly_<game_id>_thief \\
        --opponent-group-id theirteam --opponent-games-played 0

Add ``--counted`` for a league series; the report then files itself here exactly
as the unsplit driver files it, because ch. 9.3 wants the send automatic rather
than in a particular process.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _series_lib import ROOT, inclusive_games, peer_repos  # noqa: E402
from _series_report import auto_report  # noqa: E402
from _series_subgame import load_config  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))

from police_thief.infra.email.naming import (  # noqa: E402
    result_file_name,
    write_lifecycle_file,
)
from police_thief.infra.email.report_blocks import links_block  # noqa: E402
from police_thief.infra.email.reports import result_payload  # noqa: E402
from police_thief.infra.email.result_check import validate_result_payload  # noqa: E402
from police_thief.services.series_guard import containment_alarm, load_rows  # noqa: E402
from police_thief.shared.interop import derive_game_ids, terms_from_contract  # noqa: E402


def parse_args() -> argparse.Namespace:
    """The two half-directories, and the few facts no row carries."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("halves", nargs=2, help="the two role-locked artifact directories")
    parser.add_argument("--opponent-group-id", required=True)
    parser.add_argument("--opponent-games-played", type=int, default=0,
                        help="the number THEY declared on the wire - each half prints it "
                             "when it exits; never a number you chose")
    parser.add_argument("--games-played", type=int, default=0)
    parser.add_argument("--first-meeting", action="store_true",
                        help="never had a valid counted game against THIS opponent before")
    parser.add_argument("--series-label", default="")
    parser.add_argument("--timezone", default="Asia/Jerusalem")
    parser.add_argument("--config-dir", default="")
    parser.add_argument("--counted", action="store_true")
    parser.add_argument("--opponent-repos", default="",
                        help="the opponent's repositories as cop=URL,thief=URL; "
                             "9.3.3 wants both teams' links and the merge is where "
                             "a split series' one report is built")
    parser.add_argument("--out", default="", help="where to write; default beside the halves")
    return parser.parse_args()


def gather(halves: list[str]) -> list[dict]:
    """Every row from both halves, in sub-game order, refusing an incomplete set.

    Raises:
        SystemExit: when a window is missing or claimed twice. A gap here would
            become a report that silently describes a shorter series than the
            one played, and the opponent's file would contradict it.
    """
    rows = [row for half in halves for row in load_rows(Path(half))]
    numbers = [int(row["sub_game_number"]) for row in rows]
    if len(numbers) != len(set(numbers)):
        raise SystemExit(f"REFUSING: a sub-game appears in both halves: {sorted(numbers)}")
    if sorted(numbers) != list(range(1, len(numbers) + 1)):
        raise SystemExit(
            f"REFUSING to merge an incomplete series: windows {sorted(numbers)}. "
            f"Both halves must have finished; a report is every sub-game or none."
        )
    return sorted(rows, key=lambda row: int(row["sub_game_number"]))


def main() -> None:
    """Merge the halves, validate the whole, write it, and report if counted."""
    args = parse_args()
    config = load_config("police", args)
    us = str(config.private_value("game", "group_id", "team-tbd"))
    recipient = str(config.private_value("email", "recipient", ""))
    rows = gather(args.halves)
    ids = derive_game_ids(terms_from_contract(config.contract), us,
                          args.opponent_group_id, args.series_label)
    links = links_block(ids[0], github={
        us: dict(config.private("game").get("repos", {})),
        args.opponent_group_id: peer_repos(getattr(args, "opponent_repos", ""))})

    alarm = containment_alarm(rows)
    if alarm:
        print(f"\n{alarm}")
    result = result_payload(
        game_uid=ids[1], game_id=ids[0], links=links, timezone=args.timezone,
        group_ids=sorted([us, args.opponent_group_id]), sub_games=rows,
        tie_score=config.contract.scoring.tie_score,
        games_played={us: args.games_played + (1 if args.counted else 0),
                      args.opponent_group_id: inclusive_games(
                          args.opponent_games_played, args.counted)},
        first_meeting=args.first_meeting, counted=args.counted, recipient=recipient,
    )
    validate_result_payload(result, tie_score=config.contract.scoring.tie_score)
    out = Path(args.out or Path(args.halves[0]).parent / f"friendly_{ids[0]}")
    out.mkdir(parents=True, exist_ok=True)
    path = write_lifecycle_file(out, result_file_name(ids[0]), result)
    league = result["league"]
    if not args.counted and league["counted"]:
        raise SystemExit(f"REFUSING: a friendly reported counted=true ({league})")
    print(f"merged {len(rows)} rows from {len(args.halves)} halves -> {path}")
    print(f"league gate : {json.dumps(league)}")
    print(f"final_result: {json.dumps(result['final_result'], indent=2)}")
    auto_report(result, out, recipient)


if __name__ == "__main__":
    main()
