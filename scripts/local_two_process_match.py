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

``--config-dir`` points both sides at an alternate ``config/`` tree, so a
brain can be rehearsed without editing the shipped one (and without failing
the gate in ``tests/integration/test_strategy_selection.py``, which pins what
we actually ship). Both processes must pass the SAME directory: the contract
inside it is a signed term, and two different trees refuse at the handshake.

The series closes with its token ledger. The template provider costs zero, so
a run without ``ANTHROPIC_API_KEY`` legitimately reports 0 - that measures the
ledger, not what a real series costs.
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
from _series_subgame import build_handler, load_config  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))

from police_thief.domain.audit import audit_disclosure  # noqa: E402
from police_thief.domain.negotiation import build_terms  # noqa: E402
from police_thief.infra.http_transport import McpHttpTransport  # noqa: E402
from police_thief.infra.mcp_client import PeerClient  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402


def play_round(n: int, role: str, args, handler_box: SwappableHandler) -> dict:
    """Negotiate, play and mutually audit one round; return its summary row."""
    config = load_config(role, args)
    contract = config.contract
    promoted = handler_box.current
    if promoted is not None and promoted.declared_sub_game == n:
        # Already bound for this round: pre-bound before the socket opened
        # (round 1) or promoted when the other process greeted early at a
        # boundary. Either way it may already hold that greeting, and a fresh
        # handler would drop it and then wait 180s for one nobody will resend.
        handler = promoted
        if n > 1:
            print(f"[{role}] reusing the handler promoted for round {n}")
    else:
        handler = build_handler(config, role, n)
        handler_box.current = handler

    matchrt = MatchRuntime(config, game_id="local-series", sub_game=n,
                           github_commit=git_head())
    transport = McpHttpTransport(args.peer, timeout=contract.network.response_timeout_sec)
    client = PeerClient(transport, contract.network, contract.rate_limiter)

    print(f"\n[{role}] === round {n}: we are {role} ===")
    greeting = build_terms(config, peer_id=args.group_id, games_played=0, sub_game=n,
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

        if n < args.rounds:
            # Arm round n+1 before our audit goes out: the other process greets
            # the next round the instant it holds ours, while we are still
            # auditing theirs, and the box promotes this on the resulting
            # sub-game mismatch instead of refusing a greeting that is correct.
            handler_box.pending = build_handler(config, other_role(role), n + 1)
        disclosure = matchrt.disclosure()
        client.submit_audit(disclosure)
    finally:
        # One session per sub-game, closed with it. The session lives on the
        # transport, not the client - closing the wrong object here kills this
        # process mid-round and takes the opponent's audit delivery with it.
        transport.close()
    their_disclosure = wait_for(lambda: handler.audit, NEGOTIATE_WAIT_TIMEOUT,
                               f"opponent's audit disclosure for round {n}")
    report = audit_disclosure(their_disclosure, contract, **matchrt.audit_evidence())
    print(f"[{role}] audit of opponent's disclosure: {report.verdict}"
         + ("" if report.passed else f" - {report.violations}"))

    points = matchrt.points() if report.passed else 0
    print(f"[{role}] round {n} result: {matchrt.result} | points {points}")
    return {"round": n, "role": role, "result": outcome_type, "points": points,
           "audit_passed": report.passed, "tokens": matchrt.ledger.summary(),
           "brain": type(matchrt.brain).__name__, "steps": matchrt.view.step}


def token_report(rows: list[dict], budget: int) -> list[str]:
    """Series token consumption, per round and in total, as printable lines.

    One ledger per round (each is created with the whole-series budget), so the
    series figure is their sum - never any single round's ``remaining``.
    """
    spent = sum(row["tokens"]["total_tokens"] for row in rows)
    calls = sum(row["tokens"]["calls"] for row in rows)
    providers: dict[str, int] = {}
    for row in rows:
        for name, used in row["tokens"]["by_provider"].items():
            providers[name] = providers.get(name, 0) + used
    share = f"{100 * spent / budget:.2f}% of" if budget else "against no"
    lines = ["", f"=== tokens: {spent} in {calls} model call(s), "
                 f"{share} the {budget}/series budget ==="]
    for name, used in sorted(providers.items()):
        lines.append(f"  provider {name:<12} {used:>8} tokens")
    if not providers:
        lines.append("  no model call was made - the verbal layer ran on templates")
    for row in rows:
        lines.append(f"  round {row['round']:>2} {row['tokens']['total_tokens']:>8} tokens"
                     f" in {row['tokens']['calls']:>3} call(s)")
    return lines


def main() -> None:
    """Parse the command line and play one local two-process match."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-role", required=True, choices=["police", "thief"],
                       help="role played in round 1; alternates every round after")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--peer", required=True, help="opponent's MCP URL")
    parser.add_argument("--group-id", default="local-self")
    parser.add_argument("--rounds", type=int, default=6)
    parser.add_argument("--config-dir", default="",
                       help="alternate config/ tree; BOTH sides must pass the same one")
    args = parser.parse_args()

    handler_box = SwappableHandler()
    # Bind round 1 BEFORE the socket opens. The other process is usually
    # already retrying by the time we start, so its greeting lands on the first
    # millisecond the port answers - ahead of the sleep below, let alone the
    # first round. An unbound box answers "peer is booting", which is retryable
    # by design but prints a traceback in a rehearsal that has not begun yet.
    handler_box.current = build_handler(load_config(args.start_role, args),
                                        args.start_role, 1)
    start_server(handler_box, args.port)
    print(f"serving on 127.0.0.1:{args.port}/mcp ; opponent at {args.peer}")
    time.sleep(1.0)  # let our own server bind before the first greeting

    rows = []
    role = args.start_role
    for n in range(1, args.rounds + 1):
        rows.append(play_round(n, role, args, handler_box))
        role = other_role(role)

    total = sum(row["points"] for row in rows)
    print(f"\n[{args.start_role}] === series over: {args.rounds} rounds, "
         f"total points {total} ===")
    for row in rows:
        tag = "OK" if row["audit_passed"] else "TAMPERED"
        print(f"  round {row['round']:>2} as {row['role']:<6} -> {row['result']:<10} "
             f"@{row['steps']:<3} points={row['points']:<3} audit={tag} "
             f"brain={row['brain']}")
    budget = load_config(args.start_role, args).contract.network.token_budget_per_series
    print("\n".join(token_report(rows, budget)))


if __name__ == "__main__":
    main()
