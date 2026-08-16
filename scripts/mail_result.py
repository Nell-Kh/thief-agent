"""Mail a played series' result report - the step the series driver leaves to you.

``friendly_series.py`` plays the series and writes the four lifecycle files;
it deliberately does NOT mail anything, so that no rehearsal, demo or slip can
ever report to the league. Reporting is this separate, deliberate step, and
it is the same step for a self-check and for the real thing - only the
recipient differs:

    # 1. Self-check: mail OUR result to OURSELVES and compare it with the
    #    opponent's file field-for-field before anyone reports to the league.
    uv run python scripts/mail_result.py results/friendly_<game_id> --to me@example.com

    # 2. The league report, once both files agree. Requires the TOML's
    #    [email].recipient to be the binding league address; the ``counted``
    #    flag inside the result file must already be true (the series was
    #    played with --counted), or the league gate reads it as a friendly.
    uv run python scripts/mail_result.py results/friendly_<game_id> --send

Without ``--send`` the message is parked in Gmail Drafts (``[email].mode``
default), so a mistaken address costs nothing. Rule #35 punishes a missing
report as heavily as a false one, so the counted runbook is: play with
--counted, verify against the opponent, then run this with --send.

Needs Appendix A's ``credentials.json`` (and the ``token.json`` it mints on
first use) in the working directory; the Gmail account that authorized them is
the sender.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from police_thief.constants import ROLE_POLICE  # noqa: E402
from police_thief.infra.email.naming import result_file_name  # noqa: E402
from police_thief.infra.email.sender import MODE_DRAFT, MODE_SEND, GmailSender  # noqa: E402
from police_thief.shared.config import ConfigManager  # noqa: E402
from police_thief.shared.gatekeeper import Gatekeeper  # noqa: E402


def parse_args() -> argparse.Namespace:
    """The result directory to report, and where and how to mail it."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("artifacts", help="the results/friendly_<game_id> directory")
    parser.add_argument("--to", default="",
                        help="override recipient (a self-check); default: [email].recipient")
    parser.add_argument("--send", action="store_true",
                        help="really send; default parks a draft regardless of the TOML")
    parser.add_argument("--config-dir", default="",
                        help="the config directory the series was played with")
    return parser.parse_args()


def load_result(artifacts: Path) -> tuple[Path, dict]:
    """The single result_*.json in ``artifacts``, parsed.

    Raises:
        SystemExit: when there is not exactly one result file to report.
    """
    files = sorted(artifacts.glob("result_*.json"))
    if len(files) != 1:
        raise SystemExit(f"expected exactly one result_*.json in {artifacts}, found {len(files)}")
    return files[0], json.loads(files[0].read_text(encoding="utf-8"))


def gmail_service():
    """The authorized Gmail service, or a clear failure naming what is missing.

    Raises:
        SystemExit: when Appendix A's credentials are not in the working dir.
    """
    if not Path("credentials.json").exists():
        raise SystemExit("credentials.json not found here - complete Appendix A setup "
                         "(Google Cloud OAuth client) in this directory first")
    from police_thief.infra.email.oauth import build_gmail_service, load_credentials

    return build_gmail_service(load_credentials())


def main() -> None:
    """Load the result, decide recipient and mode out loud, mail it, report status."""
    args = parse_args()
    config = (ConfigManager.load(ROLE_POLICE, args.config_dir) if args.config_dir
              else ConfigManager.load(ROLE_POLICE))
    email_cfg = config.private("email")
    path, result = load_result(Path(args.artifacts))
    recipient = args.to or str(email_cfg["recipient"])
    mode = MODE_SEND if args.send else MODE_DRAFT
    league = result.get("league", {})
    print(f"result   : {path}")
    print(f"game_id  : {result.get('game_id')}   counted: {league.get('counted')} "
          f"({league.get('reason', '')})")
    print(f"to       : {recipient}" + ("   (override - a self-check)" if args.to else ""))
    print(f"mode     : {mode}")
    if mode == MODE_SEND and not args.to and not league.get("counted"):
        print("NOTE: sending an UNCOUNTED result to the configured recipient - "
              "the league reads it as a friendly, which is what it is.")
    limits = json.loads((ROOT / "config" / "rate_limits.json").read_text())["rate_limits"]
    gmail = limits["services"]["gmail"]
    sender = GmailSender(
        gmail_service(), recipient=recipient, mode=mode,
        gatekeeper=Gatekeeper(
            requests_per_minute=int(gmail["requests_per_minute"]),
            daily_quota=int(gmail["daily_quota"]),
            queue_depth=int(gmail["queue_depth"]),
            dos_max_per_window=int(gmail["dos_max_per_window"]),
            dos_window_sec=float(gmail["dos_window_sec"]),
        ),
    )
    status = sender.send_report(
        subject=f"Police-Thief result {result.get('game_id')}",
        attachment_name=result_file_name(str(result.get("game_id"))),
        payload=result,
    )
    print(f"status   : {status}")


if __name__ == "__main__":
    main()
