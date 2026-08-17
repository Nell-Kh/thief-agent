"""Rule 9.3: a counted series reports itself, and a friendly never does.

The rulebook is unusually blunt about this one:

    At the end of every legal game against an opposing team there is no longer
    room for human intervention in reporting. Each of the two teams is
    programmed to send by itself - each team separately - an automatic summary
    message to the lecturer via the Gmail API; it is not enough that only one
    side sends.                                                       (ch. 9.3)

with the acceptance checklist adding the penalty: a side that did not send a
report is not credited. Our driver used to mail nothing at all - a deliberate
safety choice after we nearly reported a rehearsal to the lecturer, but not one
the rulebook permits for a league game.

Both halves of the split are load-bearing and both are pinned here, because
each protects against the *other's* failure mode: a counted series that does
not send scores zero, and a friendly that does send is an unrecoverable
embarrassment addressed to the lecturer. Neither is caught by reading the code.

The Gmail layer itself is not exercised - these tests never authorize anything.
The question under test is purely *whether the sender is reached*, so the sender
is replaced by a recorder, which is also what makes the tests safe to run on a
machine that holds real credentials.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _series_report  # noqa: E402

LEAGUE = "rmisegal+uoh26finalgame@gmail.com"


def result(counted: bool, reason: str = "") -> dict:
    """A minimal result payload carrying only the league gate under test."""
    return {"game_id": "them-vs-yanell11-counted-1",
            "league": {"counted": counted, "reason": reason}}


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Replace the real send with a recorder; nothing authorizes or leaves."""
    calls: list[dict] = []

    def record(payload, *, recipient, mode):
        """Stand in for the Gmail send, recording what it was asked to do."""
        calls.append({"payload": payload, "recipient": recipient, "mode": mode})
        return "sent id=recorded"

    monkeypatch.setattr(_series_report, "send_result", record)
    return calls


def test_a_counted_series_reports_itself_with_no_human_step(sent, tmp_path) -> None:
    """The rule itself: armed and counted, so the driver sends before it exits."""
    _series_report.auto_report(result(True), tmp_path, LEAGUE, announce=lambda _m: None)
    assert len(sent) == 1
    assert sent[0]["recipient"] == LEAGUE
    assert sent[0]["mode"] == "send", "a draft is not a report (rule #32)"


def test_a_friendly_never_sends_whatever_the_recipient_says(sent, tmp_path) -> None:
    """The safety half: an uncounted gate stops the send even at the league address."""
    _series_report.auto_report(result(False, "friendly"), tmp_path, LEAGUE,
                               announce=lambda _m: None)
    assert sent == []


def test_a_counted_claim_that_did_not_arm_does_not_send_either(sent, tmp_path) -> None:
    """The gate has already decided; this function never second-guesses it."""
    _series_report.auto_report(result(False, "recipient mismatch"), tmp_path, LEAGUE,
                               announce=lambda _m: None)
    assert sent == []


def test_a_friendly_is_told_how_to_report_by_hand(tmp_path) -> None:
    """Silence would read as 'reported'. The manual command is named instead."""
    said: list[str] = []
    _series_report.auto_report(result(False, "friendly"), tmp_path, LEAGUE, announce=said.append)
    assert any("mail_result.py" in line for line in said)


def test_a_failed_send_is_fatal_and_names_the_recovery(monkeypatch, tmp_path) -> None:
    """An unreported counted series scores zero, so it must not exit successfully."""
    def explode(payload, *, recipient, mode):
        """A send that fails the way a dead OAuth token fails."""
        raise RuntimeError("token expired")

    monkeypatch.setattr(_series_report, "send_result", explode)
    with pytest.raises(SystemExit) as failure:
        _series_report.auto_report(result(True), tmp_path, LEAGUE, announce=lambda _m: None)
    message = str(failure.value)
    assert "NOT REPORTED" in message
    assert "mail_result.py" in message, "the operator must be told how to finish by hand"
    assert str(tmp_path) in message, "and where the artifacts they still have are"


def test_a_counted_series_refuses_to_start_on_a_machine_that_cannot_report(
    monkeypatch, tmp_path
) -> None:
    """The check moved to kickoff, where the answer is free.

    Automatic reporting means the machine that PLAYS must SEND. Discovering at
    the end of six sub-games that Appendix A's client is on the other laptop is
    a rule #35 zero that was decided in the first second.
    """
    monkeypatch.chdir(tmp_path)
    assert _series_report.reporting_blockers(True), "no credentials here - must block"
    assert _series_report.reporting_blockers(False) == [], "a friendly never reports"


def test_a_machine_holding_the_credentials_is_not_blocked(monkeypatch, tmp_path) -> None:
    """The other side of the gate: Appendix A present, counted series allowed."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "credentials.json").write_text("{}", encoding="utf-8")
    assert _series_report.reporting_blockers(True) == []
