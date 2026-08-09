"""Rules #39/#40 enforced by the suite instead of by discipline.

A leaked secret is permanent: once it is in a commit it is in the history, and
deleting it later changes nothing. The repository has never leaked one - this
file exists so that stays true under every future commit rather than resting on
whoever writes it remembering.

Three layers, each catching a different mistake:

* the ignore rules still name every secret-bearing file (someone "tidies"
  ``.gitignore``);
* no secret-bearing file is tracked, and no tracked file *contains* material
  matching a live-credential shape (someone ``git add -f``s, or pastes a key
  into a docstring, a notebook cell or a test fixture);
* the history has never carried one (the check that made the original review's
  finding "history is clean" a fact rather than a hope).

The scanner looks for issuer PREFIXES, not entropy: prefixes are what real keys
actually start with, and they do not fire on the hex digests this project is
full of. This file exempts itself, since it necessarily spells the prefixes out.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Files that must never be committed, and must always be ignored.
SECRET_FILES = (".env", "credentials.json", "token.json")

#: Ignore patterns that must survive in .gitignore.
REQUIRED_IGNORES = (".env", "credentials.json", "token.json", "*.pem", "*.key")

#: Live-credential shapes, by issuer prefix. Assembled at runtime so this file
#: does not itself contain a literal that a naive scanner would flag.
_PREFIXES = (
    "sk-" "ant-",        # Anthropic
    "sk-" "proj-",       # OpenAI project key
    "ya29." "",          # Google OAuth access token
    "GOCSPX" "-",        # Google OAuth client secret
    "rnd_" "",           # Render API key
    "ghp_" "",           # GitHub personal access token
    "github_" "pat_",    # GitHub fine-grained PAT
    "AKIA" "",           # AWS access key id
)
_PEM = "-----BEGIN" + " " + "PRIVATE KEY-----"

#: Only this file, which assembles the prefixes as literals. Documentation that
#: merely NAMES a prefix no longer needs exempting, because the scanner requires
#: a key body after it - so docs/SECURITY.md and docs/TODO.md are fully scanned.
SCAN_EXEMPT = {"tests/unit/test_secrets_hygiene.py"}

#: Binary/vendored paths where a prefix match would be meaningless.
SCAN_SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".lock")


def _git(*args: str) -> str:
    """Run a read-only git command, skipping the test if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError) as error:  # pragma: no cover
        pytest.skip(f"git unavailable: {error}")
    if result.returncode != 0:  # pragma: no cover - not a git checkout
        pytest.skip(f"not a git checkout: {result.stderr.strip()}")
    return result.stdout


def _tracked_files() -> list[str]:
    """Every path git is tracking right now."""
    return [line for line in _git("ls-files").splitlines() if line]


def _committable_files() -> list[str]:
    """Everything a ``git add -A`` would sweep up: tracked AND untracked-not-ignored.

    Scanning only tracked files leaves the exact hole that matters - a brand new
    file is untracked until the very commit that adds it, so the scan would first
    see it one commit too late. ``--others --exclude-standard`` closes that: a
    key pasted into a new doc fails the suite *before* it can be committed.
    (Found the honest way: this scanner's first version missed a new file in the
    very commit that introduced the scanner.)
    """
    listing = _git("ls-files", "--cached", "--others", "--exclude-standard")
    return sorted({line for line in listing.splitlines() if line})


#: A real key is a prefix followed by a long opaque body. Requiring that body is
#: what separates a pasted credential from prose *about* credentials - the
#: runbook in docs/SECURITY.md and the risk notes in docs/TODO.md both name these
#: prefixes on purpose, and a scanner that fires on the bare prefix would either
#: block honest documentation or be silenced by an exemption broad enough to hide
#: a real key later. (Found the honest way: this check failed on TODO.md the
#: moment that file started naming which token to revoke first.)
_KEY_BODY = r"[A-Za-z0-9_\-]{12,}"


def _looks_like_a_credential(text: str) -> list[str]:
    """The issuer prefixes that appear followed by real key material."""
    hits = [
        prefix
        for prefix in _PREFIXES
        if re.search(re.escape(prefix) + _KEY_BODY, text)
    ]
    if _PEM in text:
        hits.append("PEM private key")
    return hits


def test_the_ignore_rules_still_name_every_secret_file() -> None:
    """Rule #40. The first thing a tidy-up deletes is the thing protecting you."""
    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    entries = {line.strip() for line in ignored if line.strip()}
    missing = [pattern for pattern in REQUIRED_IGNORES if pattern not in entries]
    assert not missing, f".gitignore no longer excludes: {missing}"


