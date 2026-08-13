"""The one-per-series declaration artifact, naming both groups.

Split from ``friendly_series.py`` under the 150-line rule. This is the pre-game
document that freezes everything constant across the sub-games (rulebook
ch. 9.3.3): identities, repositories, MCP endpoints, hardware, model, budget.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from _series_lib import git_head  # noqa: E402

from police_thief.infra.email.naming import (  # noqa: E402
    declaration_file_name,
    write_lifecycle_file,
)
from police_thief.infra.email.report_blocks import group_block  # noqa: E402
from police_thief.infra.email.reports import declaration_payload  # noqa: E402
from police_thief.infra.llm import effective_model  # noqa: E402
from police_thief.shared.config import ConfigManager  # noqa: E402
from police_thief.shared.sysinfo import hardware_spec  # noqa: E402
from police_thief.shared.version import __version__  # noqa: E402


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
            llm_model=effective_model(
                str(config.private_value("trash_talk", "provider", "template")),
                str(config.private_value("llm", "model", "")),
            ),
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
