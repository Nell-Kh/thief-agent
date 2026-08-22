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

from _series_lib import (
    FIRST_TURN_BOUNDARY_SECONDS,
    NEGOTIATE_WAIT_TIMEOUT,
    ROOT,
    TURN_WAIT_TIMEOUT,
    SwappableHandler,
    git_head,
    negotiate_patiently,
    other_role,
    play_networked,
    score_for,
    wait_for,
)
from _series_row import (  # noqa: E402
    keep_opponent_disclosure,
    now_iso,
    score_row,
    write_sub_game_files,
)

sys.path.insert(0, str(ROOT / "src"))

from police_thief.domain.audit import audit_disclosure  # noqa: E402
from police_thief.domain.negotiation import build_terms, model_advisories  # noqa: E402
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


def turn_wait_for(config: ConfigManager, args) -> float:
    """How long the opponent gets for one turn, from the contract we both signed.

    ``[network].turn_timeout_seconds`` is the rulebook's own field and ours reads
    180. The driver used to wait 60 regardless, which is not a safety margin but
    a contradiction: we abandoned peers who were inside the deadline we had
    published to them. ``--turn-wait`` overrides it upward when an opponent
    declares a longer one than we do.
    """
    declared = float(config.private_value("network", "turn_timeout_seconds",
                                          TURN_WAIT_TIMEOUT))
    return max(declared, float(getattr(args, "turn_wait", 0.0) or 0.0))


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
        # The CONFIGURED dialect, not the module default: our_extras is the
        # object an opponent's declaration is refused against, so a scope we
        # announce in the greeting but omit here would refuse our own partner.
        our_extras=negotiate_extras(role, n, config.interop),
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
        # Anything still staged is for THIS sub-game or older - the opponent
        # arrived late and we built our own handler instead of promoting it.
        # Leaving it armed lets a later boundary race promote a dead handler
        # over the live one (najamjad, 2026-08-16, sub-game 2).
        handler_box.pending = None

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


def greeting_wait(args) -> float:
    """How long to wait for the opponent's greeting/first turn/audit to arrive.

    The fixed 180s was fine against a peer that runs BOTH roles concurrently,
    but uoh-ay26 run ONE sequential driver that plays g01..g06 in order, so
    their other-role endpoint is reachable-but-not-playing until their driver
    reaches that sub-game. Our rule-1 split runs two processes that race ahead
    independently, so our g04 greeting-wait expired at 180s while their driver
    was still on g03 - exactly the technical_loss G010 g04 took.

    We floor this at :data:`FIRST_TURN_BOUNDARY_SECONDS`, the boundary window
    the opponent declared, so a sequential peer has room to arrive at our window
    no matter what ``--wait`` is. Coupling this to ``--wait`` alone was itself a
    bug: ``--wait`` defaults to 120, so ``max(180, --wait)`` gave a 180s window
    unless the operator remembered to pass a big ``--wait`` - and the g03 wait
    on 2026-08-22 collapsed to 180s and would have timed out their 1200s
    boundary crossing. ``--first-turn-wait`` raises the floor further for a peer
    that declares a longer one; ``--wait`` still counts, for the genuinely-late
    case. A peer that is really gone still becomes a contained loss, only later.
    """
    return max(NEGOTIATE_WAIT_TIMEOUT, FIRST_TURN_BOUNDARY_SECONDS,
               float(getattr(args, "first_turn_wait", 0.0) or 0.0),
               float(getattr(args, "wait", 0.0) or 0.0))


