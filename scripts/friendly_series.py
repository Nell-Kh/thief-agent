"""Play a full series against ANY real opponent and write our lifecycle artifacts.

This is the league driver (TODO 9.4): unlike ``local_two_process_match.py`` (a
rehearsal that writes nothing) and ``sparring_series.py`` (hardwired to the class
interop kit's sparring peer), every opponent-specific value here is an argument,
and the four lifecycle artifact kinds are written to disk so both sides can diff
them (TODO 9.4.4).

Uncounted by default. A friendly must never claim league credit, and it cannot
even by accident: :func:`reports.league_block` arms ``counted`` only when the
report is addressed to the binding league address, so a friendly addressed
anywhere else reports ``counted: false, reason: "friendly"``. The driver asserts
that invariant on the written result before it exits.

Usage - a friendly against a tunnelled opponent, us starting as police::

    .venv/Scripts/python.exe scripts/friendly_series.py \\
        --peer https://their-tunnel.example/mcp \\
        --opponent-group-id theirteam \\
        --start-role police --rounds 6

Both peers must agree beforehand on the signed terms (notably ``setting``, which
this repo commits as "Haifa"), on who starts as which role - the two sides must
be complementary - and on the sub-game count. Whoever starts first simply waits
(``--wait``, default 120s) for the other to come up.

Each series lands in its own ``results/friendly_<game_id>/`` folder. When you
cross-check against the opponent's bundle, point the kit's checker at the two
**series folders**, never at ``results/``::

    python tools/check_artifacts.py results/friendly_<game_id> <theirs>

Its two-directory join recurses (``rglob``) where the single-directory check does
not, so a tree holding several archived series makes honest history look like the
contradictory-report shape rule 35 zeroes - the kit's own P5 finding.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _series_cli import parse_args  # noqa: E402
from _series_declaration import write_declaration  # noqa: E402
from _series_lib import (  # noqa: E402
    ROOT,
    SwappableHandler,
    git_head,
    other_role,
    start_server,
)
from _series_report import (  # noqa: E402
    auto_report,
    friendly_recipients,
    reporting_blockers,
)
from _series_subgame import (  # noqa: E402
    build_handler,
    load_config,
    peer_url_for,
    play_sub_game,
)

sys.path.insert(0, str(ROOT / "src"))

from police_thief.infra.email.naming import (  # noqa: E402
    result_file_name,
    write_lifecycle_file,
)
from police_thief.infra.email.report_blocks import links_block  # noqa: E402
from police_thief.infra.email.reports import (  # noqa: E402
    result_payload,
)
from police_thief.infra.email.result_check import validate_result_payload  # noqa: E402
from police_thief.services.series_guard import (  # noqa: E402
    CONTAINED_FAILURES,
    archive_previous_run,
    containment_alarm,
    failure_reason,
    load_rows,
    save_rows,
    technical_loss_row,
)
from police_thief.shared.interop import (  # noqa: E402
    derive_game_ids,
    terms_from_contract,
)
from police_thief.shared.preflight import counted_series_blockers  # noqa: E402


def main() -> None:
    """Run the whole series, write every artifact, and verify the league gate."""
    args = parse_args()
    config = load_config(args.start_role, args)
    us = str(config.private_value("game", "group_id", "team-tbd"))
    if us == args.opponent_group_id:
        raise SystemExit("refusing to play: our group_id equals --opponent-group-id")
    recipient = str(config.private_value("email", "recipient", ""))
    friendly_to = friendly_recipients(args.friendly_report_to)
    blockers = counted_series_blockers(
        recipient, str(config.private_value("email", "mode", ""))
    ) + reporting_blockers(args.counted)
    if args.counted and blockers:
        raise SystemExit(
            "REFUSING to play a counted series that cannot count:\n"
            + "\n".join(f"  - {blocker}" for blocker in blockers)
            + "\nThis series would play perfectly and earn zero credit. Fix the "
              "config, then re-run."
        )
    terms = terms_from_contract(config.contract)
    ids = derive_game_ids(terms, us, args.opponent_group_id,
                          getattr(args, 'series_label', ''))
    print(f"game_id  = {ids[0]}\ngame_uid = {ids[1]}")
    # The commit is already sealed into every Step-0 record and filed in every
    # row - but it was never SHOWN to the operator, and on 2026-08-17 we played
    # sharNamr on a working tree that had never had the step-rule fix applied,
    # told them in writing that it had, and only found out when they diffed the
    # field. The answer was in our own result file the whole time. One line at
    # the top, before anything is negotiated, so "the fix is committed" and
    # "the fix is running" stop being the same sentence.
    print(f"commit   = {git_head()}   <- verify this is the code you meant to play")
    print(f"setting  = {terms['setting']!r} (a signed term - must match the opponent)")

    artifacts = Path(args.artifacts or ROOT / "results" / f"friendly_{ids[0]}")
    recovered = load_rows(artifacts)
    archived = archive_previous_run(artifacts)
    if archived is not None:
        print(f"previous run preserved -> {archived}")
        if recovered:
            print(f"  it holds {len(recovered)} settled sub-game row(s); this run starts "
                  f"fresh and does not reuse them")
    artifacts.mkdir(parents=True, exist_ok=True)

    handler_box = SwappableHandler()
    # Bind sub-game 1 BEFORE the socket opens. An opponent already waiting on
    # us greets on the first millisecond the port answers, and an unbound box
    # answers "peer is booting" - retryable by design, but it spends one of the
    # opponent's three tries and its backoff on a race we can simply not have.
    # `play_sub_game` finds this handler already declared for sub-game 1 and
    # keeps it, so the greeting it may already hold is not thrown away.
    handler_box.current = build_handler(config, args.start_role, 1)
    start_server(handler_box, args.port, args.host)
    print(f"serving on {args.host}:{args.port}/mcp")
    print(f"  we are {args.start_role} in sub-game 1, so we dial "
          f"{peer_url_for(args, args.start_role)}")
    if getattr(args, "peer_thief", ""):
        print(f"  role-split opponent: as police we dial {args.peer_thief} , "
              f"as thief {args.peer}")
    time.sleep(1.0)  # let the server bind before the first greeting

    links = links_block(ids[0], github={
        us: dict(config.private("game").get("repos", {})), args.opponent_group_id: {}})
    write_declaration(args, ids, us, config, artifacts, links, recipient)

    rows, role = [], args.start_role
    for n in range(1, args.rounds + 1):
        try:
            rows.append(play_sub_game(n, role, args, ids, us, handler_box, artifacts,
                                      links, recipient))
        except CONTAINED_FAILURES as error:
            reason = failure_reason(error)
            print(f"  sub-game {n} did not finish ({reason}) - scoring a technical loss "
                  f"and continuing the series")
            rows.append(technical_loss_row(
                sub_game_number=n, us=us, opponent=args.opponent_group_id, role=role,
                expect_role=other_role(role), game_id=ids[0], github_commit=git_head(),
                reason=reason))
        # Persist after EVERY sub-game: from here on a crash costs the rest of
        # the series, never the games already won.
        save_rows(artifacts, rows)
        role = other_role(role)

    alarm = containment_alarm(rows)
    if alarm:
        print(f"\n{alarm}")

    result = result_payload(
        game_uid=ids[1], game_id=ids[0], links=links, timezone=args.timezone,
        group_ids=[us, args.opponent_group_id], sub_games=rows,
        tie_score=config.contract.scoring.tie_score,
        games_played={
            # Ours, inclusive: a COUNTED series advances the pairwise counter,
            # a friendly does not (rulebook: warm-up games are not counted).
            us: args.games_played + (1 if args.counted else 0),
            # Theirs, as THEY declared it on the wire - never a number we made
            # up. Rule #38 disqualifies whoever filed the false declaration.
            args.opponent_group_id: handler_box.opponent_games_played,
        },
        first_meeting=args.games_played == 0, counted=args.counted, recipient=recipient,
    )
    validate_result_payload(result, tie_score=config.contract.scoring.tie_score)
    path = write_lifecycle_file(artifacts, result_file_name(ids[0]), result)

    league = result["league"]
    if not args.counted and league["counted"]:
        raise SystemExit(f"REFUSING: a friendly reported counted=true ({league})")
    print(f"\nwrote result -> {path}")
    print(f"league gate : {json.dumps(league)}")
    if args.counted and not league["counted"]:
        # Not fatal - the gate did its job - but silence here would let someone
        # believe a series counted for the league when it never armed.
        print(f"WARNING: --counted was requested but did NOT arm ({league['reason']}). "
              f"Set [email].recipient to the binding league address to claim credit.")
    print(f"final_result: {json.dumps(result['final_result'], indent=2)}")
    # Rule 9.3: a COUNTED series reports itself, with no human step. A friendly
    # returns from here without sending, which is the safety property the old
    # fully-manual design existed to protect - kept exactly where it costs
    # nothing, and dropped exactly where the rulebook forbids it.
    auto_report(result, artifacts, recipient, friendly_to=friendly_to)
    print(f"\nall {args.rounds} sub-games settled. Artifacts under {artifacts}")


if __name__ == "__main__":
    main()
