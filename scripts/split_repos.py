"""Assemble the two per-role submission repositories (rules #49/#50, task 8.19).

The league grades two repositories - ``police-agent`` and ``thief-agent`` -
with cross-linked READMEs, two links on Moodle and four inside the result
JSON. This tool builds both trees under ``build/`` from the CURRENT git index,
so scratch outputs, caches and secrets can never leak in: what is not tracked
does not travel.

The partition decision (task 8.19.5), made explicit here because a reader of
either repo deserves the reasoning: **both repos carry the full engine**.
The mutual audit forces it - each side re-verifies the other's physics, so
the cop repo needs the thief's movement rules and vice versa - and rule 50
requires README, config/, PRDs, PLAN and TODO in each repo anyway. What
differs is the front page: each README opens with a role banner naming which
peer this repository submits, how to run it, and where its counterpart lives.

Run ``uv run python scripts/split_repos.py``. It builds the trees and points at
``docs/SUBMISSION.md`` 1 for publishing them - the built tree is the CONTENT,
never the procedure. Both role repos carry the full development history grafted
under one banner commit, so they are re-published by re-grafting, never by
``git init`` inside ``build/``; the README this tool writes is the only file
that procedure copies out of here.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"

#: The two submission repositories, keyed by repo name.
ROLES: dict[str, dict[str, str]] = {
    "police-agent": {
        "role": "police",
        "title": "the POLICE (cop) agent",
        "partner": "thief-agent",
        "serve": "uv run python -m police_thief peer --role police",
    },
    "thief-agent": {
        "role": "thief",
        "title": "the THIEF agent",
        "partner": "police-agent",
        "serve": "uv run python -m police_thief peer --role thief",
    },
}


def tracked_files() -> list[str]:
    """Every path in the git index - the only files allowed to travel."""
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [line for line in out.stdout.splitlines() if line]


def repo_urls() -> dict[str, str]:
    """The two submission URLs, read from the police TOML's ``repos`` table."""
    sys.path.insert(0, str(ROOT / "src"))
    from police_thief.shared.config import ConfigManager

    repos = ConfigManager.load("police").private("game").get("repos", {})
    return {"police-agent": str(repos.get("cop", "")), "thief-agent": str(repos.get("thief", ""))}


def role_banner(name: str, spec: dict[str, str], urls: dict[str, str]) -> str:
    """The front-page block that makes this tree a ROLE repo, not the dev repo."""
    partner = spec["partner"]
    return (
        f"# {name} — {spec['title']}\n\n"
        f"This repository submits **{spec['title']}** for the Police-Thief P2P league\n"
        f"(University of Haifa, \"Orchestration of AI Agents\", 2026). Its counterpart,\n"
        f"[`{partner}`]({urls[partner]}), submits the other role; the two repos share one\n"
        f"engine because the mutual audit requires each peer to re-verify the other's\n"
        f"physics (the partition decision is documented in the report below).\n\n"
        f"Run this peer:\n\n"
        f"```\n{spec['serve']}\n```\n\n"
        f"Gates: `uv run ruff check src scripts tests` and `uv run pytest` (coverage ≥85%).\n\n"
        f"The submission is the annotated tag `v1.0-submission` on this branch's tip.\n"
        f"The full commit-by-commit development history (both authors, original hashes -\n"
        f"the `github_commit` stamps sealed in every game log resolve here) sits directly\n"
        f"beneath this banner commit; the development story (branches, PRDs, PLAN, TODO -\n"
        f"rule 9.4.1) is carried in `docs/`. This tree was assembled from the git index of\n"
        f"the development repository, <https://github.com/Nell-Kh/police-thief-p2p>, by\n"
        f"`scripts/split_repos.py`.\n\n"
        f"---\n\n"
    )


def verify_banner_command(serve: str) -> None:
    """Refuse to ship a front-page command the CLI does not actually accept.

    The first published banners invited the grader to run ``serve`` - a verb
    the CLI never had - while the report body 50 lines below said ``peer``.
    A generated front page must never drift from the real subparser set again.

    Raises:
        SystemExit: when the banner's verb is not a real CLI subcommand.
    """
    verb = serve.split("python -m police_thief ", 1)[-1].split()[0]
    help_text = subprocess.run(
        [sys.executable, "-m", "police_thief", "--help"],
        cwd=ROOT, capture_output=True, text=True, check=False,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    ).stdout
    if f"{verb}" not in help_text.split("{", 1)[-1].split("}", 1)[0].split(","):
        raise SystemExit(f"banner command uses {verb!r}, which is not a CLI subcommand")


def assemble(name: str, spec: dict[str, str], urls: dict[str, str]) -> Path:
    """Copy the tracked tree into ``build/<name>/`` and write its role README."""
    if (ROOT / "README.md").read_text(encoding="utf-8").startswith(("# police-agent", "# thief-agent")):
        raise SystemExit("this tree already carries a role banner - run the split "
                         "from the development repo, never from inside a split repo")
    target = BUILD / name
    if target.exists():
        shutil.rmtree(target)
    for rel in tracked_files():
        source = ROOT / rel
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    readme = target / "README.md"
    readme.write_text(
        role_banner(name, spec, urls) + (ROOT / "README.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return target


def main() -> int:
    """Build both repos and print the human push-and-tag steps."""
    urls = repo_urls()
    missing = [name for name, url in urls.items() if "github.com" not in url]
    if missing or urls["police-agent"] == urls["thief-agent"]:
        print("REFUSING: [game].repos must name TWO distinct real GitHub URLs "
              f"(got {urls}). One URL twice ships duplicate links in the result "
              "JSON (rule #49) - fix config/police/game.toml first.")
        return 1
    for name, spec in ROLES.items():
        verify_banner_command(spec["serve"])
        target = assemble(name, spec, urls)
        files = sum(1 for _ in target.rglob("*") if _.is_file())
        print(f"built {target}  ({files} files)")
    print(
        "\nbuilt trees are the CONTENT, not the procedure.\n"
        "\n"
        "Do NOT `git init` inside build/<name> and push it. Both role repos carry\n"
        "the full development history grafted under a single banner commit, and a\n"
        "fresh init would replace that history with one squashed commit - exactly\n"
        "the mistake docs/SUBMISSION.md 1 was written to undo. It would also strand\n"
        "the annotated v1.0-submission tag on an unreachable commit.\n"
        "\n"
        "next steps (human): follow docs/SUBMISSION.md 1 - 'Republish the two\n"
        "submission repos with their real history' - once per repo. It grafts\n"
        "dev/main under a replayed banner commit, runs the gates inside the\n"
        "grafted tree, force-pushes with --force-with-lease, and MOVES the\n"
        "annotated tag to the new tip. Copy build/<name>/README.md as the banner.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