def _play(n: int, role: str, args, ids: tuple[str, str], us: str, handler: InboundHandler,
          handler_box: SwappableHandler, matchrt: MatchRuntime, client: PeerClient,
          artifacts: Path, links: dict[str, Any], recipient: str,
          contract, config) -> dict[str, Any]:
    """The sub-game itself, once the handler, runtime and client are wired."""
    game_id, game_uid = ids
    expect_role = other_role(role)
    our_terms = terms_from_contract(contract)
    print(f"\n=== sub-game {n}: we are {role} (opponent {expect_role}) ===")
    print(f"  dialling their {expect_role} at {peer_url_for(args, role)}")
    negotiate_patiently(
        client,
        {**build_terms(config, peer_id=us, games_played=args.games_played,
                       sub_game=n, step0_commit=matchrt.step0_commit,
                       git_commit_hash=git_head()),
         "game_uid": ids[1], "game_id": ids[0]},
        wait_seconds=args.wait,
        announce=lambda message: print(f"  {message}"),
    )
    wait_for(lambda: handler.opponent_terms, greeting_wait(args),
             f"opponent's greeting for sub-game {n}",
             announce=lambda message: print(message))
    their_group = handler.opponent_terms.get("group_id")
    if their_group != args.opponent_group_id:
        raise RuntimeError(f"sub-game {n}: opponent declared group_id {their_group!r}, "
                           f"expected {args.opponent_group_id!r} - check --opponent-group-id")
    print(f"  negotiated OK with {their_group} (role {handler.opponent_terms.get('role')})")
    handler_box.opponent_games_played = handler.opponent_games_played
    for note in model_advisories(handler.opponent_terms,
                                 negotiate_extras(role, n, config.interop)):
        print(f"  note: {note}")  # a difference nobody is told about is one nobody fixes

    started_at = now_iso()
    turn_wait = turn_wait_for(config, args)
    first_turn_wait = greeting_wait(args)
    # State BOTH windows. The old line printed only ``turn_wait`` (180s), while
    # the code silently waited ``first_turn_wait`` for the first turn - so an
    # operator watching g03 saw "180s", saw nothing happen, and killed a wait
    # that was working (2026-08-22). The first turn is the boundary crossing;
    # every turn after it gets the contract's per-turn deadline.
    print(f"  allowing the opponent up to {first_turn_wait:.0f}s for their FIRST turn "
          f"(crossing their sub-game boundary), then {turn_wait:.0f}s per turn after")
    play_networked(role, matchrt, client, handler, turn_wait=turn_wait,
                   first_turn_wait=first_turn_wait,
                   announce=lambda message: print(message))
    outcome_type = (matchrt.result or {}).get("type", "undecided")
    print(f"  settled locally: {outcome_type} after {matchrt.steps} steps"
          f" (our own move count: {matchrt.view.step})")
    how = (matchrt.result or {}).get("how")
    if how:
        print(f"    reason: {how}")  # the rule that decided it - never fly blind again

    _stage_next_handler(n, role, args, config, handler_box)
    ours = matchrt.disclosure()
    ack = client.submit_audit(ours)
    # Print what they said back. najamjad reported "AUDIT SKIPPED, we received
    # nothing" for three sub-games we had demonstrably sent (rules 18-20 make
    # that an accusation, not a nitpick) - and neither side could prove it,
    # because a successful send left no trace on either log. The reply is the
    # evidence: theirs, in their words, next to the record count we sent.
    print(f"  sent our disclosure ({len(ours['records'])} records, "
          f"sender={ours['sender']}) -> peer replied {ack!r}")  # noqa: E501
    theirs = wait_for(lambda: handler.audit, greeting_wait(args),
                      f"opponent's audit disclosure for sub-game {n}",
                      announce=lambda message: print(message))
    report = audit_disclosure(theirs, contract, **matchrt.audit_evidence())
    print(f"  our audit of their disclosure: {report.verdict}"
          + ("" if report.passed else f" - {report.violations}"))
    keep_opponent_disclosure(artifacts, game_id, n, report.verdict, theirs)
    row = score_row(
        n=n, role=role, expect_role=expect_role, us=us, opponent=args.opponent_group_id,
        outcome_type=outcome_type, passed=report.passed, steps=matchrt.steps,
        tokens=matchrt.ledger.total, our_commit=git_head(), their_disclosure=theirs,
        started_at=started_at, game_id=game_id,
        scores=(score_for(contract, outcome_type, role),
                score_for(contract, outcome_type, expect_role)),
    )
    write_sub_game_files(
        artifacts=artifacts, game_uid=game_uid, game_id=game_id, n=n, terms=our_terms,
        links=links, recipient=recipient, counted=args.counted,
        summary={"sub_game_number": n, "role": role, "result": outcome_type,
                 "steps": matchrt.steps, "opponent_group_id": their_group},
        records=matchrt.book.records,
    )
    return row
