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
    ROOT,
    SwappableHandler,
    git_head,
    start_server,
)
from _sparring_subgame import (  # noqa: E402
    OPPONENT_GROUP_ID,
    SUB_GAMES,
    make_scratch_config,
    run_sub_game,
)

sys.path.insert(0, str(ROOT / "src"))

from police_thief.constants import ROLE_POLICE  # noqa: E402
from police_thief.infra.email.naming import (  # noqa: E402
    declaration_file_name,
    result_file_name,
    write_lifecycle_file,
)
from police_thief.infra.email.report_blocks import group_block, links_block  # noqa: E402
from police_thief.infra.email.reports import (  # noqa: E402
    declaration_payload,
    result_payload,
)
from police_thief.shared.config import ConfigManager  # noqa: E402
from police_thief.shared.interop import (  # noqa: E402
    derive_game_ids,
    terms_from_contract,
)
from police_thief.shared.sysinfo import hardware_spec  # noqa: E402
from police_thief.shared.version import __version__  # noqa: E402


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
