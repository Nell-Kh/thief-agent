"""The README is the graded academic report, so its claims are checked too.

Rule #42 makes `README.md` the submission's academic report; ch. 9.4.2 lists its
mandatory components. Two failure modes have already happened here and neither
announces itself:

* **stale headline numbers.** The self-grade quoted 689 tests and 97.8% coverage
  long after both had moved. A grader who re-runs the suite and gets a different
  number stops trusting the section.
* **broken internal links.** Two table-of-contents anchors pointed at headings
  that had been reworded. Nothing renders as an error - the link simply goes
  nowhere, in the one document the examiner is most likely to navigate.

Both are mechanical, so both are checked rather than re-read.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"

#: Numbers that were true once and are now wrong; each names itself on failure.
SUPERSEDED_CLAIMS = ("689 tests", "613 tests", "611 tests", "762 tests", "819 tests",
                     "97.8% coverage", "97.4% coverage")

#: Components ch. 9.4.2 requires the report to contain.
REQUIRED_SECTIONS = (
    "Dec-POMDP",
    "Screenshots",
    "Cross-repo links",
    "Code-quality self-grade",
)


def _text() -> str:
    """The report as written."""
    return README.read_text(encoding="utf-8")


def _heading_anchors(text: str) -> set[str]:
    """GitHub's slug for every heading, so links can be resolved against them."""
    anchors = set()
    for heading in re.findall(r"^#{2,4} (.+)$", text, re.MULTILINE):
        slug = re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
        anchors.add(slug)
    return anchors


def test_every_internal_link_points_at_a_real_heading() -> None:
    """A dead anchor in the report is invisible until the examiner clicks it."""
    text = _text()
    anchors = _heading_anchors(text)
    broken = sorted(
        link for link in set(re.findall(r"\]\(#([a-z0-9-]+)\)", text))
        if link not in anchors
    )
    assert not broken, f"README links point at headings that do not exist: {broken}"


def test_every_referenced_repo_file_exists() -> None:
    """A report citing a file that was renamed or deleted misleads the reader."""
    missing = sorted(
        target
        for target in set(re.findall(r"\]\((docs/[\w./-]+|scripts/[\w./-]+)\)", _text()))
        if not (REPO_ROOT / target.split("#")[0]).exists()
    )
    assert not missing, f"README links to files that do not exist: {missing}"


@pytest.mark.parametrize("stale", SUPERSEDED_CLAIMS)
def test_superseded_headline_numbers_are_not_left_behind(stale: str) -> None:
    """Pinned individually so the failure message names the number to update."""
    assert stale not in _text(), (
        f"README still claims {stale!r} - re-measure and update the self-grade"
    )


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_the_report_carries_every_mandatory_component(section: str) -> None:
    """Ch. 9.4.2 lists these; a missing one costs marks on the report itself."""
    assert section in _text(), f"README is missing the {section!r} component"


def test_the_report_has_not_been_gutted() -> None:
    """A guard against a truncated or half-written report passing silently."""
    assert len(_text().splitlines()) > 300


def test_the_claimed_suite_size_is_the_collected_suite_size(request) -> None:
    """Derive the headline number instead of blocklisting stale ones.

    The blocklist caught 689 and missed 762 - enumeration always loses to the
    next stale value. This asserts the README's claimed collection size against
    the size pytest itself just collected, so the claim can only ever be the
    truth or a test failure telling someone to update one line.
    """
    import re

    match = re.search(r"(\d+) tests collected", _text())
    assert match, "README must state the collected-suite size as 'NNN tests collected'"
    claimed = int(match.group(1))
    collected = len(request.session.items)
    if collected < claimed // 2:
        pytest.skip("partial test run (-k/-x): full-suite size not observable")
    assert collected == claimed, (
        f"README claims {claimed} tests collected, this run collected {collected} - "
        f"update the two headline lines in README.md"
    )
