"""Tests for concession corroboration - the audit's rule 46/47 layer.

Split out of ``test_logbook_audit.py``, which had grown past the project's
150-code-line ceiling. The seam is the subject: that module proves the logbook
seals correctly and that a revealed trajectory obeys the board's physics; this
one proves that a *self-declared* capture is corroborated against independent
evidence before it is believed, covering the league kit's F-1 and F-2 findings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.domain.audit import audit_disclosure, verify_concession
from police_thief.domain.logbook import Logbook
from police_thief.domain.sealing import turn_record
from police_thief.shared.config import ConfigManager


@pytest.fixture
def contract(config_dir: Path):
    """The shipped police contract, as the audit layers read it."""
    return ConfigManager.load("police", config_dir).contract


def _boxed_in_book(*, actually_trapped: bool) -> Logbook:
    """A thief log that stays at its signed start cell (3,3), optionally walled in."""
    book = Logbook("g1", 1, "thief")
    barriers = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)}) if actually_trapped else frozenset()
    book.append(
        turn_record(
            step=1, role="thief", grid_size=7, position=(3, 3), barriers=barriers,
            move="STAY", intent="truth", hint="", tokens_step=0, tokens_total=0,
        )
    )
    book.append({"step": 1, "role": "thief", "type": "concession",
                 "result": {"type": "capture", "winner": "police", "how": "boxed in (rule 47)"}})
    return book


def test_a_true_rule_47_concession_corroborates_and_passes(contract) -> None:
    """A genuinely walled-in thief's concession survives the audit."""
    report = audit_disclosure(_boxed_in_book(actually_trapped=True).audit_payload(), contract)
    assert report.hashes_ok
    assert report.physics_ok
    assert report.verdict == "Verified OK"


def test_a_false_rule_47_concession_is_caught_by_the_audit(contract) -> None:
    """A concession claiming 'boxed in' where a legal step still existed is a lie."""
    report = audit_disclosure(_boxed_in_book(actually_trapped=False).audit_payload(), contract)
    assert report.hashes_ok  # the hashes are perfectly clean - only physics catches this
    assert not report.physics_ok
    assert report.verdict == "TAMPERED"
    assert any("boxed in" in violation for violation in report.violations)


def test_verify_concession_ignores_non_rule47_reasons() -> None:
    """A trapping-barrier or capture-claim win is already covered by the cop's own log."""
    records = [{"payload": {"type": "concession", "result": {"how": "trapping barrier"}}}]
    assert verify_concession(records) == []


def test_verify_concession_flags_a_rule47_claim_with_no_prior_turn() -> None:
    """A 'boxed in' claim with nothing sealed before it has nothing to corroborate it."""
    records = [{"payload": {"type": "concession", "result": {"how": "boxed in (rule 47)"}}}]
    assert any("no prior turn" in v for v in verify_concession(records))


def test_verify_concession_degrades_on_an_unreadable_last_turn() -> None:
    """No revealed cell is a legal schema, so the trail check is skipped, not failed."""
    records = [
        {"payload": {"type": "turn", "step": 1}},  # no position or state at all
        {"payload": {"type": "concession", "result": {"how": "boxed in (rule 47)"}}},
    ]
    assert verify_concession(records) == []


# The kit's own probe_f1_concession_corroboration.py cases, ported verbatim.
# Each is a way a self-declared capture goes wrong, or a way its FIX goes wrong.
_TRAIL_45 = [{"payload": {"type": "turn", "step": 1, "move": "move:STAY",
                          "position": [4, 6], "state": "grid=7x7;self=[4, 6];barriers=[]"}},
             {"payload": {"type": "turn", "step": 2, "move": "move:W",
                          "position": [4, 5], "state": "grid=7x7;self=[4, 5];barriers=[]"}}]
_TRAIL_45_BLIND = [{"payload": {"type": "turn", "step": 1, "move": "move:STAY"}},
                   {"payload": {"type": "turn", "step": 2, "move": "move:W"}}]
_TRAIL_22 = [{"payload": {"type": "turn", "step": 1, "move": "move:STAY",
                          "position": [2, 3], "state": "grid=7x7;self=[2, 3];barriers=[]"}},
             {"payload": {"type": "turn", "step": 2, "move": "move:W",
                          "position": [2, 2], "state": "grid=7x7;self=[2, 2];barriers=[]"}}]
# Walks the other way, so the trail ENDS on the cell the cop claimed.
_TRAIL_46 = [{"payload": {"type": "turn", "step": 1, "move": "move:STAY",
                          "position": [4, 5], "state": "grid=7x7;self=[4, 5];barriers=[]"}},
             {"payload": {"type": "turn", "step": 2, "move": "move:E",
                          "position": [4, 6], "state": "grid=7x7;self=[4, 6];barriers=[]"}}]


@pytest.mark.parametrize(
    ("label", "clean", "records", "kwargs"),
    [
        ("F-1 honest concession, reveal carries positions", True, _TRAIL_45,
         {"conceded_at": (4, 5), "own_barriers": [(4, 5)]}),
        ("F-1 the same, reveal carries NO position -> degrades, never accuses",
         True, _TRAIL_45_BLIND, {"conceded_at": (4, 5), "own_barriers": [(4, 5)]}),
        ("F-1 position-less AND not captured under our barriers -> STILL refused",
         False, _TRAIL_45_BLIND, {"conceded_at": (2, 2), "own_barriers": [(4, 5)]}),
        ("a concession over a cell our barriers never touched", False, _TRAIL_22,
         {"conceded_at": (2, 2), "own_barriers": [(4, 5)]}),
        ("a concession the revealed trail never reached", False, _TRAIL_45,
         {"conceded_at": (6, 6), "own_barriers": [(5, 6), (6, 5)]}),
        ("F-2 a FALSE answer echoing our claimed cell -> refused, not believed",
         False, _TRAIL_22, {"answered_at": (4, 6)}),
        ("F-2 a TRUE answer, trail ends where the answer said", True,
         _TRAIL_46, {"answered_at": (4, 6)}),
        ("F-2 a position-less answer degrades rather than accusing", True,
         _TRAIL_45_BLIND, {"answered_at": (4, 6)}),
    ],
)
def test_the_kit_f1_f2_corroboration_cases(label, clean, records, kwargs) -> None:
    """Every kit probe case, clean and dirty, lands on the expected verdict."""
    violations = verify_concession(records, board_size=7, **kwargs)
    assert (violations == []) is clean, f"{label}: {violations}"
