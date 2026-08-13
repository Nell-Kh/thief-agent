"""Play a full multi-round series between two real OS processes on localhost.

This is the same wire protocol two separate teams would use against each
other - negotiate, alternate real HTTP `receive_turn` calls, then a mutual
audit, repeated for N rounds with roles alternating each round exactly like
a real league series - just pointed at ourselves instead of a remote
opponent. Run one copy per side, each in its own process, each starting on
the opposite role:

    .venv/Scripts/python.exe scripts/local_two_process_match.py \\
        --start-role police --port 8801 --peer http://127.0.0.1:8802/mcp
    .venv/Scripts/python.exe scripts/local_two_process_match.py \\
        --start-role thief --port 8802 --peer http://127.0.0.1:8801/mcp

Add ``--rounds N`` to change the series length (default 6, matching the
league's six-sub-game convention). No lifecycle files are written and
nothing is emailed - this is a local rehearsal, not a counted or reported
game.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _series_lib import (  # noqa: E402
    NEGOTIATE_WAIT_TIMEOUT,
    ROOT,
    SwappableHandler,
    git_head,
    negotiate_patiently,
    other_role,
    play_networked,
    start_server,
    wait_for,
)

sys.path.insert(0, str(ROOT / "src"))

from police_thief.domain.audit import audit_disclosure  # noqa: E402
from police_thief.domain.negotiation import build_terms  # noqa: E402
from police_thief.infra.http_transport import McpHttpTransport  # noqa: E402
from police_thief.infra.mcp_client import PeerClient  # noqa: E402
from police_thief.services.inbound import InboundHandler  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402
from police_thief.shared.config import ConfigManager  # noqa: E402
from police_thief.shared.interop import negotiate_extras, terms_from_contract  # noqa: E402


def play_round(n: int, role: str, peer_url: str, group_id: str,
               handler_box: SwappableHandler) -> dict:
    """Negotiate, play and mutually audit one round; return its summary row."""
    expect_role = other_role(role)
    config = ConfigManager.load(role)
    contract = config.contract
    our_terms = terms_from_contract(contract)
    our_extras = negotiate_extras(role, sub_game_number=n)
    handler = InboundHandler(our_terms=our_terms, our_extras=our_extras,
                             expect_role=expect_role, reorder_window=4)
    handler_box.current = handler

    matchrt = MatchRuntime(config, game_id="local-series", sub_game=n,
                           github_commit=git_head())
    client = PeerClient(McpHttpTransport(peer_url), contract.network, contract.rate_limiter)

    print(f"\n[{role}] === round {n}: we are {role} ===")
    greeting = build_terms(config, peer_id=group_id, games_played=0, sub_game=n,
                           step0_commit=matchrt.step0_commit)
    try:
        negotiate_patiently(client, greeting,
                            announce=lambda message: print(f"[{role}] {message}"))
        wait_for(lambda: handler.opponent_terms, NEGOTIATE_WAIT_TIMEOUT,
                f"opponent's greeting for round {n}")
        print(f"[{role}] negotiated OK with {handler.opponent_terms.get('group_id')}")

        play_networked(role, matchrt, client, handler)
        outcome_type = (matchrt.result or {}).get("type", "undecided")
        print(f"[{role}] settled: {outcome_type} after {matchrt.view.step} steps")

        disclosure = matchrt.disclosure()
        client.submit_audit(disclosure)
    finally:
        client.close()  # one held session per sub-game, never one per series
    their_disclosure = wait_for(lambda: handler.audit, NEGOTIATE_WAIT_TIMEOUT,
                               f"opponent's audit disclosure for round {n}")
    report = audit_disclosure(their_disclosure, contract, **matchrt.audit_evidence())
    print(f"[{role}] audit of opponent's disclosure: {report.verdict}"
         + ("" if report.passed else f" - {report.violations}"))

    points = matchrt.points() if report.passed else 0
    print(f"[{role}] round {n} result: {matchrt.result} | points {points}")
    return {"round": n, "role": role, "result": outcome_type, "points": points,
           "audit_passed": report.passed}


def main() -> None:
    """Parse the command line and play one local two-process match."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-role", required=True, choices=["police", "thief"],
                       help="role played in round 1; alternates every round after")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--peer", required=True, help="opponent's MCP URL")
    parser.add_argument("--group-id", default="local-self")
    parser.add_argument("--rounds", type=int, default=6)
    args = parser.parse_args()

    handler_box = SwappableHandler()
    start_server(handler_box, args.port)
    print(f"serving on 127.0.0.1:{args.port}/mcp ; opponent at {args.peer}")
    time.sleep(1.0)  # let our own server bind before the first greeting

    rows = []
    role = args.start_role
    for n in range(1, args.rounds + 1):
        rows.append(play_round(n, role, args.peer, args.group_id, handler_box))
        role = other_role(role)

    total = sum(row["points"] for row in rows)
    print(f"\n[{args.start_role}] === series over: {args.rounds} rounds, "
         f"total points {total} ===")
    for row in rows:
        tag = "OK" if row["audit_passed"] else "TAMPERED"
        print(f"  round {row['round']:>2} as {row['role']:<6} -> {row['result']:<10} "
             f"points={row['points']:<3} audit={tag}")


if __name__ == "__main__":
    main()
