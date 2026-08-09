"""The 150-code-line law, enforced by the suite instead of by memory.

The submission guidelines (ch. 3.2) cap every code file at 150 lines, counting
neither blank lines nor comments, and ch. 6.1 rule 6 extends the cap to test
files explicitly. That rule had drifted unnoticed because nothing checked it:
the only record of compliance was a sentence in ``docs/COMPLIANCE.md`` claiming
zero files over the limit while four were.

Docstrings are excluded alongside comments. They are documentation, and the
same guidelines mandate one on every module, class and function - a counting
rule that punished writing them would pull the two requirements against each
other.

**The guidelines are not unambiguous about this, and we should say so.** §3.2
says "no code file shall exceed 150 lines of code (blank lines and comment lines
are not counted)" - which excludes comments and is silent on docstrings, the
reading applied here. But the quick-reference card on p.24 lists "files up to
150 lines of code, comments and docstrings", which reads the other way. An
external review pointed out, fairly, that the lenient reading was exempting the
one `src/` file that failed the stricter one.

So both are now measured, and the difference is deliberately small:
``MAX_CODE_LINES`` governs the rule, while
:func:`test_no_source_file_is_over_the_cap_under_the_stricter_reading` reports
the plain-wording count too. `services/series_guard.py` - the file that prompted
this - was split into containment and :mod:`services.series_checkpoint` so it
passes under BOTH readings rather than under the one we happened to pick.

``KNOWN_OVER_LIMIT`` is a shrinking list, not an escape hatch: a file may only
sit in it while its split is an open decision, and the second test fails if an
entry has quietly come back under the cap, so the list cannot outlive the debt.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNED_DIRS = ("src", "scripts", "tests")
MAX_CODE_LINES = 150

#: Files whose split is a pending decision, not an accepted exemption. Each is a
#: developer script, none is imported by ``src/`` or by the game at runtime.
KNOWN_OVER_LIMIT = frozenset(
    {
        "scripts/build_notebook.py",
        "scripts/friendly_series.py",
        "scripts/sparring_series.py",
    }
)


def _docstring_lines(tree: ast.Module) -> set[int]:
    """Line numbers occupied by module, class and function docstrings."""
    occupied: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            continue
        if ast.get_docstring(node) is None or not node.body:
            continue
        first = node.body[0]
        for line in range(first.lineno, (first.end_lineno or first.lineno) + 1):
            occupied.add(line)
    return occupied


def code_lines(path: Path) -> int:
    """Count a file's code lines: no blanks, no comments, no docstrings."""
    source = path.read_text(encoding="utf-8")
    skip = _docstring_lines(ast.parse(source))
    return sum(
        1
        for number, line in enumerate(source.splitlines(), start=1)
        if line.strip() and not line.strip().startswith("#") and number not in skip
    )


def python_files() -> list[Path]:
    """Every Python file the law applies to, in a stable order."""
    found: list[Path] = []
    for directory in SCANNED_DIRS:
        found.extend(
            path
            for path in (REPO_ROOT / directory).rglob("*.py")
            if "__pycache__" not in path.parts
        )
    return sorted(found)


def test_every_file_obeys_the_150_code_line_law() -> None:
    """No file outside the shrinking known-debt list may exceed the cap."""
    over = {
        relative: counted
        for path in python_files()
        if (relative := path.relative_to(REPO_ROOT).as_posix()) not in KNOWN_OVER_LIMIT
        and (counted := code_lines(path)) > MAX_CODE_LINES
    }
    assert not over, (
        f"over the {MAX_CODE_LINES}-code-line cap: {over} - split them rather than "
        "compressing them (guidelines ch. 3.2)"
    )


def plain_lines(path: Path) -> int:
    """The guidelines' literal §3.2 count: no blanks, no comments, docstrings kept."""
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def test_no_source_file_is_over_the_cap_under_the_stricter_reading() -> None:
    """`src/` must pass the plain wording too, not just the reading we chose.

    §3.2 excludes blanks and comments and is silent on docstrings; the p.24
    quick-reference card counts docstrings in. Rather than argue for the lenient
    reading, every shipped module satisfies both - so the interpretation stops
    being load-bearing. Scoped to `src/`: `tests/` and `scripts/` carry far more
    prose per statement, and the cap exists to keep production modules small.
    """
    over = {
        relative: counted
        for path in python_files()
        if (relative := path.relative_to(REPO_ROOT).as_posix()).startswith("src/")
        and (counted := plain_lines(path)) > MAX_CODE_LINES
    }
    assert not over, (
        f"over {MAX_CODE_LINES} lines under the guidelines' plain wording "
        f"(docstrings counted): {over} - split, do not compress"
    )


def test_the_known_debt_list_never_outlives_the_debt() -> None:
    """A file that has come back under the cap must leave the list."""
    settled = {
        relative: counted
        for relative in sorted(KNOWN_OVER_LIMIT)
        if (counted := code_lines(REPO_ROOT / relative)) <= MAX_CODE_LINES
    }
    assert not settled, f"now within the cap, so remove from KNOWN_OVER_LIMIT: {settled}"
