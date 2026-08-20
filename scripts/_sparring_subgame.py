"""One sparring sub-game, and the scratch config it plays under.

Split from ``sparring_series.py`` under the 150-line rule. The sparring peer is
the class interop kit's own reference opponent, so this is the closest thing we
have to a cross-implementation rehearsal without booking a real team.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from _series_lib import (  # noqa: E402
    NEGOTIATE_WAIT_TIMEOUT,
    SwappableHandler,
    git_head,
    negotiate_patiently,
    play_networked,
    score_for,
    wait_for,
)

from police_thief.constants import ROLE_POLICE, ROLE_THIEF  # noqa: E402
from police_thief.domain.audit import audit_disclosure  # noqa: E402
from police_thief.domain.negotiation import build_terms  # noqa: E402
from police_thief.infra.email.naming import (  # noqa: E402
    config_file_name,
    write_lifecycle_file,
)
from police_thief.infra.email.reports import config_payload, log_payload  # noqa: E402
from police_thief.infra.http_transport import McpHttpTransport  # noqa: E402
from police_thief.infra.mcp_client import PeerClient  # noqa: E402
from police_thief.services.inbound import InboundHandler  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402
from police_thief.shared.config import ConfigManager  # noqa: E402
from police_thief.shared.interop import negotiate_extras, terms_from_contract  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

#: The series shape the kit's sparring peer expects, shared with the driver.
SUB_GAMES = 6
OPPONENT_GROUP_ID = "sparring-local"  # must match the kit's --group-id
OUR_ROLE_FOR = {
    n: (ROLE_POLICE if n % 2 == 1 else ROLE_THIEF) for n in range(1, SUB_GAMES + 1)
}


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
    our_extras = negotiate_extras(role, n, config.interop)
    promoted = handler_box.current
    if promoted is not None and promoted.declared_sub_game == n:
        handler = promoted  # a boundary-race greeting already landed in it
        print(f"  reusing the promoted handler for sub-game {n} (early greeting captured)")
    else:
        handler = InboundHandler(our_terms=our_terms, our_extras=our_extras,
                                 expect_role=expect_role, reorder_window=4)
        handler_box.current = handler

    matchrt = MatchRuntime(config, game_id=game_id, sub_game=n, github_commit=git_head())
    transport = McpHttpTransport(peer_url, timeout=contract.network.response_timeout_sec)
    client = PeerClient(transport, contract.network, contract.rate_limiter)

    greeting = build_terms(config, peer_id=our_group_id, games_played=0, sub_game=n,
                           step0_commit=matchrt.step0_commit)
    print(f"\n=== sub-game {n}: we are {role} ===")
    try:
        negotiate_patiently(client, greeting, announce=lambda message: print(f"  {message}"))
        wait_for(lambda: handler.opponent_terms, NEGOTIATE_WAIT_TIMEOUT,
                f"opponent's greeting for sub-game {n}")
        their_group = handler.opponent_terms.get("group_id")
        if their_group != opponent:
            raise RuntimeError(f"sub-game {n}: opponent declared group_id {their_group!r}, "
                               f"expected {opponent!r}")
        print(f"  negotiated: opponent={their_group}, "
              f"role={handler.opponent_terms.get('role')}")

        play_networked(role, matchrt, client, handler)
        outcome_type = (matchrt.result or {}).get("type", "undecided")
        print(f"  settled locally: {outcome_type} after {matchrt.view.step} steps")

        if n < SUB_GAMES:
            # Stage sub-game n+1's handler NOW: the kit greets the next sub-game the
            # instant its audit is posted, and the box promotes this on the mismatch.
            next_role = OUR_ROLE_FOR[n + 1]
            handler_box.pending = InboundHandler(
                our_terms=our_terms,
                our_extras=negotiate_extras(next_role, n + 1, config.interop),
                expect_role=ROLE_THIEF if next_role == ROLE_POLICE else ROLE_POLICE,
                reorder_window=4,
            )
        disclosure = matchrt.disclosure()
        client.submit_audit(disclosure)
        their_disclosure = wait_for(lambda: handler.audit, NEGOTIATE_WAIT_TIMEOUT,
                                   f"opponent's audit disclosure for sub-game {n}")
    finally:
        # One session per sub-game, closed with it. The session lives on the
        # transport, not the client - closing the wrong object here kills this
        # process mid-sub-game and takes the opponent's audit delivery with it.
        transport.close()
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
