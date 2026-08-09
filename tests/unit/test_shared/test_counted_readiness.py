"""Tests for the counted-series readiness guard.

The failure this guards against is silent by construction: a misaddressed or
undelivered report plays a perfect series and scores nothing, with no error
anywhere. Both halves were live in this repository at once, which is why the
check is a shared function rather than a line in one driver.
"""

from __future__ import annotations

from police_thief.constants import AGENT_REPORT_ADDRESS, EMAIL_MODE_DRAFT, EMAIL_MODE_SEND
from police_thief.shared.config import ConfigManager
from police_thief.shared.preflight import counted_series_blockers

OTHER_ADDRESS = "yanalserhan3@gmail.com"


def test_the_binding_address_in_send_mode_has_no_blockers() -> None:
    """The one combination that can actually score a league game."""
    assert counted_series_blockers(AGENT_REPORT_ADDRESS, EMAIL_MODE_SEND) == []


def test_a_personal_recipient_is_a_blocker() -> None:
    """Rule #51: a report addressed elsewhere never arms as counted."""
    blockers = counted_series_blockers(OTHER_ADDRESS, EMAIL_MODE_SEND)
    assert len(blockers) == 1
    assert OTHER_ADDRESS in blockers[0]
    assert AGENT_REPORT_ADDRESS in blockers[0]
    assert "rule #51" in blockers[0]


def test_draft_mode_is_a_blocker() -> None:
    """Rule #32: a counted game parked in Drafts is never reported at all."""
    blockers = counted_series_blockers(AGENT_REPORT_ADDRESS, EMAIL_MODE_DRAFT)
    assert len(blockers) == 1
    assert "Drafts" in blockers[0]
    assert "rule #32" in blockers[0]


def test_both_faults_are_reported_together_not_one_at_a_time() -> None:
    """Fixing one and re-running should not surface the other as a surprise."""
    blockers = counted_series_blockers(OTHER_ADDRESS, EMAIL_MODE_DRAFT)
    assert len(blockers) == 2


def test_an_empty_or_missing_recipient_is_a_blocker() -> None:
    """A config with no [email] section must not read as ready."""
    assert counted_series_blockers("", "") != []


def test_every_blocker_names_a_config_key_the_reader_can_act_on() -> None:
    """A guard that only says 'no' costs the same time it was meant to save."""
    for blocker in counted_series_blockers(OTHER_ADDRESS, EMAIL_MODE_DRAFT):
        assert "[email]" in blocker


def test_the_shipped_configs_are_addressed_to_the_league_but_held_in_draft() -> None:
    """The committed resting state: correctly addressed, deliberately undelivered.

    Pins both halves of the decision in 11.1.6 - the address is fixed for good,
    and ``draft`` is the default so no demo or sparring run can mail the
    lecturer. A counted series flips the mode on purpose (11.3.2), so this test
    failing means someone left ``send`` on in the committed config.
    """
    for role in ("police", "thief"):
        config = ConfigManager.load(role)
        assert config.private_value("email", "recipient", "") == AGENT_REPORT_ADDRESS
        assert config.private_value("email", "mode", "") == EMAIL_MODE_DRAFT
