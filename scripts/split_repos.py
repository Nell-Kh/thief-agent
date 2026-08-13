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

Run ``uv run python scripts/split_repos.py``; it prints the push-and-tag
steps that only a human with the GitHub account can perform.
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
        "serve": "uv run python -m police_thief serve --role police",
    },
    "thief-agent": {
        "role": "thief",
        "title": "the THIEF agent",
        "partner": "police-agent",
        "serve": "uv run python -m police_thief serve --role thief",
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
        f"---\n\n"
    )


def assemble(name: str, spec: dict[str, str], urls: dict[str, str]) -> Path:
    """Copy the tracked tree into ``build/<name>/`` and write its role README."""
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
        target = assemble(name, spec, urls)
        files = sum(1 for _ in target.rglob("*") if _.is_file())
        print(f"built {target}  ({files} files)")
    print(
        "\nnext steps (human, once per repo - replace <name> with police-agent / thief-agent):\n"
        "  1. create the empty GitHub repo with EXACTLY the URL in the config\n"
        "  2. cd build/<name>\n"
        "     git init -b main && git add -A\n"
        '     git commit -m "initial submission tree"\n'
        "     git remote add origin <url> && git push -u origin main\n"
        "     git tag v1.0-submission && git push origin v1.0-submission\n"
        "  3. verify the gates INSIDE build/<name>: uv sync && uv run pytest -q\n"
        "  4. grant the lecturer access / set visibility (rule #49)\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
