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

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _series_lib import (  # noqa: E402
    NEGOTIATE_WAIT_TIMEOUT,
    OPENING_WAIT_SECONDS,
    ROOT,
    SwappableHandler,
    git_head,
    negotiate_patiently,
    other_role,
    play_networked,
    score_for,
    start_server,
    wait_for,
)

sys.path.insert(0, str(ROOT / "src"))

from police_thief.domain.audit import audit_disclosure  # noqa: E402
from police_thief.domain.negotiation import build_terms  # noqa: E402
from police_thief.infra.email.naming import (  # noqa: E402
    config_file_name,
    declaration_file_name,
    result_file_name,
    write_lifecycle_file,
)
from police_thief.infra.email.report_blocks import group_block, links_block  # noqa: E402
from police_thief.infra.email.reports import (  # noqa: E402
    config_payload,
    declaration_payload,
    log_payload,
    result_payload,
)
from police_thief.infra.email.result_check import validate_result_payload  # noqa: E402
from police_thief.infra.http_transport import McpHttpTransport  # noqa: E402
from police_thief.infra.mcp_client import PeerClient  # noqa: E402
from police_thief.services.inbound import InboundHandler  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402
from police_thief.services.series_guard import (  # noqa: E402
    CONTAINED_FAILURES,
    archive_previous_run,
    containment_alarm,
    failure_reason,
    load_rows,
    save_rows,
    technical_loss_row,
)
from police_thief.shared.config import ConfigManager  # noqa: E402
from police_thief.shared.interop import (  # noqa: E402
    derive_game_ids,
    negotiate_extras,
    terms_from_contract,
)
from police_thief.shared.preflight import counted_series_blockers  # noqa: E402
from police_thief.shared.sysinfo import hardware_spec  # noqa: E402
from police_thief.shared.version import __version__  # noqa: E402


def load_config(role: str, args) -> ConfigManager:
    """Load ``role``'s configuration, honouring an explicit ``--config-dir``."""
    return ConfigManager.load(role, args.config_dir) if args.config_dir \
        else ConfigManager.load(role)


def play_sub_game(n: int, role: str, args, ids: tuple[str, str], us: str,
                  handler_box: SwappableHandler, artifacts: Path,
                  links: dict[str, Any], recipient: str) -> dict[str, Any]:
    """Negotiate, play and mutually audit one sub-game; return its result row."""
    game_id, game_uid = ids
    expect_role = other_role(role)
    config = load_config(role, args)
    contract = config.contract
    our_terms = terms_from_contract(contract)
    handler = InboundHandler(our_terms=our_terms, our_extras=negotiate_extras(role, n),
                             expect_role=expect_role, reorder_window=4)
    handler_box.current = handler

    matchrt = MatchRuntime(config, game_id=game_id, sub_game=n, github_commit=git_head())
    client = PeerClient(McpHttpTransport(args.peer), contract.network, contract.rate_limiter)

    print(f"\n=== sub-game {n}: we are {role} (opponent {expect_role}) ===")
    negotiate_patiently(
        client,
        build_terms(config, peer_id=us, games_played=args.games_played,
                    sub_game=n, step0_commit=matchrt.step0_commit),
        wait_seconds=args.wait,
        announce=lambda message: print(f"  {message}"),
    )
    wait_for(lambda: handler.opponent_terms, NEGOTIATE_WAIT_TIMEOUT,
             f"opponent's greeting for sub-game {n}")
    their_group = handler.opponent_terms.get("group_id")
    if their_group != args.opponent_group_id:
        raise RuntimeError(f"sub-game {n}: opponent declared group_id {their_group!r}, "
                           f"expected {args.opponent_group_id!r} - check --opponent-group-id")
    print(f"  negotiated OK with {their_group} (role {handler.opponent_terms.get('role')})")

    play_networked(role, matchrt, client, handler)
    outcome_type = (matchrt.result or {}).get("type", "undecided")
    print(f"  settled locally: {outcome_type} after {matchrt.view.step} steps")

    client.submit_audit(matchrt.disclosure())
    theirs = wait_for(lambda: handler.audit, NEGOTIATE_WAIT_TIMEOUT,
                      f"opponent's audit disclosure for sub-game {n}")
    report = audit_disclosure(theirs, contract, **matchrt.audit_evidence())
    print(f"  our audit of their disclosure: {report.verdict}"
          + ("" if report.passed else f" - {report.violations}"))

    if not report.passed:
        outcome_type, score_us, score_them = "tamper_forfeit", 0, 0
    else:
        score_us = score_for(contract, outcome_type, role)
        score_them = score_for(contract, outcome_type, expect_role)
    zeroed = outcome_type in ("timeout", "technical_loss", "tamper_forfeit")
    tie = (not zeroed) and score_us == score_them
    winner = None if zeroed or tie else (us if score_us > score_them else args.opponent_group_id)

    opponent = args.opponent_group_id
    log_name = f"log_{game_id}_g{n:02d}.json"
    row = {
        "sub_game_number": n, "roles": {us: role, opponent: expect_role},
        "started_at": "", "ended_at": "",
        "result": outcome_type, "winner_group": winner, "tie": tie,
        "steps": matchrt.view.step,
        "github_commit": {us: git_head(), opponent: "unknown"},
        "tokens": {us: matchrt.ledger.total, opponent: 0},
        "score": {us: score_us, opponent: score_them},
        "log_files": {us: log_name, opponent: log_name},
        "audit": {"log_verified": report.passed, "tampered": not report.passed},
    }

    write_lifecycle_file(artifacts, config_file_name(game_id, n),
                         config_payload(game_uid, game_id, n, our_terms, links, recipient,
                                        counted=args.counted))
    summary = {"sub_game_number": n, "role": role, "result": outcome_type,
               "steps": matchrt.view.step, "opponent_group_id": their_group}
    write_lifecycle_file(artifacts, log_name,
                         log_payload(game_uid, game_id, n, links, summary,
                                     matchrt.book.records, recipient, counted=args.counted))
    return row


