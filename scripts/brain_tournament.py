"""Every cop brain against every thief brain, under BELIEF, over the real wire shape.

The `[strategy]` line in each private TOML is the single most consequential
choice in the repository, and it was justified by a research notebook whose
numbers were measured under PERFECT INFORMATION on 1900 start pairs. That is
the wrong condition for the claim: a league match is only ever played under
belief, from the contract's one fixed start, and `hybrid.py` documents exactly
the trap - a cop that is twelve steps faster with perfect information is six
steps *slower* once it must chase a diffuse belief argmax.

So this harness re-measures the choice in the condition that actually pays. It
plays complete :class:`MatchRuntime` matches - the same objects the networked
peer uses, with the same commit-reveal, scent, belief and deception layers -
and only replaces the transport with a direct hand-off, because who carries the
bytes cannot change who wins.

Deterministic: the brains are pure functions of the view, the start is fixed by
the contract, and the verbal layer is pinned to the template provider so no
model call can perturb a move. One match per pairing is therefore the whole
answer, not a sample of it.

Usage::

    .venv/Scripts/python.exe scripts/brain_tournament.py
    .venv/Scripts/python.exe scripts/brain_tournament.py --check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from police_thief.constants import ROLE_POLICE, ROLE_THIEF  # noqa: E402
from police_thief.domain.brain.base import load_brain  # noqa: E402
from police_thief.infra.llm import TemplateProvider  # noqa: E402
from police_thief.services.match_runtime import MatchRuntime  # noqa: E402
from police_thief.shared.config import ConfigManager  # noqa: E402

BRAIN = "police_thief.domain.brain"

#: Every cop brain in the tree, with the label the report prints.
#:
#: `seal` belongs here for the same reason the others do: a harness that omits
#: a candidate does not derive the choice, it ratifies it. It was missing while
#: `config/police/game.toml` named it in prose as the previous league choice,
#: so the one brain able to change the verdict was the one never measured.
COPS = {
    "blind": f"{BRAIN}.blind:BlindPoliceBrain",
    "enhanced": f"{BRAIN}.enhanced:EnhancedPoliceBrain",
    "region": f"{BRAIN}.region:RegionPoliceBrain",
    "hybrid": f"{BRAIN}.hybrid:HybridPoliceBrain",
    "wall": f"{BRAIN}.wall:WallPoliceBrain",
    "seal": f"{BRAIN}.seal:SealPoliceBrain",
    "box": f"{BRAIN}.box:BoxPoliceBrain",
}

#: Every thief brain in the tree.
THIEVES = {
    "blind": f"{BRAIN}.blind:BlindThiefBrain",
    "enhanced": f"{BRAIN}.enhanced:EnhancedThiefBrain",
    "evade": f"{BRAIN}.evade:EvadeThiefBrain",
}

#: A wedged pairing must end the harness, not the series it was meant to protect.
SAFETY_CAP = 120


def _peer(role: str, spec: str, config_dir: Path) -> MatchRuntime:
    """A full runtime for ``role`` with ``spec`` as its brain and no model calls."""
    runtime = MatchRuntime(ConfigManager.load(role, config_dir), game_id="tourney",
                           sub_game=1, github_commit="tournament")
    runtime.brain = load_brain(spec, role, runtime.contract)
    runtime.provider = TemplateProvider()
    return runtime


def play(cop: MatchRuntime, thief: MatchRuntime) -> tuple[str, str, int]:
    """Play one belief-mode match out; return ``(outcome, winner, steps)``."""
    for _ in range(SAFETY_CAP):
        if cop.ended and thief.ended:
            break
        for sender, receiver in ((thief, cop), (cop, thief)):
            if sender.ended:
                continue
            reply = receiver.on_turn(sender.play_turn())
            if reply is not None:
                sender.on_turn(reply)
    result = cop.result or thief.result or {"type": "undecided", "winner": None}
    return str(result["type"]), str(result.get("winner")), max(cop.view.step, thief.view.step)


def matrix(config_dir: Path) -> dict[tuple[str, str], tuple[str, str, int]]:
    """Every cop against every thief, keyed ``(cop_label, thief_label)``."""
    return {
        (cop_name, thief_name): play(_peer(ROLE_POLICE, cop_spec, config_dir),
                                     _peer(ROLE_THIEF, thief_spec, config_dir))
        for cop_name, cop_spec in COPS.items()
        for thief_name, thief_spec in THIEVES.items()
    }


def cop_score(results: dict, cop_name: str) -> tuple[int, float]:
    """``(captures, mean steps to capture)`` for one cop - higher, then lower, wins."""
    rows = [results[(cop_name, thief)] for thief in THIEVES]
    captures = [steps for outcome, _winner, steps in rows if outcome == "capture"]
    return len(captures), (sum(captures) / len(captures) if captures else float("inf"))


def thief_score(results: dict, thief_name: str) -> tuple[int, float]:
    """``(survivals, mean steps survived)`` for one thief - higher, then higher, wins."""
    rows = [results[(cop, thief_name)] for cop in COPS]
    survivals = [outcome for outcome, _winner, _steps in rows if outcome == "survival"]
    return len(survivals), sum(steps for _o, _w, steps in rows) / len(rows)


def report(results: dict) -> list[str]:
    """The matrix and the two verdicts, as printable lines."""
    header = "cop vs thief".ljust(12) + "".join(f"{name:>22}" for name in THIEVES)
    lines = [header, "-" * len(header)]
    for cop_name in COPS:
        cells = []
        for thief_name in THIEVES:
            outcome, winner, steps = results[(cop_name, thief_name)]
            cells.append(f"{outcome}/{winner}@{steps}")
        lines.append(f"{cop_name:<12}" + "".join(f"{cell:>22}" for cell in cells))
    lines.append("")
    best_cop = max(COPS, key=lambda name: (cop_score(results, name)[0],
                                           -cop_score(results, name)[1]))
    best_thief = max(THIEVES, key=lambda name: thief_score(results, name))
    for name in COPS:
        captures, mean = cop_score(results, name)
        lines.append(f"  cop   {name:<10} captures {captures}/{len(THIEVES)}"
                     + (f", mean {mean:.1f} steps" if captures else ""))
    for name in THIEVES:
        survivals, mean = thief_score(results, name)
        lines.append(f"  thief {name:<10} survives {survivals}/{len(COPS)}, "
                     f"mean {mean:.1f} steps alive")
    lines += ["", f"BEST COP   : {best_cop}", f"BEST THIEF : {best_thief}"]
    return lines


def configured(config_dir: Path) -> tuple[str, str]:
    """The brain specs the two private TOMLs actually select right now."""
    police = ConfigManager.load(ROLE_POLICE, config_dir)
    thief = ConfigManager.load(ROLE_THIEF, config_dir)
    return (str(police.private_value("strategy", "police_class", "")),
            str(thief.private_value("strategy", "thief_class", "")))


def main() -> None:
    """Play the matrix, print it, and optionally gate on the configured picks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", default=str(ROOT / "config"))
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero unless the TOMLs select the winners")
    args = parser.parse_args()
    config_dir = Path(args.config_dir)
    results = matrix(config_dir)
    print("\n".join(report(results)))
    police_spec, thief_spec = configured(config_dir)
    print(f"\nconfigured cop   : {police_spec}")
    print(f"configured thief : {thief_spec}")
    if args.check:
        best_cop = max(COPS, key=lambda n: (cop_score(results, n)[0], -cop_score(results, n)[1]))
        best_thief = max(THIEVES, key=lambda n: thief_score(results, n))
        wrong = [line for line in (
            None if police_spec == COPS[best_cop] else f"cop should be {COPS[best_cop]}",
            None if thief_spec == THIEVES[best_thief] else f"thief should be {THIEVES[best_thief]}",
        ) if line]
        raise SystemExit("\n".join(wrong) if wrong else 0)


if __name__ == "__main__":
    main()
