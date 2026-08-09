"""Notebook cells, part 5 of 5: Conclusions: three generations in one notebo.

Split from ``build_notebook.py`` under the 150-line rule. The notebook is
authored as code so every figure in the committed ``.ipynb`` is the output of a
real run rather than a pasted image; these modules hold the cell text and
``build_notebook.py`` concatenates them, in order, into one notebook.
"""

from __future__ import annotations

from _notebook_cells import md

CELLS = [
    md(
        "## 13. Conclusions: three generations in one notebook\n\n"
        "1. **Generation 0 - the pinch cop - was unfixable by tuning**: a flat 0% "
        "capture surface across its whole parameter grid. The parity dance (equal "
        "speeds, orthogonal moves, a trap trigger that never fires on the diagonal) is "
        "structural; no sweep repairs structure.\n"
        "2. **Generation 1 - the region cop** - inverted the objective from distance to "
        "*options* and converted 1900/1900 against reactive evaders in ~8 steps. Its "
        "parameters are robust (every reasonable cell of the sweep is identical) and its "
        "mechanism causal (the barrier-disabled control collapses to 0%).\n"
        "3. **The thief's answer exposed the cop**: a weighted blend of worst-case "
        "region, distance, openness and mobility (`EvadeThiefBrain`) survives the region "
        "cop on 60/72 starts. Lexicographic priorities lose; blends win. Any league "
        "opponent with an open-field evader would have beaten generation 1.\n"
        "4. **Generation 2 - the wall cop - closes the race**: an opening center wall "
        "with one guarded door (needing no position knowledge - immune to belief error), "
        "then the region hunt inside the thief's half. Exhaustive: **1900/1900 against "
        "every archetype including the strongest evader**, max 29 of 35 steps, max 8 of "
        "14 barriers.\n"
        "5. **The shipped pair** is therefore `WallPoliceBrain` + `EvadeThiefBrain`: the "
        "best attacker we could build, and the defender that beats everything except "
        "that attacker. A full belief-based networked self-play match confirms the "
        "transfer: agreed capture verdict on both peers.\n"
        "5b. **Red-teaming found what validation could not**: specialist anti-wall thieves exposed a pillar-orbit dance no archetype triggered; the repetition-triggered stone now converts it, and all six archetypes fall 1900/1900 (worst case 32 of 35 steps, 10 of 14 stones).\n"
        "6. **The verbal layer is now asymmetric warfare**: our motion judge turns opponents' lies into negative evidence (their lying scores 0.62, worse than their silence at 1.00), while our adaptive deception still poisons naive opponents (2.69) and goes safely vague against sophisticated ones.\n"
        "7. **Token budget is comfortable**: worst-case series utilization is a small "
        "fraction of the 200k cap, and the template fallback bounds the worst case at "
        "zero tokens."
    ),
]
