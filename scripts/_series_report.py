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

from _series_lib import inclusive_games

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
    """Mail one result payload as a JSON attachment; return the sender's status.

    Raises:
        SystemExit: when Gmail refuses the DRAFT for want of scope. Our OAuth
            client deliberately requests ``gmail.send`` and nothing else, so the
            agent can send a report and cannot read a mailbox - but drafting
            needs ``gmail.compose``, which is strictly broader. The "safe
            rehearsal" every runbook reaches for first is therefore the one path
            our own token cannot walk, and it surfaced as a raw 403 traceback
            twice on 2026-08-17 before anyone read the scope. Naming it costs
            eight lines and saves the same ten minutes every time.
    """
    from police_thief.infra.email.naming import result_file_name

    try:
        return build_sender(recipient, mode).send_report(
            subject=f"Police-Thief result {result.get('game_id')}",
            attachment_name=result_file_name(str(result.get("game_id"))),
            payload=result,
        )
    except Exception as failure:
        if mode != "draft" or "insufficient" not in str(failure).lower():
            raise
        raise SystemExit(
            "Gmail refused the DRAFT: our OAuth client holds gmail.send only, and "
            "drafting needs gmail.compose. This is the scope we chose on purpose - "
            "it is why the agent cannot read your mail. Re-run with --send and an "
            "explicit --to <your own address>, which reaches the same code path the "
            "real report uses."
        ) from failure


def friendly_recipients(raw: str) -> list[str]:
    """The addresses an UNCOUNTED series mails itself to - never a league one.

    nis-yar1 (2026-08-17) asked that both teams deliver friendly results
    automatically, so neither side can quietly decline to publish an unflattering
    one. That is a good norm and costs nothing. What it does cost is the property
    the manual-friendly design was built to protect: the driver's own send now
    aims at an address typed on a command line, and ``rmisegal`` is a short word
    to fat-finger at midnight.

    So both league addresses are refused, and refused HERE - parsed at kickoff,
    where the answer is free - rather than at the end of six settled sub-games
    where the mistake is already in the lecturer's inbox and unrecoverable.

    Raises:
        SystemExit: when a league address appears among the friendly recipients.
    """
    from police_thief.constants import AGENT_REPORT_ADDRESS, LECTURER_ADDRESS

    addresses = [entry.strip() for entry in raw.split(",") if entry.strip()]
    bound = {AGENT_REPORT_ADDRESS.lower(), LECTURER_ADDRESS.lower()}
    forbidden = sorted({a for a in addresses if a.lower() in bound})
    if forbidden:
        raise SystemExit(
            f"REFUSING to arm friendly delivery to a league address: {forbidden}. "
            "A friendly is a warm-up between two teams; ch. 9.3 addresses the "
            "lecturer at the end of a LEGAL game only. Play it --counted, or mail "
            "somebody else."
        )
    return addresses


def _report_friendly(result: dict[str, Any], artifacts: Path,
                     recipients: list[str], announce) -> None:
    """Mail an uncounted series to the opposing team, or say how to do it by hand.

    Deliberately NOT fatal, unlike the counted path directly below: rule #35
    scores an unreported league series at zero, so that one dies rather than
    exit successfully on a silent failure. A friendly carries no such penalty,
    and killing the driver after six settled sub-games would destroy nothing
    except the evening. A failure here therefore prints what broke, names the
    command that finishes the job, and moves to the next address.
    """
    from police_thief.infra.email.sender import MODE_SEND

    if not recipients:
        announce("report   : not sent - uncounted series. Rule 9.3 addresses the "
                 "lecturer at the end of a LEGAL game; a friendly is reported "
                 f"between the two teams with:\n            "
                 f"uv run python scripts/mail_result.py {artifacts} --to <them> --send")
        return
    for address in recipients:
        try:
            status = send_result(result, recipient=address, mode=MODE_SEND)
        except Exception as failure:  # noqa: BLE001 - one bad address must not eat the rest
            announce(f"report   : FAILED to mail the friendly to {address} ({failure!r})\n"
                     f"            uv run python scripts/mail_result.py {artifacts} "
                     f"--to {address} --send")
            continue
        announce(f"report   : friendly result mailed to {address} ({status})")


def auto_report(result: dict[str, Any], artifacts: Path, recipient: str,
                announce=print, friendly_to: tuple[str, ...] | list[str] = ()) -> None:
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
        _report_friendly(result, artifacts, list(friendly_to), announce)
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


def series_result(args, ids, us, links, rows, config, their_games, recipient) -> dict[str, Any]:
    """The one report a finished series produces, built from its rows.

    ``games_played`` is the only field needing care. Ours is inclusive: a
    COUNTED series advances the pairwise counter, a friendly does not (warm-up
    games are not counted). Theirs is what THEY declared on the wire - the
    games before this one - advanced by the same +1 the field name promises;
    never a number we made up, because rule #38 disqualifies whoever filed
    the false declaration, so the base is always theirs.
    """
    from police_thief.infra.email.reports import result_payload

    return result_payload(
        game_uid=ids[1], game_id=ids[0], links=links, timezone=args.timezone,
        group_ids=[us, args.opponent_group_id], sub_games=rows,
        tie_score=config.contract.scoring.tie_score,
        games_played={
            us: args.games_played + (1 if args.counted else 0),
            args.opponent_group_id: inclusive_games(their_games, args.counted),
        },
        first_meeting=args.first_meeting, counted=args.counted, recipient=recipient,
    )
