"""Notebook cells, part 1 of 5: Parameter Research: Converting Inference int.

Split from ``build_notebook.py`` under the 150-line rule. The notebook is
authored as code so every figure in the committed ``.ipynb`` is the output of a
real run rather than a pasted image; these modules hold the cell text and
``build_notebook.py`` concatenates them, in order, into one notebook.
"""

from __future__ import annotations

from _notebook_cells import code, md

CELLS = [
    md(
        "# Parameter Research: Converting Inference into Capture\n\n"
        "**Project:** Distributed Cops-and-Robbers over P2P | **Phase 8** research notebook\n\n"
        "Phase 7's first full networked self-play match ended with a striking asymmetry: "
        "the cop's Bayesian belief argmax sat **exactly on the thief's true cell**, and the "
        "thief still survived 35 steps. Inference was solved; *conversion* was not. This "
        "notebook isolates the conversion problem in a perfect-information harness (the "
        "cop is given the thief's true cell, i.e. the best case belief can ever deliver), "
        "measures the shipped pinch strategy, diagnoses why it cannot convert, derives a "
        "replacement - the **region cop** - and tunes both sides' parameters."
    ),
    code(
        "import itertools\n"
        "import sys\n\n"
        "sys.path.insert(0, '../src')\n"
        "import matplotlib.pyplot as plt\n\n"
        "from police_thief.constants import ROLE_POLICE, ROLE_THIEF\n"
        "from police_thief.domain.board import Board\n"
        "from police_thief.domain.brain import enhanced\n"
        "from police_thief.domain.brain.enhanced import EnhancedPoliceBrain, EnhancedThiefBrain\n"
        "from police_thief.domain.brain.region import RegionPoliceBrain\n"
        "from police_thief.domain.state import GameState\n"
        "from police_thief.sdk import SimulationSdk\n"
        "from police_thief.services.runtime import LocalMatchRunner\n"
        "from police_thief.shared.config import ConfigManager\n\n"
        "config = ConfigManager.load(ROLE_POLICE, config_dir='../config')\n"
        "sdk = SimulationSdk(config)\n"
        "contract = config.contract\n"
        "GRID = contract.board.grid_size\n\n"
        "def run_match(police_brain, thief_brain, cop_start, thief_start):\n"
        "    \"\"\"One perfect-information mini-game; returns (event, steps, barriers).\"\"\"\n"
        "    runner = LocalMatchRunner(sdk, police_brain=police_brain, thief_brain=thief_brain)\n"
        "    state = GameState(board=Board(GRID), cop=cop_start, thief=thief_start)\n"
        "    while not state.finished:\n"
        "        runner.play_turn(state)\n"
        "    return state.outcome.event, state.step, state.barriers_used\n\n"
        "def sample_pairs(stride=3, min_distance=3):\n"
        "    cells = [(r, c) for r in range(0, GRID, stride) for c in range(0, GRID, stride)]\n"
        "    return [(a, b) for a, b in itertools.product(cells, cells)\n"
        "            if abs(a[0] - b[0]) + abs(a[1] - b[1]) >= min_distance]\n\n"
        "PAIRS = sample_pairs()\n"
        "print(f'evaluation grid: {len(PAIRS)} start pairs, contract ceiling "
        "{contract.movement.max_moves} moves')"
    ),
    md(
        "## 1. Baseline: the pinch cop cannot convert\n\n"
        "The shipped `EnhancedPoliceBrain` pursues by BFS and, within `PINCH_RANGE` of the "
        "target, spends barriers sealing the target's widest escape cell while keeping "
        "`BARRIER_RESERVE` in hand. Sweep both parameters over the full evaluation grid:"
    ),
    code(
        "pinch_results = {}\n"
        "for pinch, reserve in itertools.product([1, 2, 3, 4], [0, 1, 2, 3]):\n"
        "    enhanced.PINCH_RANGE, enhanced.BARRIER_RESERVE = pinch, reserve\n"
        "    outcomes = [run_match(EnhancedPoliceBrain(ROLE_POLICE, contract),\n"
        "                          EnhancedThiefBrain(ROLE_THIEF, contract), a, b)\n"
        "                for a, b in PAIRS]\n"
        "    captures = sum(1 for event, _, _ in outcomes if event == 'capture')\n"
        "    pinch_results[(pinch, reserve)] = captures / len(PAIRS)\n"
        "enhanced.PINCH_RANGE, enhanced.BARRIER_RESERVE = 2, 2  # restore defaults\n\n"
        "fig, ax = plt.subplots(figsize=(6, 4))\n"
        "grid = [[pinch_results[(p, r)] for r in [0, 1, 2, 3]] for p in [1, 2, 3, 4]]\n"
        "image = ax.imshow(grid, vmin=0, vmax=1, cmap='RdYlGn')\n"
        "ax.set_xticks(range(4), [0, 1, 2, 3])\n"
        "ax.set_yticks(range(4), [1, 2, 3, 4])\n"
        "ax.set_xlabel('BARRIER_RESERVE')\n"
        "ax.set_ylabel('PINCH_RANGE')\n"
        "ax.set_title('Pinch cop capture rate (perfect information)')\n"
        "for i, p in enumerate([1, 2, 3, 4]):\n"
        "    for j, r in enumerate([0, 1, 2, 3]):\n"
        "        ax.text(j, i, f'{pinch_results[(p, r)]:.0%}', ha='center', va='center')\n"
        "fig.colorbar(image)\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md(
        "**The surface is flat at 0%.** No parameter setting converts a single start - the "
        "problem is structural, not a tuning miss. That kills the original phase-8 plan "
        "(tune the pinch) and demands a diagnosis."
    ),
    md(
        "## 2. Diagnosis: the parity dance\n\n"
        "Trace the endgame of one match. The cop herds the thief into a corner, then the "
        "two settle into a 2-cycle: cop steps to the corner's edge, thief slides along the "
        "wall, cop steps back, thief slides back. With equal speeds and orthogonal moves, "
        "the pursuer never gains the last step - and the pinch trigger (orthogonal "
        "adjacency) never fires because the dance settles on the *diagonal*:"
    ),
    code(
        "runner = LocalMatchRunner(sdk,\n"
        "    police_brain=EnhancedPoliceBrain(ROLE_POLICE, contract),\n"
        "    thief_brain=EnhancedThiefBrain(ROLE_THIEF, contract))\n"
        "state = GameState(board=Board(GRID), cop=(0, 0), thief=(6, 6))\n"
        "distances = []\n"
        "while not state.finished:\n"
        "    runner.play_turn(state)\n"
        "    gap = abs(state.cop[0] - state.thief[0]) + abs(state.cop[1] - state.thief[1])\n"
        "    distances.append(gap)\n"
        "fig, ax = plt.subplots(figsize=(7, 3))\n"
        "ax.plot(range(1, len(distances) + 1), distances, marker='o', markersize=3)\n"
        "ax.set_xlabel('step')\n"
        "ax.set_ylabel('cop-thief Manhattan distance')\n"
        "ax.set_title(f'The parity dance: distance never reaches 0 "
        "(outcome: {state.outcome.event})')\n"
        "ax.axhline(1, color='red', linestyle=':', label='capture requires 0')\n"
        "ax.legend()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md(
        "## 3. The region cop\n\n"
        "Stop chasing the thief; strangle its **options**. Define the thief's *safe region* "
        "as the set of cells it reaches strictly before the cop (two BFS fields). Each turn "
        "the region cop picks, among all legal steps and all legal barrier placements, the "
        "action minimizing `(region size, thief exit count, distance)` - with two quota "
        "guards: mid-game barriers must starve the region by `MIN_SHRINK` cells, and once "
        "the region is at most `ENDGAME` cells *any* sealed exit is worth a stone, because "
        "a barrier is the one move the thief can never undo. Same evaluation grid:"
    ),
]
