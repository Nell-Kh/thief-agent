"""A friendly reports itself to the opponent - and can never reach the lecturer.

nis-yar1 (2026-08-17) proposed that both teams deliver friendly results
automatically, so that neither side can quietly decline to publish a series it
lost. We agreed: a norm that removes the temptation to be selective about
evidence is worth having, and it costs nothing.

What it does cost is the property the manual-friendly design existed to protect.
Until now ``friendly_series.py`` mailed NOTHING, which made "we accidentally
reported a warm-up to the lecturer" structurally impossible rather than merely
unlikely. Arming the driver's own send re-opens that door, and points it at an
address typed on a command line.

So the door is narrowed instead of re-opened: the two league addresses are
refused outright, at parse time, before a single sub-game is played. A typo is
caught while it is still free. And the refusal is a hard exit, not a warning,
because the failure it prevents is the one failure in this project that cannot
be undone by re-running anything.

The asymmetry in what happens AFTER the send is deliberate too, and pinned
below: a counted series that fails to report dies loudly (rule #35 scores it
zero, so exiting successfully would be a lie), while a friendly that fails to
report prints the recovery command and carries on (six settled sub-games are
not worth discarding over an unreachable mailbox).

No test here authorizes anything or touches Gmail; the sender is a recorder,
which is what makes this file safe to run on the machine that holds the real
credentials.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _series_report  # noqa: E402

from police_thief.constants import AGENT_REPORT_ADDRESS, LECTURER_ADDRESS  # noqa: E402

THEM = "yardentziar@gmail.com"
US = "yanalserhan3@gmail.com"


def result(counted: bool, reason: str = "") -> dict:
    """A minimal result payload carrying only the league gate under test."""
    return {"game_id": "nis-yar1-vs-yanell11",
            "league": {"counted": counted, "reason": reason}}


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Replace the real send with a recorder; nothing authorizes or leaves."""
    calls: list[dict] = []

    def record(payload, *, recipient, mode):
        """Stand in for the Gmail send, recording what it was asked to do."""
        calls.append({"recipient": recipient, "mode": mode})
        return "sent id=recorded"

    monkeypatch.setattr(_series_report, "send_result", record)
    return calls


@pytest.mark.parametrize("address", [AGENT_REPORT_ADDRESS, LECTURER_ADDRESS])
def test_a_league_address_can_never_be_a_friendly_recipient(address) -> None:
    """The one accident that cannot be undone by re-running anything."""
    with pytest.raises(SystemExit) as refusal:
        _series_report.friendly_recipients(f"{THEM},{address}")
    assert address in str(refusal.value)


def test_the_refusal_survives_a_change_of_case() -> None:
    """Addresses are case-insensitive; a guard that is not would be decoration."""
    with pytest.raises(SystemExit):
        _series_report.friendly_recipients(AGENT_REPORT_ADDRESS.upper())


def test_ordinary_addresses_parse_into_a_clean_list() -> None:
    """Commas, stray spaces and a trailing comma are all one operator typing fast."""
    assert _series_report.friendly_recipients(f" {THEM} , {US}, ") == [THEM, US]
    assert _series_report.friendly_recipients("") == []


def test_a_friendly_with_recipients_mails_every_one_of_them(sent, tmp_path) -> None:
    """The norm we agreed to: the series publishes itself, with no human step."""
    _series_report.auto_report(result(False, "friendly"), tmp_path, AGENT_REPORT_ADDRESS,
                               announce=lambda _m: None, friendly_to=[THEM, US])
    assert [call["recipient"] for call in sent] == [THEM, US]
    assert {call["mode"] for call in sent} == {"send"}, "a draft is not a delivery"


def test_a_friendly_with_no_recipients_still_sends_nothing(sent, tmp_path) -> None:
    """The old safety property, unchanged where nobody asked for delivery."""
    _series_report.auto_report(result(False, "friendly"), tmp_path, AGENT_REPORT_ADDRESS,
                               announce=lambda _m: None)
    assert sent == []


def test_the_configured_league_recipient_is_not_mailed_by_a_friendly(sent, tmp_path) -> None:
    """``recipient`` is the league address on a counted-ready config; it must not leak.

    The friendly path is handed the SAME ``recipient`` argument the counted path
    reports to. Nothing but the gate keeps them apart, so the gate is tested.
    """
    _series_report.auto_report(result(False, "friendly"), tmp_path, AGENT_REPORT_ADDRESS,
                               announce=lambda _m: None, friendly_to=[THEM])
    assert [call["recipient"] for call in sent] == [THEM]


def test_a_counted_series_ignores_the_friendly_list_entirely(sent, tmp_path) -> None:
    """One series, one report. A counted run must not also spray the opponent."""
    _series_report.auto_report(result(True), tmp_path, AGENT_REPORT_ADDRESS,
                               announce=lambda _m: None, friendly_to=[THEM, US])
    assert [call["recipient"] for call in sent] == [AGENT_REPORT_ADDRESS]


def test_one_unreachable_address_does_not_cost_the_others(monkeypatch, tmp_path) -> None:
    """A dead mailbox is not a reason to withhold the report from a live one."""
    reached: list[str] = []

    def flaky(payload, *, recipient, mode):
        """Fail for the first address only, the way one bad entry in a list does."""
        if recipient == THEM:
            raise RuntimeError("no such mailbox")
        reached.append(recipient)
        return "sent"

    monkeypatch.setattr(_series_report, "send_result", flaky)
    said: list[str] = []
    _series_report.auto_report(result(False, "friendly"), tmp_path, AGENT_REPORT_ADDRESS,
                               announce=said.append, friendly_to=[THEM, US])
    assert reached == [US]
    assert any("mail_result.py" in line and THEM in line for line in said), \
        "the address that failed must come with the command that finishes it"


def test_a_failed_friendly_send_is_not_fatal(monkeypatch, tmp_path) -> None:
    """The asymmetry with rule #35: a friendly is not worth discarding a series over."""
    def explode(payload, *, recipient, mode):
        """A send that fails the way a dead OAuth token fails."""
        raise RuntimeError("token expired")

    monkeypatch.setattr(_series_report, "send_result", explode)
    _series_report.auto_report(result(False, "friendly"), tmp_path, AGENT_REPORT_ADDRESS,
                               announce=lambda _m: None, friendly_to=[THEM])