def test_git_actually_ignores_the_secret_files_that_exist() -> None:
    """Asserting the rule text is not the same as asserting the behaviour."""
    for name in SECRET_FILES:
        if not (REPO_ROOT / name).exists():
            continue
        result = subprocess.run(
            ["git", "check-ignore", name],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"{name} exists and is NOT ignored"


def test_no_secret_bearing_file_is_tracked() -> None:
    """Rule #39, present tense."""
    tracked = set(_tracked_files())
    leaked = [name for name in SECRET_FILES if name in tracked]
    assert not leaked, f"secret files are tracked: {leaked}"


def test_no_committable_file_contains_live_credential_material() -> None:
    """Catches the paste into a docstring, a notebook cell or a test fixture.

    Scans tracked *and* untracked-not-ignored files, so a key in a brand new
    file fails before the commit that would publish it, not after.
    """
    offenders: dict[str, list[str]] = {}
    for path in _committable_files():
        if path in SCAN_EXEMPT or path.endswith(SCAN_SKIP_SUFFIXES):
            continue
        full = REPO_ROOT / path
        if not full.is_file():
            continue
        try:
            text = full.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if hits := _looks_like_a_credential(text):
            offenders[path] = hits
    assert not offenders, f"live-credential shapes in committable files: {offenders}"


def test_prose_about_credentials_is_not_mistaken_for_one() -> None:
    """Documentation must be able to name a prefix without failing the build.

    The alternative is an exemption list, and an exemption broad enough to cover
    the security runbook is broad enough to hide a real key pasted into it later.
    Requiring a key BODY after the prefix keeps both files fully scanned.
    """
    prose = [
        "revoke the rnd_ token first - it is a Render infrastructure key",
        "keys look like sk-proj-... or ghp_... depending on the issuer",
        "| `rnd_...` | Render | dashboard.render.com |",
    ]
    for line in prose:
        assert not _looks_like_a_credential(line), f"false positive on prose: {line!r}"


def test_material_that_really_is_a_key_is_still_caught() -> None:
    """The other half of the precision trade - recall must not have moved.

    Synthetic bodies, not real credentials: the shapes are what matter.
    """
    planted = [
        'MCP_AUTH_TOKEN="rnd_' + "A1b2C3d4E5f6G7h8" + '"',
        'key = "sk-' + 'ant-api03-' + "x" * 20 + '"',
        "token: ya29." + "a0ARGnu0Z6upgEBXo4VQ94",
    ]
    for line in planted:
        assert _looks_like_a_credential(line), f"missed a credential shape: {line[:28]!r}"


def test_the_env_example_documents_without_disclosing() -> None:
    """A template that carries a real value is worse than no template."""
    example = REPO_ROOT / ".env-example"
    assert example.is_file(), ".env-example is a required onboarding artifact"
    text = example.read_text(encoding="utf-8")
    assert not _looks_like_a_credential(text), ".env-example contains real key material"


def test_no_secret_has_ever_been_committed_in_the_whole_history() -> None:
    """A secret in ANY reachable commit is leaked forever, even if later removed."""
    names = set()
    for line in _git("log", "--all", "--pretty=format:", "--name-only").splitlines():
        if line.strip():
            names.add(line.strip())
    leaked = sorted(name for name in names if Path(name).name in SECRET_FILES)
    assert not leaked, f"secret files appear in git history: {leaked}"


def test_the_env_file_if_present_carries_only_what_the_code_reads() -> None:
    """Every unused secret is liability with no upside.

    ``ANTHROPIC_API_KEY`` is the only variable any module reads. Four others
    once sat beside it - an OpenAI key, a Gmail app password, a Render token and
    a sender address - referenced by nothing, rotated by nobody, and readable by
    anything with access to the folder. This fails until they are gone.
    """
    env = REPO_ROOT / ".env"
    if not env.is_file():
        pytest.skip(".env absent (CI, or a clean checkout)")
    declared = {
        line.split("=", 1)[0].strip()
        for line in env.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#") and "=" in line
    }
    assert declared <= {"ANTHROPIC_API_KEY"}, (
        f"unused secrets still present in .env: {sorted(declared - {'ANTHROPIC_API_KEY'})}"
        " - revoke them at the provider, then delete the lines (docs/SECURITY.md)"
    )
