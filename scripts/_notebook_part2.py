"""Notebook cells, part 2 of 5: Sensitivity: choosing MIN_SHRINK and ENDGAME.

Split from ``build_notebook.py`` under the 150-line rule. The notebook is
authored as code so every figure in the committed ``.ipynb`` is the output of a
real run rather than a pasted image; these modules hold the cell text and
``build_notebook.py`` concatenates them, in order, into one notebook.
"""

from __future__ import annotations

from _notebook_cells import code, md

CELLS = [
    code(
        "outcomes = [run_match(RegionPoliceBrain(ROLE_POLICE, contract),\n"
        "                      EnhancedThiefBrain(ROLE_THIEF, contract), a, b)\n"
        "            for a, b in PAIRS]\n"
        "captures = [steps for event, steps, _ in outcomes if event == 'capture']\n"
        "barriers = [used for event, _, used in outcomes if event == 'capture']\n"
        "print(f'capture rate : {len(captures)}/{len(PAIRS)}')\n"
        "print(f'mean steps   : {sum(captures) / len(captures):.1f} "
        "(ceiling {contract.movement.max_moves})')\n"
        "print(f'mean barriers: {sum(barriers) / len(barriers):.2f} "
        "(quota {contract.movement.max_barriers})')\n\n"
        "fig, ax = plt.subplots(figsize=(7, 3))\n"
        "ax.hist(captures, bins=range(2, 14), edgecolor='black')\n"
        "ax.set_xlabel('steps to capture')\n"
        "ax.set_ylabel('matches')\n"
        "ax.set_title('Region cop: time-to-capture over the evaluation grid')\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md(
        "## 4. Sensitivity: choosing MIN_SHRINK and ENDGAME\n\n"
        "The two knobs guard the barrier quota. Sweep both; report capture rate and mean "
        "cost (steps, barriers):"
    ),
    code(
        "rows = []\n"
        "for shrink, endgame in itertools.product([1, 2, 3, 4, 5], [2, 4, 6, 8]):\n"
        "    brain_class = type('Tuned', (RegionPoliceBrain,),\n"
        "                       {'MIN_SHRINK': shrink, 'ENDGAME': endgame})\n"
        "    outcomes = [run_match(brain_class(ROLE_POLICE, contract),\n"
        "                          EnhancedThiefBrain(ROLE_THIEF, contract), a, b)\n"
        "                for a, b in PAIRS]\n"
        "    caught = [(steps, used) for event, steps, used in outcomes if event == 'capture']\n"
        "    rows.append((shrink, endgame, len(caught) / len(PAIRS),\n"
        "                 sum(s for s, _ in caught) / max(len(caught), 1),\n"
        "                 sum(u for _, u in caught) / max(len(caught), 1)))\n"
        "print(f'{\"MIN_SHRINK\":>10} {\"ENDGAME\":>8} {\"capture\":>8} '\n"
        "      f'{\"steps\":>6} {\"barriers\":>9}')\n"
        "for shrink, endgame, rate, steps, used in rows:\n"
        "    print(f'{shrink:>10} {endgame:>8} {rate:>8.0%} {steps:>6.1f} {used:>9.2f}')\n\n"
        "# Control: is the flatness real robustness, or a broken sweep? Cripple the\n"
        "# barrier logic entirely (impossible MIN_SHRINK, no endgame) and re-measure.\n"
        "crippled = type('Crippled', (RegionPoliceBrain,), {'MIN_SHRINK': 100, 'ENDGAME': 0})\n"
        "outcomes = [run_match(crippled(ROLE_POLICE, contract),\n"
        "                      EnhancedThiefBrain(ROLE_THIEF, contract), a, b)\n"
        "            for a, b in PAIRS]\n"
        "no_barrier_rate = sum(1 for e, _, _ in outcomes if e == 'capture') / len(PAIRS)\n"
        "print(f'\\ncontrol - barriers disabled: {no_barrier_rate:.0%} capture '\n"
        "      '(the endgame gate is the load-bearing part)')"
    ),
    md(
        "## 5. The thief's first defense attempt (spoiler: it fails)\n\n"
        "Flip the question: with the region cop now the reference attacker, which "
        "`TRAP_RISK_PENALTY` maximizes the thief's survival time? (Survival points are "
        "granted only at the full 35 steps, but every extra step forces more cop moves in "
        "a real match - more scent decay, more belief noise.)"
    ),
    code(
        "penalties = [0, 1, 3, 5, 8]\n"
        "mean_survival = []\n"
        "for penalty in penalties:\n"
        "    thief_class = type('TunedThief', (EnhancedThiefBrain,),\n"
        "                       {'TRAP_RISK_PENALTY': penalty})\n"
        "    outcomes = [run_match(RegionPoliceBrain(ROLE_POLICE, contract),\n"
        "                          thief_class(ROLE_THIEF, contract), a, b)\n"
        "                for a, b in PAIRS]\n"
        "    mean_survival.append(sum(steps for _, steps, _ in outcomes) / len(outcomes))\n"
        "fig, ax = plt.subplots(figsize=(6, 3))\n"
        "ax.plot(penalties, mean_survival, marker='o')\n"
        "ax.set_xlabel('TRAP_RISK_PENALTY')\n"
        "ax.set_ylabel('mean steps survived')\n"
        "ax.set_title('Thief survival vs trap-risk aversion (against the region cop)')\n"
        "plt.tight_layout()\n"
        "plt.show()\n"
        "for penalty, steps in zip(penalties, mean_survival, strict=True):\n"
        "    print(f'penalty {penalty}: survives {steps:.1f} steps on average')"
    ),
    md(
        "## 6. Exhaustive validation\n\n"
        "The 72-pair grid could hide blind spots. Validate the chosen parameters over "
        "**every** legal start pair at Manhattan distance ≥ 3 - all 1900 of them:"
    ),
    code(
        "cells = [(r, c) for r in range(GRID) for c in range(GRID)]\n"
        "all_pairs = [(a, b) for a, b in itertools.product(cells, cells)\n"
        "             if abs(a[0] - b[0]) + abs(a[1] - b[1]) >= 3]\n"
        "outcomes = [run_match(RegionPoliceBrain(ROLE_POLICE, contract),\n"
        "                      EnhancedThiefBrain(ROLE_THIEF, contract), a, b)\n"
        "            for a, b in all_pairs]\n"
        "captures = [steps for event, steps, _ in outcomes if event == 'capture']\n"
        "print(f'capture rate: {len(captures)}/{len(all_pairs)}')\n"
        "print(f'steps: mean {sum(captures) / len(captures):.1f}, max {max(captures)} '\n"
        "      f'(ceiling {contract.movement.max_moves})')"
    ),
    md(
        "## 7. The arms race, round 1: evolving the thief\n\n"
        "A 100% cop against our *own* thief proves little about the league - it may only "
        "prove the thief is weak. So the thief gets its turn. Strict priority orderings "
        "of its criteria all fail; what works is a **weighted blend** of four terms: the "
        "worst-case own safe region after the cop's best reply (one-ply max-min), true-path "
        "distance from the cop, *openness* (distance from the nearest edge - walls are "
        "where strangulation begins), and mobility:"
    ),
    code(
        "from police_thief.domain.brain.evade import EvadeThiefBrain\n\n"
        "outcomes = [run_match(RegionPoliceBrain(ROLE_POLICE, contract),\n"
        "                      EvadeThiefBrain(ROLE_THIEF, contract), a, b)\n"
        "            for a, b in PAIRS]\n"
        "survived = sum(1 for event, _, _ in outcomes if event == 'survival')\n"
        "mean_steps = sum(steps for _, steps, _ in outcomes) / len(outcomes)\n"
        "print(f'EvadeThief vs the region cop: {survived}/{len(PAIRS)} survivals, '\n"
        "      f'mean {mean_steps:.1f} steps (enhanced thief: 0 survivals, 9.0 steps)')"
    ),
    md(
        "The blend flips the match: the region cop that captured everything now loses "
        "most starts. Defense wins this parameter point - which means an opponent who "
        "builds an open-field evader would beat our round-1 cop. The cop must answer."
    ),
]
