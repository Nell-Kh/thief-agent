"""M7 end-to-end shell run: play, write the lifecycle files, mail the report.

Plays one local mini-game, assembles the four lifecycle JSON files under
``results/`` in the league's joined shape (uid derived from the negotiated
terms, settlement hash inline), and mails the result through the gated Gmail
pipeline - a local stub receives the identical bytes without credentials. The
league fields ride DISARMED: a demo is not a counted series (rules 37-38).
"""

from __future__ import annotations

import datetime
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from police_thief.constants import ROLE_POLICE, ROLE_THIEF
from police_thief.domain.logbook import Logbook
from police_thief.infra.email.naming import (
    config_file_name,
    declaration_file_name,
    result_file_name,
    write_lifecycle_file,
)
from police_thief.infra.email.report_blocks import group_block, links_block
from police_thief.infra.email.reports import (
    config_payload,
    declaration_payload,
    log_payload,
    result_payload,
)
from police_thief.infra.email.sender import configured_sender
from police_thief.services.runtime import runner_from_config
from police_thief.shared.config import ConfigManager
from police_thief.shared.interop import derive_game_ids, terms_from_contract
from police_thief.shared.sysinfo import hardware_spec

OPPONENT = "self-play-opponent"  # a demo double, declared as such - never a real rival's name


def git_head() -> str:
    """The exact commit playing this game (rulebook ch. 5.5)."""
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return out.stdout.strip() or "uncommitted"


def stub_service() -> SimpleNamespace:
    """A Gmail double for machines without credentials - same call shape."""
    def request(kind: str) -> SimpleNamespace:
        """A stub Gmail request object that only reports what it was asked to do."""
        return SimpleNamespace(execute=lambda: print(f"  [stub gmail] {kind} accepted"))

    # ``userId`` mirrors the real Gmail API keyword, hence the noqa.
    drafts = SimpleNamespace(create=lambda userId, body: request("draft"))  # noqa: N803
    messages = SimpleNamespace(send=lambda userId, body: request("send"))  # noqa: N803
    return SimpleNamespace(users=lambda: SimpleNamespace(drafts=lambda: drafts,
                                                         messages=lambda: messages))


def real_or_stub_service() -> SimpleNamespace:
    """Real Gmail when Appendix A setup exists here; otherwise the stub."""
    if Path("credentials.json").exists():
        from police_thief.infra.email.oauth import build_gmail_service, load_credentials

        return build_gmail_service(load_credentials())
    print("no credentials.json here - using the stub service (pipeline unchanged)")
    return stub_service()


def main() -> None:
    """One demo mini-game, the lifecycle files, one gated (uncounted) report."""
    config = ConfigManager.load(ROLE_POLICE)
    state = runner_from_config(config).play()
    outcome = state.outcome
    print(f"mini-game over at step {state.step}: {outcome.event} - {outcome.reason}")

    # The uid MUST derive from the flat negotiated terms (kit SPEC section 6):
    # a uid derived from anything private never matches the opponent's.
    terms = terms_from_contract(config.contract)
    head = git_head()
    us = str(config.private_value("game", "group_id", "team-tbd"))
    game_id, game_uid = derive_game_ids(terms, us, OPPONENT)
    repos = dict(config.private("game").get("repos", {}))
    links = links_block(game_id, github={us: repos, OPPONENT: {}})
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    recipient = str(config.private_value("email", "recipient", ""))
    groups = [
        group_block(
            group_id=us, group_name=str(config.private_value("game", "group_name", us)),
            members=list(config.private("game").get("members", [])), repos=repos,
            mcp_servers={"cop": "http://127.0.0.1:8801/mcp", "thief": "http://127.0.0.1:8802/mcp"},
            llm_model=str(config.private_value("llm", "model", "template")),
            hardware_spec=hardware_spec(), github_commit=head,
            counted_games_played=0, code_version="1.0",
        ),
        group_block(group_id=OPPONENT, group_name=OPPONENT, members=[], repos={},
                    mcp_servers={}, llm_model="template", hardware_spec=hardware_spec(),
                    github_commit=head, counted_games_played=0, code_version="1.0"),
    ]
    book = Logbook(game_id, 1, ROLE_POLICE)
    book.append({"step": state.step, "event": outcome.event, "reason": outcome.reason})
    book.close({"type": outcome.event})
    declaration = declaration_payload(
        game_uid=game_uid, game_id=game_id, links=links, timezone="Asia/Jerusalem",
        started_at=now, num_sub_games=1, groups=groups, counted=False, recipient=recipient,
        max_tokens_per_game=config.contract.network.token_budget_per_series,
    )
    winner = us if outcome.event == "capture" else OPPONENT
    rows = [{
        "sub_game_number": 1, "roles": {us: "police", OPPONENT: "thief"},
        "started_at": now, "ended_at": now, "result": outcome.event,
        "winner_group": winner, "tie": False, "steps": state.step,
        "github_commit": {us: head, OPPONENT: head},
        "tokens": {us: 0, OPPONENT: 0},  # honest: the template provider spends none
        "score": {us: outcome.points_for(ROLE_POLICE), OPPONENT: outcome.points_for(ROLE_THIEF)},
        "log_files": {us: f"log_{game_id}_g01.json", OPPONENT: f"log_{game_id}_g01.json"},
        "audit": {"log_verified": True, "tampered": False},
    }]
    result = result_payload(
        game_uid=game_uid, game_id=game_id, links=links, timezone="Asia/Jerusalem",
        group_ids=[us, OPPONENT], sub_games=rows, tie_score=config.contract.scoring.tie_score,
        games_played={us: 0, OPPONENT: None}, first_meeting=True, counted=False,
        recipient=recipient,
    )
    log = log_payload(game_uid, game_id, 1, links, counted=False, records=book.records,
                      summary={"sub_game_number": 1, "result": outcome.event,
                               "steps": state.step}, recipient=recipient)
    for name, payload in [
        (declaration_file_name(game_id), declaration),
        (config_file_name(game_id, 1), config_payload(game_uid, game_id, 1, terms, links,
                                                      recipient, counted=False)),
        (f"log_{game_id}_g01.json", log),
        (result_file_name(game_id), result),
    ]:
        print(f"  wrote {write_lifecycle_file(Path('results'), name, payload)}")

    sender = configured_sender(config, real_or_stub_service())
    status = sender.send_report(
        subject=f"Police-Thief result {game_id}",
        attachment_name=result_file_name(game_id), payload=result)
    print(f"report -> {sender.recipient} [{sender.mode}]: {status}")
    print(f"gatekeeper log: {sender._gatekeeper.log}")  # noqa: SLF001 - demo introspection


if __name__ == "__main__":
    main()
