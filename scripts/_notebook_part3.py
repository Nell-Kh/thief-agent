"""Notebook cells, part 3 of 5: Round 2: the wall cop.

Split from ``build_notebook.py`` under the 150-line rule. The notebook is
authored as code so every figure in the committed ``.ipynb`` is the output of a
real run rather than a pasted image; these modules hold the cell text and
``build_notebook.py`` concatenates them, in order, into one notebook.
"""

from __future__ import annotations

from _notebook_cells import code, md

CELLS = [
    md(
        "## 8. Round 2: the wall cop\n\n"
        "No greedy refinement of the region cop reclaims the open-field evader - the "
        "evader's whole design is to deny the greedy shrink its opportunities. The "
        "classic pursuit-theory answer: **change the board**. Spend the opening on a "
        "center-column wall with a single door at (3,3) - six stones, built edges-inward "
        "so every stone anchors a real cut, requiring *no knowledge of the thief's "
        "position at all* (perfect under belief uncertainty) - then run the region hunt "
        "inside the thief's half with the door under control:"
    ),
    code(
        "from police_thief.domain.brain.blind import BlindThiefBrain\n"
        "from police_thief.domain.brain.wall import WallPoliceBrain\n\n"
        "for thief_cls in (BlindThiefBrain, EnhancedThiefBrain, EvadeThiefBrain):\n"
        "    outcomes = [run_match(WallPoliceBrain(ROLE_POLICE, contract),\n"
        "                          thief_cls(ROLE_THIEF, contract), a, b)\n"
        "                for a, b in PAIRS]\n"
        "    caught = [steps for event, steps, _ in outcomes if event == 'capture']\n"
        "    print(f'WallCop vs {thief_cls.__name__:18s}: {len(caught)}/{len(PAIRS)} '\n"
        "          f'captures, mean {sum(caught)/max(len(caught),1):.1f} steps')"
    ),
    md(
        "Exhaustive validation of the finale - every legal start pair at distance >= 3, "
        "against the strongest thief:"
    ),
    code(
        "outcomes = [run_match(WallPoliceBrain(ROLE_POLICE, contract),\n"
        "                      EvadeThiefBrain(ROLE_THIEF, contract), a, b)\n"
        "            for a, b in all_pairs]\n"
        "caught = [(steps, used) for event, steps, used in outcomes if event == 'capture']\n"
        "print(f'captures: {len(caught)}/{len(all_pairs)}')\n"
        "print(f'steps:    mean {sum(s for s,_ in caught)/len(caught):.1f}, '\n"
        "      f'max {max(s for s,_ in caught)} (ceiling {contract.movement.max_moves})')\n"
        "print(f'barriers: max {max(u for _,u in caught)} '\n"
        "      f'(quota {contract.movement.max_barriers})')\n\n"
        "fig, ax = plt.subplots(figsize=(7, 3))\n"
        "ax.hist([s for s, _ in caught], bins=range(5, 33), edgecolor='black')\n"
        "ax.axvline(contract.movement.max_moves, color='red', linestyle=':',\n"
        "           label='35-step ceiling')\n"
        "ax.set_xlabel('steps to capture')\n"
        "ax.set_ylabel('matches')\n"
        "ax.set_title('Wall cop vs the strongest evader: all 1900 starts')\n"
        "ax.legend()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md(
        "## 9. Red team: attacking our own cop\n\n"
        "A 100% score against thieves that don't know the wall exists proves little - "
        "league opponents can study our public repo. So three specialist thieves were "
        "built purely to break the wall cop: a **door camper** (gravity toward the "
        "guarded door instead of the open center), a **side flipper** (always cross to "
        "the cop's opposite side while the wall is open), and a **wall blocker** (park "
        "on the next missing stone while the cop is far). The side flipper found a real "
        "hole: 2/192 starts survived. The trace showed something ironic - the cop's own "
        "hunt stone had become a *pillar*, and the thief orbited it in a 2-cycle the "
        "region hunt could never break: the parity dance, reborn inside a pocket. The "
        "fix ships in the region cop: a repeated ``(cop, thief, stones)`` state - the "
        "dance's signature - now buys an anchored, hunt-preserving stone that cuts the "
        "orbit ring. Post-fix, live:"
    ),
    code(
        "from police_thief.constants import MOVE_STAY\n"
        "from police_thief.domain.brain.evade import openness, worst_case_region\n"
        "from police_thief.domain.brain.pathfind import distance_field as dfield\n"
        "from police_thief.domain.brain.region import _reach\n"
        "from police_thief.domain.brain.wall import DOOR, WALL_COLUMN\n"
        "from police_thief.domain.rules import destination, legal_moves\n\n\n"
        "class DoorCamper(EvadeThiefBrain):\n"
        "    def _pick_move(self, view):\n"
        "        best_key, best_move = None, MOVE_STAY\n"
        "        cop_f, door_f = dfield(view.board, view.target), dfield(view.board, DOOR)\n"
        "        for move in legal_moves(view.board, view.position):\n"
        "            cell = destination(view.position, move)\n"
        "            if cell == view.target:\n"
        "                continue\n"
        "            score = (worst_case_region(view.board, cell, view.target)\n"
        "                     + 2 * min(_reach(cop_f, cell), 8) - 2 * min(_reach(door_f, cell), 8)\n"
        "                     + len(view.board.free_neighbours(cell)))\n"
        "            if best_key is None or (score, str(move)) > best_key:\n"
        "                best_key, best_move = (score, str(move)), move\n"
        "        return best_move\n\n"
        "class SideFlipper(EvadeThiefBrain):\n"
        "    def _pick_move(self, view):\n"
        "        best_key, best_move = None, MOVE_STAY\n"
        "        cop_f = dfield(view.board, view.target)\n"
        "        cop_side = -1 if view.target[1] < WALL_COLUMN else 1\n"
        "        for move in legal_moves(view.board, view.position):\n"
        "            cell = destination(view.position, move)\n"
        "            if cell == view.target:\n"
        "                continue\n"
        "            score = (10 * (1 if (cell[1] - WALL_COLUMN) * cop_side < 0 else 0)\n"
        "                     + worst_case_region(view.board, cell, view.target)\n"
        "                     + 2 * min(_reach(cop_f, cell), 8) + openness(view.board, cell))\n"
        "            if best_key is None or (score, str(move)) > best_key:\n"
        "                best_key, best_move = (score, str(move)), move\n"
        "        return best_move\n\n"
        "grid = [(r, c) for r in range(0, GRID, 3) for c in range(0, GRID, 3)]\n"
        "red_pairs = [(a, b) for a, b in itertools.product(grid, grid)\n"
        "             if abs(a[0] - b[0]) + abs(a[1] - b[1]) >= 3]\n"
        "for thief_cls in (DoorCamper, SideFlipper):\n"
        "    outcomes = [run_match(WallPoliceBrain(ROLE_POLICE, contract),\n"
        "                          thief_cls(ROLE_THIEF, contract), a, b)\n"
        "                for a, b in red_pairs]\n"
        "    survived = sum(1 for e, _, _ in outcomes if e == 'survival')\n"
        "    worst = max(s for _, s, _ in outcomes)\n"
        "    print(f'{thief_cls.__name__:11s}: {survived}/{len(red_pairs)} survivals, '\n"
        "          f'worst capture at step {worst} (pre-fix: SideFlipper survived 2)')"
    ),
]
