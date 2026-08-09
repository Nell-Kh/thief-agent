"""A persistent driver for a full six-sub-game series against the kit's sparring peer.

Extends the one-off rehearsal from TODO 8.15.3w into a long-running process: it stays up across
all six sub-games (role alternating each one, as the kit's own ``netplay.py`` does on its side),
plays each sub-game for real over MCP against ``python -m sparring.cli serve --peer <us> --role
thief``, and writes OUR OWN four lifecycle artifacts (declaration_/config_/log_/result_) via
``infra/email/reports.py`` so ``tools/check_artifacts.py <ours> <theirs>`` can prove the
cross-team join (TODO 8.15.4w).

Usage::

    .venv/Scripts/python.exe scripts/sparring_series.py

Then, in the sibling kit repo, with a *Python 3.12* interpreter::

    python -m sparring.cli serve --port 8931 --peer http://127.0.0.1:8801/mcp \\
        --role thief --group-id sparring-local --scent-model multiplicative_book_v1

Both fixes already proven in 8.15.3w are applied here: ``world.map_area`` is overridden to
``"Haifa"`` (the kit's own default ``setting``) in a scratch copy of ``config/``, never in the
real ``config/game.json``; the scent-model lock already matches by construction
(``shared/interop.py``'s ``SCENT_MODEL_SHA256`` is the ``multiplicative_book_v1`` hash) as long as
the kit is told to declare the same model with ``--scent-model multiplicative_book_v1``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _series_lib import (  # noqa: E402
    NEGOTIATE_WAIT_TIMEOUT,
    ROOT,
    SwappableHandler,
    git_head,
    negotiate_patiently,
    play_networked,
    score_for,
    start_server,
    wait_for,
)

sys.path.insert(0, str(ROOT / "src"))

from police_thief.constants import ROLE_POLICE, ROLE_THIEF  # noqa: E402
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
from police_thief.infra.http_transport import McpHttpTransport  # noqa: E402
from police_thief.infra.mcp_client import PeerClient  # noqa: E402
from police_thief.services.inbound import InboundHandler  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402
from police_thief.shared.config import ConfigManager  # noqa: E402
from police_thief.shared.interop import (  # noqa: E402
    derive_game_ids,
    negotiate_extras,
    terms_from_contract,
)
from police_thief.shared.sysinfo import hardware_spec  # noqa: E402
from police_thief.shared.version import __version__  # noqa: E402

SUB_GAMES = 6
OPPONENT_GROUP_ID = "sparring-local"  # must match the kit's --group-id
OUR_ROLE_FOR = {n: (ROLE_POLICE if n % 2 == 1 else ROLE_THIEF) for n in range(1, SUB_GAMES + 1)}


def make_scratch_config(scratch_dir: Path, setting: str = "Haifa") -> Path:
    """Copy ``config/`` into ``scratch_dir``, pinning ``world.map_area`` to ``setting``.

    The tracked ``config/game.json`` now ships "Haifa" (the kit peer's own default), so this
    scratch copy is normally a no-op; it stays because ``setting`` is a *signed* term and this
    rehearsal must keep working even if the tracked default is renegotiated for a real opponent.
    """
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)
    shutil.copytree(ROOT / "config", scratch_dir)
    game_json = scratch_dir / "game.json"
    data = json.loads(game_json.read_text(encoding="utf-8"))
    data["world"]["map_area"] = setting
    game_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return scratch_dir


def run_sub_game(n: int, scratch_dir: Path, peer_url: str, our_group_id: str, us: str,
                 opponent: str, game_id: str, game_uid: str, handler_box: SwappableHandler,
                 artifacts_dir: Path, links: dict[str, Any], recipient: str) -> dict[str, Any]:
    """Play sub-game ``n`` against the kit peer and return its scored row."""
    role = OUR_ROLE_FOR[n]
    expect_role = ROLE_THIEF if role == ROLE_POLICE else ROLE_POLICE
    config = ConfigManager.load(role, scratch_dir)
    contract = config.contract
    our_terms = terms_from_contract(contract)
    our_extras = negotiate_extras(role, n)
    handler = InboundHandler(our_terms=our_terms, our_extras=our_extras,
                             expect_role=expect_role, reorder_window=4)
    handler_box.current = handler

    matchrt = MatchRuntime(config, game_id=game_id, sub_game=n, github_commit=git_head())
    client = PeerClient(McpHttpTransport(peer_url), contract.network, contract.rate_limiter)

    greeting = build_terms(config, peer_id=our_group_id, games_played=0, sub_game=n,
                           step0_commit=matchrt.step0_commit)
    print(f"\n=== sub-game {n}: we are {role} ===")
    negotiate_patiently(client, greeting, announce=lambda message: print(f"  {message}"))
    wait_for(lambda: handler.opponent_terms, NEGOTIATE_WAIT_TIMEOUT,
            f"opponent's greeting for sub-game {n}")
    their_group = handler.opponent_terms.get("group_id")
    if their_group != opponent:
        raise RuntimeError(f"sub-game {n}: opponent declared group_id {their_group!r}, "
                           f"expected {opponent!r}")
    print(f"  negotiated: opponent={their_group}, role={handler.opponent_terms.get('role')}")

    play_networked(role, matchrt, client, handler)
    outcome_type = (matchrt.result or {}).get("type", "undecided")
    print(f"  settled locally: {outcome_type} after {matchrt.view.step} steps")

    disclosure = matchrt.disclosure()
    client.submit_audit(disclosure)
    their_disclosure = wait_for(lambda: handler.audit, NEGOTIATE_WAIT_TIMEOUT,
                               f"opponent's audit disclosure for sub-game {n}")
    their_report = audit_disclosure(their_disclosure, contract, **matchrt.audit_evidence())
    print(f"  our audit of their disclosure: {their_report.verdict}"
         + ("" if their_report.passed else f" - {their_report.violations}"))

    if not their_report.passed:
        outcome_type = "tamper_forfeit"
        score_us, score_them = 0, 0
    else:
        score_us = score_for(contract, outcome_type, role)
        score_them = score_for(contract, outcome_type, expect_role)
    zeroed = outcome_type in ("timeout", "technical_loss", "tamper_forfeit")
    tie = (not zeroed) and score_us == score_them
    winner = None if zeroed or tie else (us if score_us > score_them else opponent)

    log_names = {us: f"log_{game_id}_g{n:02d}.json", opponent: f"log_{game_id}_g{n:02d}.json"}
    row = {
        "sub_game_number": n, "roles": {us: role, opponent: expect_role},
        "started_at": "", "ended_at": "",
        "result": outcome_type, "winner_group": winner, "tie": tie,
        "steps": matchrt.view.step,
        "github_commit": {us: git_head(), opponent: git_head()},
        "tokens": {us: matchrt.ledger.total, opponent: 0},
        "score": {us: score_us, opponent: score_them},
        "log_files": log_names,
        "audit": {"log_verified": their_report.passed, "tampered": not their_report.passed},
    }

    write_lifecycle_file(
        artifacts_dir, config_file_name(game_id, n),
        config_payload(game_uid, game_id, n, our_terms, links, recipient, counted=False),
    )
    summary = {"sub_game_number": n, "role": role, "result": outcome_type,
              "steps": matchrt.view.step, "opponent_group_id": their_group}
    write_lifecycle_file(
        artifacts_dir, log_names[us],
        log_payload(game_uid, game_id, n, links, summary, matchrt.book.records, recipient,
                   counted=False),
    )
    return row


def main() -> None:
    """Parse the command line and run the full sparring series against the kit peer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8801)
    parser.add_argument("--peer", default="http://127.0.0.1:8931/mcp")
    parser.add_argument("--artifacts", default=str(ROOT / "results" / "sparring_series"))
    args = parser.parse_args()

    scratch_dir = make_scratch_config(Path(ROOT / "scripts" / "_scratch_config_sparring"))
    base_config = ConfigManager.load(ROLE_POLICE, scratch_dir)
    us = str(base_config.private_value("game", "group_id", "team-tbd"))
    opponent = OPPONENT_GROUP_ID
    terms = terms_from_contract(base_config.contract)
    game_id, game_uid = derive_game_ids(terms, us, opponent)
    print(f"game_id  = {game_id}")
    print(f"game_uid = {game_uid}")

    artifacts_dir = Path(args.artifacts)
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    handler_box = SwappableHandler()
    start_server(handler_box, args.port)
    print(f"serving on 127.0.0.1:{args.port}/mcp ; opponent expected at {args.peer}")
    time.sleep(1.0)  # let the server bind before the first greeting

    recipient = str(base_config.private_value("email", "recipient", ""))
    links = links_block(game_id, github={
        us: dict(base_config.private("game").get("repos", {})), opponent: {},
    })

    rows: list[dict[str, Any]] = []
    declared = False
    for n in range(1, SUB_GAMES + 1):
        row = run_sub_game(n, scratch_dir, args.peer, us, us, opponent, game_id, game_uid,
                           handler_box, artifacts_dir, links, recipient)
        if not declared:
            now = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
            groups = [
                group_block(group_id=us, group_name=str(base_config.private_value(
                    "game", "group_name", us)), members=list(base_config.private(
                        "game").get("members", [])), repos=dict(base_config.private(
                            "game").get("repos", {})),
                    mcp_servers={"police": f"http://127.0.0.1:{args.port}/mcp"},
                    llm_model=str(base_config.private_value("llm", "model", "template")),
                    hardware_spec=hardware_spec(), github_commit=git_head(),
                    counted_games_played=0, code_version=__version__),
                group_block(group_id=opponent, group_name="sparring peer (kit)", members=[],
                           repos={}, mcp_servers={"thief": args.peer}, llm_model="template",
                           hardware_spec={"note": "opponent process, not introspectable"},
                           github_commit="unknown", counted_games_played=0, code_version="kit"),
            ]
            write_lifecycle_file(
                artifacts_dir, declaration_file_name(game_id),
                declaration_payload(game_uid=game_uid, game_id=game_id, links=links,
                                   timezone="Asia/Jerusalem", started_at=now,
                                   num_sub_games=SUB_GAMES, groups=groups, counted=False,
                                   recipient=recipient,
                                   max_tokens_per_game=base_config.contract.network
                                   .token_budget_per_series),
            )
            declared = True
        rows.append(row)
        print(f"  sub-game {n} row: {row['result']} score={row['score']} tie={row['tie']} "
             f"winner={row['winner_group']}")

    result = result_payload(
        game_uid=game_uid, game_id=game_id, links=links, timezone="Asia/Jerusalem",
        group_ids=[us, opponent], sub_games=rows,
        tie_score=base_config.contract.scoring.tie_score,
        games_played={us: 0, opponent: None}, first_meeting=True, counted=False,
        recipient=recipient,
    )
    path = write_lifecycle_file(artifacts_dir, result_file_name(game_id), result)
    print(f"\nwrote result -> {path}")
    print(f"final_result: {json.dumps(result['final_result'], indent=2)}")
    print(f"\nall {SUB_GAMES} sub-games settled. Artifacts under {artifacts_dir}")


if __name__ == "__main__":
    main()
