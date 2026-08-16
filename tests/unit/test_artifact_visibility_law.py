"""The league artifacts must stay committable - asserted, not remembered.

A series writes its declaration, per-sub-game config, log and result into
``results/friendly_<game_id>/``. Those four are the evidence a counted series
happened at all: without them in the repository the submission asserts a
result nobody can check.

Twice now (2026-08-16, both times) ``.gitignore`` has been widened to a blanket
``results/``, and both times the damage was silent - ``git add results/`` adds
nothing and prints nothing, so the artifacts simply would not have been there.
Generated noise still gets ignored, but by NAME. This file is what makes the
distinction survive the next person who is tired of seeing scratch output in
``git status``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Paths a real series writes, which MUST be committable.
LEAGUE_ARTIFACTS = (
    "results/friendly_them-vs-yanell11/declaration_them-vs-yanell11.json",
    "results/friendly_them-vs-yanell11/config_them-vs-yanell11_g01.json",
    "results/friendly_them-vs-yanell11/log_them-vs-yanell11_g01.json",
    "results/friendly_them-vs-yanell11/result_them-vs-yanell11.json",
    "results/README.md",
)

#: Paths that are generated noise, which SHOULD stay ignored - so the law is
#: "ignore by name", not "ignore nothing".
GENERATED_NOISE = (
    "results/rehearsal_2026-01-01/log_x_g01.json",
    "results/config_demo_2026-08-06_g01.json",
)


def is_ignored(path: str) -> bool:
    """Whether git would ignore ``path``, asked of git rather than guessed.

    ``git check-ignore`` exits 0 when a path is ignored and 1 when it is not,
    and it answers for paths that do not exist - which is the case that matters
    here, since the artifacts of the next series have not been written yet.
    """
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=ROOT, capture_output=True, check=False,
    )
    if result.returncode > 1:
        pytest.skip(f"git unavailable or not a repository: {result.stderr!r}")
    return result.returncode == 0


@pytest.mark.parametrize("path", LEAGUE_ARTIFACTS)
def test_a_league_artifact_is_committable(path: str) -> None:
    """The evidence of a played series must not be ignored.

    If this fails, someone has widened ``.gitignore`` to swallow ``results/``
    and a counted series would be submitted with nothing beside it. Ignore the
    noise by name instead - see the ``# results`` block in ``.gitignore``.
    """
    assert not is_ignored(path), (
        f"{path} is git-ignored, so a played series would be submitted with no "
        f"evidence. Narrow the `results/` rule in .gitignore back to named noise."
    )


@pytest.mark.parametrize("path", GENERATED_NOISE)
def test_generated_noise_is_still_ignored(path: str) -> None:
    """The rule is 'ignore by name', so the named noise must really be ignored."""
    assert is_ignored(path), f"{path} should be ignored as generated output"
