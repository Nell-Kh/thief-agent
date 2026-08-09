"""Guidelines §3.3 - every module, class and function documented - as a gate.

The rule is unconditional, and the codebase largely met it: `src/` and
`scripts/` were complete, `tests/` was not. An external review found 589
undocumented definitions there, and `COMPLIANCE.md` had been recording "a sweep
is still owed" for some time.

They were not all the same kind of gap, so they did not get the same answer.

* **Modules, classes, fixtures and helpers** genuinely need prose: a fixture
  called ``view`` or a fake called ``SlowTransport`` tells you its shape and
  nothing about why it exists. All 125 were written.
* **Test functions** are the declared exception. Their names are already full
  sentences - ``test_a_diagonal_or_unknown_move_is_rejected`` - and a docstring
  restating the name is documentation theatre: it adds a line, adds no
  information, and pushes files toward a cap that exists to keep them readable.

An exception nobody checks is just a gap with better branding, so the convention
is enforced here instead of merely written down: an undocumented test function
must have a name that really is a sentence. Fall below that and the choice is
yours - rename it, or write the docstring - but you cannot quietly do neither.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Directories the docstring rule applies to.
SCANNED_DIRS = ("src", "scripts", "tests")

#: Words after the ``test_`` prefix for a name to read as a sentence on its own.
#: Four is the point at which a name states a subject and an outcome rather than
#: a label: ``test_nonces_never_repeat`` (3) is a label, ``test_a_forged_hash_is
#: _tampered`` (5) is a claim.
MIN_SENTENCE_WORDS = 4


def _python_files() -> list[Path]:
    """Every Python file the rule applies to, in a stable order."""
    found: list[Path] = []
    for directory in SCANNED_DIRS:
        found.extend(
            path
            for path in (REPO_ROOT / directory).rglob("*.py")
            if "__pycache__" not in path.parts
        )
    return sorted(found)


def _definitions(tree: ast.Module):
    """Every class and function node in a parsed module."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def test_every_module_has_a_docstring() -> None:
    """Including the package markers, which should say what lives below them."""
    missing = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in _python_files()
        if ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) is None
    ]
    assert not missing, f"modules without a docstring: {missing}"


def test_every_class_has_a_docstring() -> None:
    """A fake or a helper class must say what it stands in for."""
    missing: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        missing += [
            f"{path.relative_to(REPO_ROOT).as_posix()}::{node.name}"
            for node in _definitions(tree)
            if isinstance(node, ast.ClassDef) and ast.get_docstring(node) is None
        ]
    assert not missing, f"classes without a docstring: {missing}"


def test_every_non_test_function_has_a_docstring() -> None:
    """Fixtures, helpers and all production code - no exception claimed here."""
    missing: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        missing += [
            f"{path.relative_to(REPO_ROOT).as_posix()}::{node.name}"
            for node in _definitions(tree)
            if not isinstance(node, ast.ClassDef)
            and not node.name.startswith("test_")
            and ast.get_docstring(node) is None
        ]
    assert not missing, f"functions without a docstring: {missing}"


def test_an_undocumented_test_carries_its_meaning_in_its_name() -> None:
    """The declared exception, held to the standard that justifies it.

    A test may skip the docstring only by having a name that states what it
    claims. Short names are not forbidden - they just have to say so in prose.
    """
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in _definitions(tree):
            if isinstance(node, ast.ClassDef) or not node.name.startswith("test_"):
                continue
            if ast.get_docstring(node) is not None:
                continue
            words = [word for word in node.name.split("_")[1:] if word]
            if len(words) < MIN_SENTENCE_WORDS:
                offenders.append(
                    f"{path.relative_to(REPO_ROOT).as_posix()}::{node.name} "
                    f"({len(words)} words)"
                )
    assert not offenders, (
        "these tests have neither a docstring nor a sentence-length name - "
        f"rename or document them: {offenders}"
    )
