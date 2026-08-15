"""One counted/friendly sub-game: negotiate, play, audit, score the row.

Split from ``friendly_series.py`` under the 150-line rule. Everything here
happens against a real opponent over the wire, so every step that can disagree -
the greeting, the group id, the mutual audit - is checked rather than assumed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _series_lib import (  # noqa: E402
    NEGOTIATE_WAIT_TIMEOUT,
    ROOT,
    SwappableHandler,
    git_head,
    negotiate_patiently,
    other_role,
    play_networked,
    score_for,
    wait_for,
)

sys.path.insert(0, str(ROOT / "src"))

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


def load_config(role: str, args) -> ConfigManager:
    """Load ``role``'s configuration, honouring an explicit ``--config-dir``."""
    return ConfigManager.load(role, args.config_dir) if args.config_dir \
        else ConfigManager.load(role)


def peer_url_for(args, our_role: str) -> str:
    """The opponent endpoint to dial this sub-game.

    A role-split opponent (one process and one tunnel per role - sharNamr,
    2026-08-15) is dialled at its THIEF address exactly when WE are police;
    a single-endpoint opponent leaves ``--peer-thief`` empty and both roles
    resolve to ``--peer``.
    """
    thief_url = getattr(args, "peer_thief", "") or ""
    return thief_url if (thief_url and our_role == "police") else args.peer


def build_handler(config: ConfigManager, role: str, n: int) -> InboundHandler:
    """The inbound handler for sub-game ``n`` played as ``role``.

    One construction site, because three callers need an identical handler at
    three different moments: the sub-game itself, the next sub-game staged at
    a boundary, and sub-game 1 bound before the socket opens.
    """
    return InboundHandler(
        our_terms=terms_from_contract(config.contract),
        our_extras=negotiate_extras(role, n),
        expect_role=other_role(role),
        reorder_window=4,
    )


def play_sub_game(n: int, role: str, args, ids: tuple[str, str], us: str,
                  handler_box: SwappableHandler, artifacts: Path,
                  links: dict[str, Any], recipient: str) -> dict[str, Any]:
    """Negotiate, play and mutually audit one sub-game; return its result row."""
    game_id, game_uid = ids
    config = load_config(role, args)
    contract = config.contract
    promoted = handler_box.current
    if promoted is not None and promoted.declared_sub_game == n:
        # Already bound for this sub-game: either pre-bound before the socket
        # opened (sub-game 1) or promoted when the opponent greeted early at a
        # boundary. Either way an opening greeting may already be inside it,
        # and a fresh handler would drop it and then wait 180s for a greeting
        # nobody is going to send again.
        handler = promoted
        if n > 1:
            print(f"  reusing the handler promoted for sub-game {n} (early greeting captured)")
    else:
        handler = build_handler(config, role, n)
        handler_box.current = handler

    matchrt = MatchRuntime(config, game_id=game_id, sub_game=n, github_commit=git_head())
    transport = McpHttpTransport(peer_url_for(args, role),
                                 timeout=contract.network.response_timeout_sec)
    client = PeerClient(transport, contract.network, contract.rate_limiter,
                        turn_patience_sec=getattr(args, "turn_patience", 0.0))
    try:
        return _play(n, role, args, ids, us, handler, handler_box, matchrt, client,
                     artifacts, links, recipient, contract, config)
    finally:
        # One session per sub-game, closed with it: the audited sub-game has no
        # further use for its tunnel, and a leaked one outlives the series.
        transport.close()


def _stage_next_handler(n: int, role: str, args, config: ConfigManager,
                        handler_box: SwappableHandler) -> None:
    """Arm the next sub-game's handler so a boundary greeting is not refused.

    The opponent may greet sub-game n+1 the instant it holds our audit for n,
    while this side is still auditing theirs and writing artifacts. Sub-game n's
    handler then refuses that greeting - correctly, on its own terms - and a
    driver that treats a refusal as fatal (the kit's does, and it is right to:
    no amount of waiting fixes a real mismatch) loses the series on a race.
    :class:`SwappableHandler` promotes ``pending`` on exactly that mismatch, so
    the greeting is answered as the sub-game it actually names.

    Staged HERE, not at the top of the sub-game: while the match is live, a
    mismatch is far likelier to be a genuine disagreement than a boundary race,
    and promoting on it would abandon a sub-game in progress. After our own
    settlement there is nothing left of n to protect.
    """
    if n >= args.rounds:
        return  # no n+1 to stage; a stale pending would outlive the series
    handler_box.pending = build_handler(config, other_role(role), n + 1)


def _play(n: int, role: str, args, ids: tuple[str, str], us: str, handler: InboundHandler,
          handler_box: SwappableHandler, matchrt: MatchRuntime, client: PeerClient,
          artifacts: Path, links: dict[str, Any], recipient: str,
          contract, config) -> dict[str, Any]:
    """The sub-game itself, once the handler, runtime and client are wired."""
    game_id, game_uid = ids
    expect_role = other_role(role)
    our_terms = terms_from_contract(contract)
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
    how = (matchrt.result or {}).get("how")
    if how:
        print(f"    reason: {how}")  # the rule that decided it - never fly blind again

    _stage_next_handler(n, role, args, config, handler_box)
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