def write_declaration(args, ids: tuple[str, str], us: str, config: ConfigManager,
                      artifacts: Path, links: dict[str, Any], recipient: str) -> None:
    """Write the one-per-series declaration artifact naming both groups."""
    game_id, game_uid = ids
    private = config.private("game")
    groups = [
        group_block(
            group_id=us, group_name=str(config.private_value("game", "group_name", us)),
            members=list(private.get("members", [])), repos=dict(private.get("repos", {})),
            mcp_servers={"self": args.public_url or f"http://127.0.0.1:{args.port}/mcp"},
            llm_model=str(config.private_value("llm", "model", "template")),
            hardware_spec=hardware_spec(), github_commit=git_head(),
            counted_games_played=args.games_played, code_version=__version__),
        group_block(
            group_id=args.opponent_group_id, group_name=args.opponent_group_id, members=[],
            repos={}, mcp_servers={"peer": args.peer}, llm_model="unknown",
            hardware_spec={"note": "opponent process, not introspectable"},
            github_commit="unknown", counted_games_played=0, code_version="unknown"),
    ]
    write_lifecycle_file(
        artifacts, declaration_file_name(game_id),
        declaration_payload(
            game_uid=game_uid, game_id=game_id, links=links, timezone=args.timezone,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            num_sub_games=args.rounds, groups=groups, counted=args.counted,
            recipient=recipient,
            max_tokens_per_game=config.contract.network.token_budget_per_series),
    )


def parse_args() -> argparse.Namespace:
    """Command-line surface: everything opponent-specific is an argument."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--peer", required=True, help="opponent's MCP URL")
    parser.add_argument("--opponent-group-id", required=True,
                        help="the group_id the opponent will declare; a mismatch aborts")
    parser.add_argument("--start-role", required=True, choices=["police", "thief"],
                        help="our role in sub-game 1; alternates each sub-game after")
    parser.add_argument("--rounds", type=int, default=6, help="sub-games in the series")
    parser.add_argument("--port", type=int, default=8801, help="port our MCP server binds")
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address; 0.0.0.0 for a direct remote connection")
    parser.add_argument("--public-url", default="",
                        help="our tunnel URL, recorded in the declaration artifact")
    parser.add_argument("--artifacts", default="", help="output directory for artifacts")
    parser.add_argument("--config-dir", default="",
                        help="alternate config/ directory (a second identity, for rehearsals)")
    parser.add_argument("--wait", type=float, default=OPENING_WAIT_SECONDS,
                        help="seconds to keep re-offering terms to an opponent that has "
                             "not started yet (the two-terminal gap)")
    parser.add_argument("--games-played", type=int, default=0,
                        help="counted games already played against this opponent (rule 37)")
    parser.add_argument("--timezone", default="Asia/Jerusalem")
    parser.add_argument("--counted", action="store_true",
                        help="claim league credit; only arms when addressed to the "
                             "binding league address, and never for a friendly")
    return parser.parse_args()


def main() -> None:
    """Run the whole series, write every artifact, and verify the league gate."""
    args = parse_args()
    config = load_config(args.start_role, args)
    us = str(config.private_value("game", "group_id", "team-tbd"))
    if us == args.opponent_group_id:
        raise SystemExit("refusing to play: our group_id equals --opponent-group-id")
    recipient = str(config.private_value("email", "recipient", ""))
    blockers = counted_series_blockers(
        recipient, str(config.private_value("email", "mode", ""))
    )
    if args.counted and blockers:
        raise SystemExit(
            "REFUSING to play a counted series that cannot count:\n"
            + "\n".join(f"  - {blocker}" for blocker in blockers)
            + "\nThis series would play perfectly and earn zero credit. Fix the "
              "config, then re-run."
        )
    terms = terms_from_contract(config.contract)
    ids = derive_game_ids(terms, us, args.opponent_group_id)
    print(f"game_id  = {ids[0]}\ngame_uid = {ids[1]}")
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
    start_server(handler_box, args.port, args.host)
    print(f"serving on {args.host}:{args.port}/mcp ; opponent at {args.peer}")
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
        games_played={us: args.games_played, args.opponent_group_id: None},
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
    print(f"\nall {args.rounds} sub-games settled. Artifacts under {artifacts}")


if __name__ == "__main__":
    main()
