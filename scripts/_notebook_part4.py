"""Notebook cells, part 4 of 5: # 9b. The speed-margin frontier: a hybrid, a.

Split from ``build_notebook.py`` under the 150-line rule. The notebook is
authored as code so every figure in the committed ``.ipynb`` is the output of a
real run rather than a pasted image; these modules hold the cell text and
``build_notebook.py`` concatenates them, in order, into one notebook.
"""

from __future__ import annotations

from _notebook_cells import code, md

CELLS = [
    md(
        "### 9b. The speed-margin frontier: a hybrid, and why it is not the default\n\n"
        "The wall cop pays ~25 steps even against thieves the region hunt kills in ~9, "
        "and every step is two more messages over a possibly-flaky tunnel. A hybrid was "
        "built: open in hunt mode, commit irreversibly to the wall on the first of "
        "three tripwires (region stalled 2 turns; region still > 14 at step 4; step 12 "
        "reached). Exhaustive verdict over all 1900 starts: **1900/1900 at a mean of "
        "~12 steps** against reference-style thieves - but **1891/1900** against our "
        "own elite evader; nine starts slip away, because the opening hunt steps pull "
        "the cop off its wall route and the wall finishes too late. The frontier is "
        "structural, so the choice ships in configuration: `WallPoliceBrain` (the "
        "guarantee) is the default; `HybridPoliceBrain` is the documented speed "
        "profile for opponents that have already shown a reference-fork thief. The "
        "192-start grid, for the record, showed the hybrid at 192/192 against the "
        "evader - only the exhaustive sweep exposed the nine escapes. Sample density "
        "is not proof.\n\n"
        "A second wire upgrade landed alongside: the cop's capture claims name its own "
        "cell, and when the cop's scent in the same message burns fresh at the claimed "
        "spot, the claim is verified ground truth - the thief's belief about the cop "
        "pins to it (factor 25, never a full collapse, so a forged claim with no scent "
        "behind it moves nothing)."
    ),
    md(
        "## 10. Transfer check: belief instead of truth, over the real wire\n\n"
        "Everything above hands the cop the thief's true cell. One full networked "
        "self-play match - commitments, scent, hints, belief maps, the lot - checks that "
        "the results transfer to the game as actually played:"
    ),
    code(
        "from police_thief.services.match_runtime import MatchRuntime\n\n"
        "police = MatchRuntime(ConfigManager.load('police', config_dir='../config'),\n"
        "                      game_id='nb', sub_game=1, github_commit='notebook')\n"
        "thief = MatchRuntime(ConfigManager.load('thief', config_dir='../config'),\n"
        "                     game_id='nb', sub_game=1, github_commit='notebook')\n"
        "for _ in range(90):\n"
        "    if thief.ended and police.ended:\n"
        "        break\n"
        "    if not thief.ended:\n"
        "        reply = police.on_turn(thief.play_turn())\n"
        "        if reply is not None:\n"
        "            thief.on_turn(reply)\n"
        "    if police.ended and thief.ended:\n"
        "        break\n"
        "    if not police.ended:\n"
        "        reply = thief.on_turn(police.play_turn())\n"
        "        if reply is not None:\n"
        "            police.on_turn(reply)\n"
        "print('police claims:', police.result)\n"
        "print('thief  claims:', thief.result)\n"
        "print('verdicts agree:', police.result['winner'] == thief.result['winner'])"
    ),
    md(
        "## 11. The verbal duel: lies, vagueness, and the motion judge\n\n"
        "The hint is the game's only deception channel - scent and movement cannot lie. "
        "Phase 8 measured what a lying thief does to a cop's belief (mean argmax error, "
        "in cells, over a full match against a pursuit cop that follows hints):\n\n"
        "| thief's hint policy | naive cop (trusts hints) | our cop (motion judge) |\n"
        "|---|---|---|\n"
        "| honest | 0.56 | **0.38** |\n"
        "| mislead (systematic lies) | **2.69** | 0.62 |\n"
        "| vague (no geometry) | 1.00 | 1.00 |\n\n"
        "Two findings shaped the shipped design. **First**: a single scent snapshot "
        "cannot verify a motion claim - a walk north and its mirrored lie scent the same "
        "cells, so our original snapshot judge let lies inflate our error to 2.69. The "
        "shipped TrustModel instead tracks the *displacement of the fresh-scent "
        "centroid* between consecutive turns and dots it with the claimed direction: "
        "truth corroborates, the mirror lie contradicts. Against it, lying is now "
        "*worse than silence* (0.62 vs 1.00): every detected lie damps the falsely "
        "claimed region, which is free negative evidence. **Second**: our own hints are "
        "governed by a configurable DeceptionPolicy. The cop's capture claims leak "
        "its belief argmax every turn, so the thief adapts - while claims wander, feed "
        "directional lies (poisons naive cops at 2.69); once claims land close, go "
        "vague, because against a motion judge the only unfalsifiable hint is one that "
        "claims nothing. The cop, which has no claim-feedback channel, ships vague "
        "permanently: zero leak, zero risk. And the wall cop's capture step is "
        "identical under every opponent hint policy - the opening wall consults no "
        "belief at all, so there is nothing for a lie to poison."
    ),
    md(
        "## 12. Token budget analysis (guidelines ch. 11)\n\n"
        "The verbal layer is the only token consumer. The cost model is parametric so the "
        "table survives price changes - counts are what the design fixes:"
    ),
    code(
        "import math\n\n"
        "steps_ceiling = contract.movement.max_moves\n"
        "every_n = int(config.private_value('trash_talk', 'every_n_steps', 3))\n"
        "games_per_series = contract.network.num_games\n"
        "budget = contract.network.token_budget_per_series\n"
        "# Measured envelope for one hint call (Haiku, 15-word cap enforced):\n"
        "input_per_call, output_per_call = 350, 40\n"
        "calls_per_game = math.ceil(steps_ceiling / every_n)\n"
        "tokens_per_game = calls_per_game * (input_per_call + output_per_call)\n"
        "series_total = tokens_per_game * games_per_series\n"
        "print(f'hint calls per mini-game : {calls_per_game} (every {every_n} steps, '\n"
        "      f'{steps_ceiling}-step ceiling)')\n"
        "print(f'tokens per mini-game     : {tokens_per_game:,} '\n"
        "      f'({input_per_call} in + {output_per_call} out per call)')\n"
        "print(f'tokens per series        : {series_total:,} of {budget:,} budget '\n"
        "      f'= {series_total / budget:.1%} utilization')\n"
        "print(f'region-cop reality check : captures at ~8 steps cut police-side calls '\n"
        "      f'to ~{math.ceil(8 / every_n)} per game')\n"
        "print('fallback ladder          : claude_api -> throttle -> budget guard -> '\n"
        "      'template (0 tokens), so a dead API never breaks the 15-word hint')"
    ),
]
