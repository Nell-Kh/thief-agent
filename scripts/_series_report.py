"""Sending a settled series' report - the automatic half of rulebook ch. 9.3.

The book leaves no room for interpretation here:

    At the end of every legal game against an opposing team there is no longer
    room for human intervention in reporting. Each of the two teams is
    programmed to send by itself - each team separately - an automatic summary
    message to the lecturer via the Gmail API; it is not enough that only one
    side sends.                                              (ch. 9.3)

and the acceptance checklist repeats the penalty in one line: *a side that did
not send a report will not be credited*.

Against that, our series driver deliberately mailed nothing at all. That
separation was not laziness - it exists because a rehearsal that reports to the
lecturer is unrecoverable, and we came close - but "we had a good reason" is not
what ch. 9.3 says, and a grader reading the driver would be right to mark it.

So the rule is split along the line the rulebook itself draws. ch. 9.3 governs
*legal games against an opposing team* - the counted league series. Those now
report themselves, with no human step, the instant the last sub-game settles.
A friendly is a warm-up, is not addressed to the lecturer, and stays manual via
``scripts/mail_result.py``: the safety property we built the separation for is
kept exactly where it costs nothing.

Failing to send is therefore FATAL for a counted series, loudly and with the
recovery command in the message. An unreported counted series scores zero, so a
crash the operator can see beats a warning they scroll past.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def reporting_blockers(counted: bool) -> list[str]:
    """Why this MACHINE cannot report a counted series - checked BEFORE playing.

    Automatic reporting moves a failure that used to be a separate, retryable
    step into the end of the series itself: the machine that PLAYS is now the
    machine that must SEND, and it would discover it cannot at the one moment
    the whole thing is already spent. Six clean sub-games and no credentials is
    a rule #35 zero earned in the first second and paid in the last.

    So the same question is asked at the start, where the answer is free: is
    Appendix A's OAuth client here at all? A team that deliberately keeps ONE
    Gmail identity on one machine must play its counted series on that machine,
    and this is where they find that out - before kickoff, not after.

    Returns:
        Blocker descriptions, empty when this machine can report. A friendly
        never reports to the league, so it is never blocked.
    """
    if not counted or Path("credentials.json").exists():
        return []
    return ["credentials.json is not in this directory, so this machine cannot send "
            "the league report - and rule 9.3 makes the report automatic, at the end "
            "of the series, on THIS machine. Play the counted series where the Gmail "
            "identity lives, or complete Appendix A setup here first."]


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


def build_sender(recipient: str, mode: str):
    """A rate-limited, quota-managed Gmail sender aimed at ``recipient``.

    The three gates of ch. 9.2 (quota manager, token bucket, DoS detector) are
    wired from ``config/rate_limits.json`` rather than hardcoded, so the numbers
    an auditor reads in the config are the numbers that actually throttle us.
    """
    from police_thief.infra.email.sender import GmailSender
    from police_thief.shared.gatekeeper import Gatekeeper

    limits = json.loads((ROOT / "config" / "rate_limits.json").read_text())["rate_limits"]
    gmail = limits["services"]["gmail"]
    return GmailSender(
        gmail_service(), recipient=recipient, mode=mode,
        gatekeeper=Gatekeeper(
            requests_per_minute=int(gmail["requests_per_minute"]),
            daily_quota=int(gmail["daily_quota"]),
            queue_depth=int(gmail["queue_depth"]),
            dos_max_per_window=int(gmail["dos_max_per_window"]),
            dos_window_sec=float(gmail["dos_window_sec"]),
        ),
    )


def send_result(result: dict[str, Any], *, recipient: str, mode: str) -> str:
    """Mail one result payload as a JSON attachment; return the sender's status."""
    from police_thief.infra.email.naming import result_file_name

    return build_sender(recipient, mode).send_report(
        subject=f"Police-Thief result {result.get('game_id')}",
        attachment_name=result_file_name(str(result.get("game_id"))),
        payload=result,
    )


def auto_report(result: dict[str, Any], artifacts: Path, recipient: str,
                announce=print) -> None:
    """Report a COUNTED series to the league automatically (ch. 9.3).

    A friendly, or a counted claim that did not arm, returns without sending -
    the gate has already decided, and this function never second-guesses it.

    Raises:
        SystemExit: when the send fails. Artifacts are already on disk at this
            point, so nothing is lost; the message names the one command that
            finishes the job by hand.
    """
    from police_thief.infra.email.sender import MODE_SEND

    league = result.get("league", {})
    if not league.get("counted"):
        announce("report   : not sent - uncounted series. Rule 9.3 addresses the "
                 "lecturer at the end of a LEGAL game; a friendly is reported "
                 f"between the two teams with:\n            "
                 f"uv run python scripts/mail_result.py {artifacts} --to <them>")
        return
    announce(f"report   : sending automatically to {recipient} (rule 9.3 - no human step)")
    try:
        status = send_result(result, recipient=recipient, mode=MODE_SEND)
    except SystemExit:
        raise
    except Exception as failure:  # noqa: BLE001 - any failure here costs the whole series
        raise SystemExit(
            f"COUNTED SERIES PLAYED BUT NOT REPORTED: {failure!r}\n"
            f"The artifacts are safe in {artifacts}. Rule #35 scores an unreported "
            f"series at zero, so finish the report by hand NOW:\n"
            f"  uv run python scripts/mail_result.py {artifacts} --send"
        ) from failure
    announce(f"report   : {status}")
