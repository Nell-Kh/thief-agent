# thief-agent — the THIEF agent

This repository submits **the THIEF agent** for the Police-Thief P2P league
(University of Haifa, "Orchestration of AI Agents", 2026). Its counterpart,
[`police-agent`](https://github.com/Nell-Kh/police-agent), submits the other role; the two repos share one
engine because the mutual audit requires each peer to re-verify the other's
physics (the partition decision is documented in the report below).

Run this peer:

```
uv run python -m police_thief peer --role thief
```

Gates: `uv run ruff check src scripts tests` and `uv run pytest` (coverage ≥85%).

The submission is the annotated tag `v1.0-submission` on this branch's tip.
The full commit-by-commit development history (both authors, original hashes -
the `github_commit` stamps sealed in every game log resolve here) sits directly
beneath this banner commit; the development story (branches, PRDs, PLAN, TODO -
rule 9.4.1) is carried in `docs/`. This tree was assembled from the git index of
the development repository, <https://github.com/Nell-Kh/police-thief-p2p>, by
`scripts/split_repos.py`.

---

# Police-Thief P2P — Distributed Cops-and-Robbers over a Peer-to-Peer Network

**Final project, "Orchestration of AI Agents" — Dept. of Computer Science, University of Haifa, 2026.**
**Team code:** `yanell11` · **Version:** 1.00 · **Tag:** `v1.0-submission` *(annotated, pushed in both submission repos)*

Two autonomous agents — **cop** and **thief** — race on a discrete grid with **no central server
and no referee**: P2P over FastMCP, SHA-256 commit-reveal integrity, decaying pheromone scent
fields, Bayesian belief maps, deceptive natural-language hints, a local-truth GUI, and a
cryptographic Replay Viewer. This document is the project's academic report (rulebook rule #42):
system overview, the Dec-POMDP formalism behind it, the orchestration dilemmas we had to solve,
three generations of strategy work with measured tables, the deception findings, the interop
conformance chapter, and an honest self-grade of the code.

---

## Table of contents

1. [Quick start](#quick-start)
2. [Abstract & system overview](#1-abstract--system-overview)
3. [The Dec-POMDP formalism](#2-the-dec-pomdp-formalism)
4. [Belief machinery](#3-belief-machinery-scent-evidence-motion-judge-negative-evidence-claim-pin)
5. [Orchestration dilemmas](#4-orchestration-dilemmas-turns-failures-gatekeeperorchestrator)
6. [Strategy generation 0–1 — pinch failure and the region cop](#5-strategy-generation-01--pinch-failure-and-the-region-cop)
7. [Strategy generation 2 — wall cop, red team, hybrid frontier](#6-strategy-generation-2--wall-cop-red-team-hybrid-frontier)
8. [The verbal layer & deception economics](#7-the-verbal-layer--deception-economics)
9. [Interop chapter — the kit, the vectors, the bytes we fixed](#8-interop-chapter--the-kit-the-vectors-the-bytes-we-fixed)
10. [Results tables](#9-results-tables-reproduced-from-notebooksanalysisipynb)
11. [Screenshots](#10-screenshots)
12. [Cross-repo links](#11-cross-repo-links)
13. [Code-quality self-grade (rule #55)](#12-code-quality-self-grade-rule-55)
    - [12.1 Five decisions the rules do not require](#121-five-decisions-the-rules-do-not-require)
14. [Limitations & future work](#13-limitations--future-work)
15. [Documentation index](#documentation-index)

---

## Quick start

```bash
uv sync

# Terminal 1
uv run python -m police_thief peer --role police
# Terminal 2
uv run python -m police_thief peer --role thief

# Replay a saved match
uv run python -m police_thief replay --log logs/log_<game_id>_g01.json

# Tests & lint
uv run pytest
uv run ruff check .
```

Config: shared, signed game contract `config/game.json` (mirrors the rulebook's Mandatory
Parameters Table, Appendix ו; byte-identical on both peers, locked via SHA-256). Private
per-peer settings: `config/police/game.toml`, `config/thief/game.toml` (overlay rule: shared
JSON overrides private TOML). Secrets live in `.env` / `credentials.json` / `token.json` — all
git-ignored; see `.env-example`. League exposure: [docs/TUNNELING.md](docs/TUNNELING.md).

---

## 1. Abstract & system overview

Cop and thief are two fully separate OS processes, each simultaneously a FastMCP **server**
(exposing tools to the opponent) and a FastMCP **client** (calling the opponent's tools).
Neither process holds the other's true position — there is no referee and no shared memory.
Each side reconstructs the game from its own local truth: its own moves, the opponent's decaying
scent field, and the opponent's natural-language hints, which may be lies. Every move is
protected by a SHA-256 commit-reveal scheme, so integrity does not depend on either side's
honesty — it depends on a hash function. At game end a two-layer mutual audit (hash replay +
trajectory physics) either agrees a verdict or exposes a forgery as a technical loss.

**C4 context:**

```
+----------------+        commits/reveals/hints over MCP  +----------------+
|  POLICE peer   | <---   (via public tunnel URLs)   ---> |   THIEF peer   |
+-------+--------+                                        +--------+-------+
        |                                                          |
        | Gmail API (send-only, JSON attachment)                   |
        v                                                          v
+-------+---------+     game-end reports      +--------------------------+
| Lecturer inbox  | <------------------------  |  Anthropic API (Haiku)  |
+-----------------+                            |  verbal layer only     |
                                                +--------------------------+
```

**C4 containers (one per peer process):** a Tkinter GUI rendering local truth only; a FastMCP
server for inbound tools; an MCP client for outbound calls; the Orchestrator runtime (state
machine, deadline tracker, watchdog); file-based storage (`config/`, `logs/`, `results/`). A
separate Replay Viewer process loads saved logs offline. Full component/code views:
[docs/PLAN.md §1](docs/PLAN.md).

**Why this shape.** The rulebook forbids a referee (#1/#2) and forbids showing the objective
board (#8/#9); the only way to build a competitive, honest agent under those constraints is to
make every claim self-verifying (crypto) and every inference probabilistic (belief). The rest of
this report walks through the formal model (§2), how belief is actually computed (§3), the
reliability engineering that keeps two independent processes from deadlocking each other (§4),
three generations of strategy work (§5–§6), what we learned about lying over a scent channel
(§7), and how we made our wire format interoperate with an independently authored kit (§8).

**Five decisions the rulebook does not require.** Most of this project implements a
specification. These five do not — each exists because a specific failure was possible, was
going to be silent, and was going to cost points in a way nobody could reconstruct afterwards.
They are the parts we would defend in a review, and each is evidenced in
[§12.1](#121-five-decisions-the-rules-do-not-require):

| | Decision | The silent failure it prevents |
|---|---|---|
| 1 | **Audit physics, not just hashes** (`domain/audit.py`) | A perfectly hash-consistent log that teleports, moves diagonally, or walks through a declared barrier |
| 2 | **A hostile peer forfeits instead of crashing us** (`domain/audit.py::_disclosed_records`, 17 fuzz tests) | Their malformed disclosure taking our process down, turning their forfeit into our technical loss |
| 3 | **The containment alarm accuses us first** (`services/series_guard.py`) | Six contained sub-games reporting as a tidy 2–2 series while our own driver was the thing that was broken |
| 4 | **A counted claim must be addressed to count** (`infra/email/report_blocks.py::_is_armed`) | A misconfigured recipient turning a won series into a rule-#38 false declaration |
| 5 | **Find the refusal the night before** (`shared/preflight.py`) | Discovering a one-key contract disagreement at kickoff, with both teams waiting |

## 2. The Dec-POMDP formalism

The game is a two-agent, general-sum **decentralized partially observable Markov decision
process**, ⟨n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ⟩ with n = 2 (police *p*, thief *t*):

- **State space `S`.** `(pos_p, pos_t, barriers, step)` — both agents' cells on a
  `grid_size × grid_size` board (minimum 7×7), the set of placed barrier cells (irreversible,
  quota `max_barriers = 14`), and the step counter (ceiling `max_moves = survival_threshold =
  35`). `domain/state.py::GameState` is the code's ground truth; it exists once per process and
  is never transmitted.
- **Action space `Aᵢ`.** `{N, S, E, W, STAY}` for both roles (`constants.MOVE_DELTAS` — diagonals
  are unrepresentable, not merely rejected); the police additionally has a barrier-placement
  action, legal only on a STAY turn, on its own cell or an orthogonal neighbor, subject to the
  quota. `domain/rules.py` is the sole source of legality (`legal_moves`, `validate_move`).
- **Transition function `P`.** Deterministic given the joint action and the barrier set: a
  legal move updates one coordinate; STAY (with or without a barrier) updates none; capture is
  detected on coordinate overlap, on a barrier landing on the thief's cell (#46), or on the
  thief having zero legal exits (#47, `rules.is_trapped`). `domain/engine.py::apply/end_turn`
  implements `P` and the termination check in one place.
- **Reward `R`.** The fixed scoring table from `config/game.json` (capture 20/5, survival 5/10,
  tie 2, technical loss 0/0 — `domain/scoring.py`), applied at game end per role. `R` is common
  knowledge (part of the signed contract) even though `S` at any given time is not.
- **Observation function `Ωᵢ`.** Each agent observes only: its own position and step-local
  board state; the *opponent's* scent field (never its own — local-truth discipline, rule #8);
  and the opponent's verbal hint for that turn, which may misrepresent intent. It never observes
  `pos_opponent` directly. `services/world_view.py::WorldView` is the object with literally no
  field capable of holding the opponent's true position — rule #9 is enforced by the schema, not
  by a runtime check that could be bypassed.
- **Observation model `O`.** `P(Ωᵢ | S, A)` is exactly the pheromone emission/decay model of §3:
  a deterministic function of the joint action history, cryptographically locked pre-series
  (rule #23) so both agents provably share the same `O`.
- **Discount `γ`.** Effectively 1 within a mini-game (finite horizon, `max_moves` bounded); the
  scoring table's capture/survival split is what makes early termination valuable, standing in
  for discounting across the fixed 35-step ceiling.

The **decentralized** part is structural, not incidental: there is no central controller with
joint-state access (that would be a referee, forbidden by #1/#2), so each agent must maintain and
act on its own posterior over `S` — the belief map of §3 is the Dec-POMDP's belief state,
computed independently and never reconciled except at the end-of-game audit (which reconciles
*history*, not *belief*).

## 3. Belief machinery: scent evidence, motion judge, negative evidence, claim pin

`domain/belief.py::BeliefMap` holds a `grid_size × grid_size` probability distribution over the
opponent's cell, updated once per own turn in three stages:

1. **Motion diffusion (the "judge").** The previous posterior is spread across each cell's legal
   neighbors (barriers excluded), modeling "the opponent moved somewhere reachable since I last
   updated" — this is the prior for the new step, not a re-derivation from scratch.
2. **Scent likelihood.** The opponent's own scent field (Figure 4's fixed 5×5 emission matrix,
   center 0.90, decaying by `τ(t+1) = max(0, (1-ρ)·τ(t) + Δτ)` with ρ = 0.10 — verbatim, tested
   digit-for-digit in `test_scent.py`) is read and used as a multiplicative likelihood: warm
   cells become more probable, barrier cells are pinned to zero, and the result is renormalized.
   The value 0.81 (= 0.9 × 0.9, one decay step from peak) is the yardstick `expected_fresh_trail`
   uses throughout the trust model.
3. **Hint fusion and negative evidence.** A decoded verbal hint contributes a direction/region
   likelihood term weighted by the EWMA trust coefficient from `domain/trust.py` (§7); a
   **truthful "not caught" answer** to a capture claim is negative evidence — `belief.exclude`
   zeroes that one cell without needing a positive sighting, closing a real gap we found only
   once we started testing over the live wire (§4, §5.6).

On top of the base model (compatible with the reference belief scheme) we ship two competitive
additions, both load-bearing for conversion in §5–§6: **barrier-aware diffusion** (motion spreads
only across non-barrier neighbors, so belief mass never leaks through a wall a moment after it
goes up) and **verified-claim pinning** (`hybrid.py`/§6): when the cop's own scent independently
corroborates a thief claim, belief collapses ~25× faster onto that cell instead of decaying at the
ordinary trust rate. Every stage is barrier-aware, renormalizing, and covered by property tests
for the two invariants that actually matter operationally: Σp = 1 after every update, and
`p(barrier cell) = 0` always (`test_belief.py`, 17 tests).

## 4. Orchestration dilemmas: turns, failures, gatekeeper/orchestrator

Building the reliability layer meant repeatedly answering the same question the rulebook poses
explicitly (ch. 8): *what happens when the world fails at exactly the wrong moment?*

- **Turn-taking without a referee.** `services/turn_taking.py` / `turn_receiving.py` implement
  the commit → ack → reveal → apply cycle from ADR-7: the wire carries *only* a commit hash, the
  hint, the sender's scent grid, and public events (barrier declaration, capture claim/answer,
  concession) — never a raw position. `services/match_runtime.py` is the single object that owns
  one peer's full mini-game loop; nothing else is allowed to drive it (rule #3).
- **State machine as the first line of defense.** `services/phase_machine.py` encodes exactly six
  states and the legal-transition table from PLAN §2; any other transition raises immediately.
  This turned what would otherwise be silent, hard-to-reproduce deadlocks (two processes each
  waiting on the other, with no crash and no error) into loud, testable, development-time
  exceptions (`test_phase_machine.py`, 14 tests over every legal and illegal edge).
- **Deadlines are a failure mode, not patience.** `services/deadline.py::DeadlineTracker` puts an
  expiry on every outbound MCP call (30 s default), with bounded retries and backoff from config;
  exhaustion drives the phase machine to `TECHNICAL_LOSS` and closes the turn cleanly instead of
  hanging. `docs/TUNNELING.md` documents the observed consequence: a dead opponent tunnel yields a
  clean technical loss in ~11 s, never a hang.
- **The watchdog is a second, independent clock.** `services/watchdog.py` monitors heartbeats
  from the main loop itself (not from the network) — a hung *local* process (e.g., a runaway
  brain computation) gets the same controlled persist-then-shutdown treatment as a dead
  opponent, via `recovery.py`'s crash-rescue path that preserves the logbook so a killed process
  can resume from disk rather than losing a game's audit trail.
- **At-least-once delivery over an unreliable channel (kit 7.1).** Once we started fuzzing our
  own wire, retried commits reappeared even on a healthy connection (client-side retry policy vs
  server-side idempotency is a genuinely separate concern). `services/enforcement.py` now dedupes
  on `(step, commit)`: the identical retransmission is absorbed idempotently and never renews a
  deadline, but the *same step with a different commit* — equivocation — stays loud and refuses.
  A capacity-2 reorder buffer replays out-of-order steps in order rather than rejecting them
  outright. Both behaviors are pinned against the kit's own `delivery_contract.json` decision
  table (§8), not just our own intuition of "reasonable."
- **The gatekeeper is the orchestrator's mirror image for outbound email.** `shared/gatekeeper.py`
  composes a token bucket (verbatim refill law, injected clock), a daily quota, and a DOS lock
  behind a FIFO queue, so the one truly external, rate-limited resource (Gmail) can never be
  hammered by a bug in the game loop — the orchestrator protects *turns*, the gatekeeper protects
  *the account*, and neither module is aware of the other's existence (rule #3's "single gateway"
  read literally: two gateways, two concerns, zero cross-talk).
- **The concession that had to be spoken, not inferred.** Our first live-network capture
  (`8.20`) revealed a real orchestration bug hiding as a strategy bug: a trapped thief simply
  went silent, and the cop — correctly, per rule #21/#22 — never assumed a capture it had not been
  told about. The fix was not smarter inference; it was making rule #47 ("no legal move ⇒
  captured") a spoken event: `services/turn_taking.py` now emits a sealed, auditable concession
  message the instant the thief detects its own trap, and `services/inbound.py` distinguishes
  that concession from an ordinary claim answer so a legacy `win_claim` message still works. The
  lesson generalizes: in a system with no referee, *every* terminal condition must be an
  explicit, sealed message — an inferred ending is a disagreement waiting to happen.

## 5. Strategy generation 0–1 — pinch failure and the region cop

**Generation 0 (blind).** With a degenerate belief (opponent position known exactly), the cop
brain follows a barrier-aware BFS shortest path (`brain/pathfind.py`) with no manual
intervention — the M3 milestone. This isolates *decision correctness* from *uncertainty*, and is
also the honest baseline every later number in this report is measured against.

**Generation 1, first attempt: the pinch cop.** Our first belief-driven cop targeted the argmax
of the belief map and used its remaining barrier quota to "pinch" the thief's estimated corridor.
Sweeping the pinch parameters across the full configuration space in the research notebook
(`notebooks/analysis.ipynb` §1) produced a flat **0% capture surface** — not a tuning problem, a
design flaw. §2 of the notebook diagnoses it with a distance trace: the cop and a competent
evader fall into a **parity dance**, a stable oscillation where the cop's BFS-shortest response to
the current belief argmax is always one parity class away from actually closing distance, because
chasing a *point estimate* discards exactly the information (spread of the distribution) needed to
cut off an evader who is reacting to the same estimate.

**Generation 1, the fix: the region cop.** `brain/region.py` replaces "chase the argmax" with
**minimize the thief's reachable safe region**: rather than a single target cell, it treats the
whole set of cells consistent with high belief mass as the target and chooses barrier placements
that shrink that region monotonically (with exit-count tie-breaks and quota guards so it never
over-commits early). Fixing a `distance_field` `-1`-for-unreachable off-by-one (`_reach`) was the
last correctness bug standing between the design and the numbers: **1900/1900** captures across
the full exhaustive pairing grid, mean 7.8 steps to capture, worst case 11 steps, using roughly 2
of the 14 barriers on average (`notebooks/analysis.ipynb` §3–§6; `test_region_brain.py`).

The throughline for §5–§6: **minimizing an opponent's reachable space beats chasing a point
estimate of their position**, whether the estimate comes from truth (generation 0), belief
(generation 1), or a hostile, evolved adversary (generation 2, next).

## 6. Strategy generation 2 — wall cop, red team, hybrid frontier

**The arms race.** A region cop that is *unbeaten* against reference-shaped thieves is not the
same claim as *unbeatable*; we treated our own region cop as the opponent to attack.
`brain/evade.py` is a worst-case-region evader found via a weight-blend search over a
multi-objective score (region size, cop distance, openness, mobility) after **lexicographic**
orderings of the same objectives consistently lost — a searchable design lesson in its own right,
not just a numeric one: ranking sub-goals discards exactly the trade-off information a blend
preserves. The evolved evader won **60 of 72** rounds against the plain region cop.

**Round 2: the wall cop.** `brain/wall.py` answers not with a smarter chase but with a change of
plan: commit early to a center wall with one guarded door, collapsing the board into a
smaller region before falling back to region-hunt logic once the thief is contained. Several
minimax-style and explicit anti-dance cop designs were attempted and *rejected* as failed designs
(documented, not deleted, in `notebooks/analysis.ipynb` §7–§8) before the wall-then-hunt
combination proved both simple and robust. Exhaustive validation across **every archetype** in
the project (blind, region, evade, wall, hybrid) reached **1900/1900** captures, worst-case 29 of
35 steps, worst-case barrier usage 8 of 14.

**Red team.** We then built three purpose-built attackers against our *own* wall cop —
`DoorCamper`, `SideFlipper`, `WallBlocker` — and found one genuine hole: a **pillar-orbit** pattern
(2 losses out of 192 trials) where a hunting barrier stone became an unintended merry-go-round
around a pillar cell. The fix is a **dance-breaker**: a repeated-state detector that spends one
anchored, hunt-preserving barrier to break the cycle rather than adding a special case for the
specific orbit shape found. Re-validated exhaustively afterward across six archetypes at
**1900/1900**, worst case 32 of 35 steps — the fix generalized rather than just patching the
observed instance, which we confirmed by construction (the detector is topology-agnostic) rather
than by hoping the red team hadn't found everything.

**The hybrid frontier — and why it is not the default.** `brain/hybrid.py` adds three
"commit tripwires" (irreversible wall-commitment triggers) on top of the wall cop, chasing a
speed/margin trade-off. Under **perfect information** it is genuinely stronger against weak
thieves (1900/1900, mean 12 steps) but **weaker against our own elite evader** (1891/1900) — a
real regression, not noise, and the original reason it was documented as a *selectable* profile
rather than promoted to default.

**That trade-off does not survive contact with belief.** Re-measured under the only conditions a
league match is ever played in — inferred positions, from the contract's fixed start — the
hybrid's speed advantage inverts:

| cop (belief, fixed start) | vs. blind thief | vs. enhanced thief | vs. elite evader (§6c) |
|---|---|---|---|
| Wall | capture @ 24 | capture @ 24 | **survival** |
| Hybrid | capture @ 25 | capture @ 25 | **survival** |
| **Seal** (default) | capture @ 25 | capture @ 25 | **survival** |

*Those are the numbers **after** the emitter fit below. Before it the same table read
wall 28/28/**survival**, hybrid 34/34/**survival**, seal 29/29/**capture @30** — one cop
converting the elite evader, which is why `seal` was written and why it is still shipped.*

The opening hunt burns tempo chasing a belief argmax that is still diffuse, so the wall closes
*later* than it would have unopened, and the elite evader escapes both. There is therefore no
opponent class for which the hybrid is the better league choice, and the config now says so
outright instead of offering it as a peer alternative. The class and its tests stay, because the
perfect-information frontier they map is a real result — and because the gap between the two
tables is itself the finding: **a strategy validated only under perfect information can invert
under belief, so every strategic claim in this project is now stated with its information
condition attached.**

### 6b. The emitter fit — locating a peer that publishes a plateau

A live opponent (`sharNamr`, 2026-08-15) reported that our cop was blind to them, and the cause
was ours as much as theirs. The transmitted `smell_grid` is the **whole accumulated trail**, and
every conformant model **clamps** it at `emit_intensity`; after a few moves the maximum is
therefore a *plateau* — measured at **13 of 49 cells** on our own field — so `belief.argmax()`
answered with whatever the tie-break happened to order first. Both roles were steering by a
phantom, and no amount of strategy work would have fixed it.

The cure is to stop reading the peak and invert the model instead: for every candidate cell,
predict the field that cell's emission would produce from last turn's field, and keep the best
fit (`domain/emitter.py`). Against our registered `multiplicative_book_v1` it is exact — **8 of 8**
cells on a moving path, zero residual — and against a peer on another reading it degrades to
"the nearest cell that explains the field" instead of failing.

The measured consequence is the table above: **every barrier cop now converts every archetype**,
captures land 4–5 steps sooner, and the pure-pursuit cop still cannot convert (equal speed with
no stones is the parity dance of §5). It also changed what the strategy gate can honestly assert:
with three cops converting everything, "who ranks first" is decided by a speed tie-break worth
zero points, so `tests/integration/test_strategy_selection.py` now pins **conversion** — the
property the rulebook pays for — and names the converting set, rather than crowning a winner.
`seal` remained the shipped cop through round 4 because its conversion is structural (cross the door, spend a
stone on it, hunt a closed chamber) where `wall`'s now rests on the belief being precise.

### 6c. Round 4 — a stone is a wall

With every barrier cop converting every thief (§6b), the next question was whether the thief
could be brought back. Deeper pessimism did not do it: extending the max-min horizon from one
cop reply to four changed **not a single game**. So instead of tuning weights we traced a lost
game under belief, and the mistake was visible by step 16 — the thief kept drifting into the
**doorway** of the wall the cop had just built, then got sealed into the half the cop had
entered and hunted down in a closed chamber.

The cause was one function. `openness()` scored "distance from the nearest **edge**" — a static
board property that cannot see a barrier — while its own docstring claimed walls were what it
existed to avoid. On a walled board the most "open" cell by that measure is the door: the exact
cell a wall cop wants the thief standing in. Counting a placed stone as a wall (and re-weighting
distance and mobility with it) is the whole change:

| thief (belief, fixed start) | blind | enhanced | region | wall | hybrid | seal |
|---|---|---|---|---|---|---|
| evade, edge-only openness | survives | survives | survives | caught @25 | caught @29 | caught @26 |
| **evade, a stone is a wall** | survives | survives | survives | **survives** | **survives** | **survives** |

It holds under perfect information too, from three separate starts
(`test_wall_and_evade.py`), so it is not an artifact of the belief pipeline. The arms race now
stands at: no cop in this tree converts our elite evader, and
`test_strategy_selection.py::test_no_cop_in_the_tree_converts_the_elite_evader` is the test a
round-5 cop must break.

### 6d. Round 5 — search where the seal cop danced

The round-4 thief was then met for real. Against a live opponent whose thief had become
elite-class overnight (sharNamr, 2026-08-17) our cop went 0-for-3, and it was not a fault of
information: under **perfect** information from the contract's fixed start, not one of the four
barrier cops converted our own evader, and the best of them (`seal`) converted 11 of 60 sampled
starts. The trace of the loss says exactly where the game goes. The wall is up by turn 14; four
turns are then spent walking back to the door; the door is sealed at turn 20 — and the position
is a closed 3×7 chamber holding cop, thief and seven stones with fifteen turns left. The
inherited region hunt then dances between (3,4) and (4,4) for all fifteen while the thief sits in
the far corner. The opening is right; the endgame loses.

The evader's whole edge is that it prices the cop's best reply before it moves — one ply of
pessimism — while every cop before this one planned zero plies ahead. `brain/search.py` is a
two-ply minimax (cop, thief, cop, thief, evaluate) over the cop's steps and stones, alpha-beta
pruned, valuing a position by the thief's safe region, its exits and its distance. On the open
board it is too wide to afford and too shallow to see a wall pay off; with the board halved it is
cheap and decisive. `brain/box.py` keeps the seal cop's opening untouched and hands the position
to the search **the moment the wall stands**. Where that hand-off sits was measured, not chosen:
handing over before the wall is complete is catastrophic (0 of 40 starts — a two-ply horizon
never finishes a wall), and handing over only once the door is stoned costs a step. Structure by
plan; the moment it exists, search.

| condition | seal | **box** |
|---|---|---|
| from the turn-20 chamber, 15 turns, perfect information | survival | **capture in 5** |
| fixed start, perfect information | survival | **capture @24** |
| 60 sampled starts, perfect information | 11 captures | **60 captures**, mean 25.7, worst 30 |
| fixed start, **belief**, real pipeline — vs blind / enhanced / evade | @26 / @26 / survival | **@27 / @27 / @25** |

**Red team.** "Converts our three thieves" is the wrong bar for "as strong as possible", so
`tests/adversaries/` holds thieves that do not ship, each written to attack one assumption of the
plan: a **two-ply search thief** (the cop's own weapon, mirrored), a **door camper** that loves the
doorway and the cop's side of the wall, a **wall-hugger** that never lets the halving separate them,
and a **pure distance runner**; plus, in the research harness, a late crosser, a side camper and a
one-ply searcher. Under perfect information from the fixed start and 20 sampled starts each: **8
adversaries, 160 of 160 starts converted**, mean 25.6–26.6 steps. `test_red_team_cop.py` holds the
fixed start of every shipped adversary and a six-start spread as the regression guard.

The arms race now stands at: `box` converts every thief in the tree including our own elite
evader and every adversary built to break it, and
`test_strategy_selection.py::test_exactly_the_round_five_cop_converts_the_elite_evader` is the
test a round-6 thief must break.

**Determinism, redefined.** Along the way "deterministic" stopped meaning "the same object always
decides the same way" (true but uninteresting) and came to mean the operationally relevant claim:
**a freshly constructed brain, given the same state, makes the same decision** — the property
that actually matters for reproducible replays and for red-teaming an opponent's exact published
behavior rather than an instance's incidental internal counters.

## 7. The verbal layer & deception economics

Hints are free natural language (rules #26/#27 — never coordinates), capped at 15 words, produced
by a provider chain (`template` deterministic fallback → `ollama` → `claude_api`/Haiku, our
default) that always degrades gracefully to the zero-token template on any failure, so a game
never stalls on an LLM outage. The `Intent` flag (truth/lie) is decided by strategy, sealed into
the commit record, and the LLM never sees or influences movement (rule #25) — it composes text
for a decision already made.

**Measuring the cost of lying.** Before building a deception *policy* we measured the effect of
one against a naive, hint-trusting cop: an opponent that follows a lying hint accumulates belief
error rising from **0.56 to 2.69** (notebook §11) relative to a truthful baseline — the first hard
number establishing that lying is actually worth the cognitive and engineering cost of doing it
well, rather than an assumed-valuable feature.

**A temporal trust model, not a snapshot one.** `domain/trust.py` compares the *displacement* of
the opponent's scent centroid between turns against the direction the hint claimed, rather than a
single-frame intensity check — the naive check is defeated trivially by an opponent standing
still and lying about direction (no motion to contradict); the temporal check catches it because
displacement, not intensity, is what a direction claim actually predicts.

**An adaptive deception policy, not a coin flip.** `services/deception.py`'s `DeceptionPolicy`
selects among honest / mislead / vague / adaptive styles, with the adaptive style adjusting its
lie rate off the *opponent's own claim-gap feedback* (how far their belief argmax lands from
truth after each hint) — lying more against an opponent who is demonstrably not catching on, and
throttling back against one who is. The vague style is generated through both the template and
the Haiku prompt paths; one iteration's Haiku output leaked the phrase "right now" (an implicit
truthful timestamp inside a supposedly vague sentence) and had to be caught and constrained
explicitly in the prompt — a small, concrete example of why every LLM-authored hint is still
validated structurally (`validate_hint`) before it ever reaches the wire, never trusted as-is.

**The headline result.** Against our own belief-driven cop, actively lying (belief error 0.62)
turned out to be *worse for the thief than staying silent* (1.00, i.e. no hint at all) — because
a detected lie is redirected evidence, not neutral noise: our trust model uses a caught
contradiction to push belief mass *toward* the true scent concentration, so a naive liar poisons
their own position estimate for us more effectively than silence would have. The practical
takeaway carried into brain design: **deception is a tool for degrading a weak, hint-trusting
opponent, not a universal advantage — and it must be evaluated against the specific belief model
on the other end**, not assumed to help unconditionally.

## 8. Interop chapter — the kit, the vectors, the bytes we fixed

Late in the project we obtained the league's independent interoperability kit
(`copthief-league-protocol`, MIT-licensed) — a full 1032-line `SPEC.md` plus vendored test
vectors — built to let two teams' independently written implementations agree on every
byte that crosses the audit boundary, because a mismatch at audit time scores **both** teams
zero regardless of who is "right." We vendored the kit's license and 14 vector fixtures verbatim
under `tests/vectors/` and wrote `tests/interop/test_kit_vectors.py`: 11 tests that each feed a
vendored vector through *our* code and demand byte-exact equality, the same standard the kit's
own `verify_vectors.py` holds itself to.

**What we had to change, and why it mattered:**

- **IEEE floating-point drift in the scent kernel.** Our originally *computed* emission values
  matched the spec's formula but drifted from the kit's vectors in the last bit or two of a
  `float` — the classic trap of two independently-implemented floating-point pipelines being
  "equivalent" mathematically but not byte-identical. The fix was to replace the computed values
  with a verbatim lookup table matching the registered `multiplicative_book_v1` model exactly,
  rather than trying to chase bit-for-bit equivalence through arithmetic — the scent model is a
  *contract*, not a formula to be re-derived, once a canonical registered version exists.
- **The scent lock moved from "our own hash of our own formula" to the registered book.** Rule
  #23 requires the model be locked pre-series; we now lock against the kit's own registered
  `multiplicative_book_v1` document instead of a self-described formula string, so two independently
  written peers converge on the identical lock value without needing to exchange source code.
- **The wire terms shape flattened to 14 keys** (`shared/interop.py::terms_from_contract`) to
  match the kit's `terms_signature` fixture, with `sign_terms`/`derive_game_ids` producing the
  exact `game_uid`/`game_id` derivation the kit's `derive_starts` and `game_uid` vectors pin.
- **At-least-once delivery and the zero-step capture final** (§4, §6.13) were both driven
  directly by kit fixtures — `delivery_contract.json`'s decision table and the kit's `3.1`
  capture-final shape (`claim_response {claim: [own cell], caught: true}`) — rather than by our
  own guess at "reasonable" wire behavior, which is exactly the point of an interop kit: it
  replaces mutual guessing about edge cases with a shared, testable ground truth.

### 8.1 The declared contradiction: which reading of the book we speak

The rulebook's front matter says nothing binds unless it says so, and its
academic-freedom clause permits resolving a contradiction either way **provided
the choice, its location and its reasoning are stated**. This section is that
statement. Four places in this project follow the kit and the reference peer it
pins rather than the book's printed formulae:

| # | Fork | Book says | We do (`kit`) | Source |
|---|---|---|---|---|
| 1 | Commit seal | `sha256(canonical({state,move,intent,nonce}))` — nonce **inside** the JSON | `sha256(canonical(payload) + "\|" + nonce)` — nonce appended | ch. 5.3.1 vs kit `commit_reveal` (CORE) |
| 2 | Scent update | `tau' = max(0, (1-rho)*tau + delta)` — one clamp, at zero | additionally clamped above at `emit_intensity` | ch. 4.3 vs registered `multiplicative_book_v1` |
| 3 | Settlement hash | one canonical form throughout, compact | spaced separators for the settlement preimage only | ch. 5.3 vs kit `report_consensus` (CORE) |
| 4 | Signed terms | the App. B field set | adds `min_center_intensity` (14 keys, not 13) | App. B vs kit `terms_signature` (CORE) |

**Why we chose the kit column.** These are not stylistic. Fork 1 changes every
digest in every log; fork 2 diverges on the first re-emission (`0.9*0.9 + 0.9 =
1.71` clamps to `0.9`, unclamped it converges on 9.0) and the field crosses the
wire each turn; fork 3 and 4 decide whether a handshake and a settlement can
complete at all. A pair that disagrees on any one of them fails the mutual audit
in **both** directions, and rules #19/#35 then score both teams zero regardless
of who was "right". The kit is the only artifact we have that two independently
written implementations have actually agreed on byte-for-byte, and its fixtures
are vendored here and re-derived on every test run.

**We are explicit that this is a bet, not a proof.** The graded authority is the
book. If the league converges on the printed formulae instead, all four forks
are wrong at once. So the choice is not baked in: `[interop].profile` in the
per-peer TOML selects `kit` (default) or `book`, each fork is implemented both
ways, and `tests/interop/test_dialect_divergence.py` pins the actual digests,
tau values, key counts and settlement hashes so neither dialect can silently
collapse into the other.

**It is declared on the wire.** `interop_profile` rides in the handshake beside
the locked-model hashes, and `negotiation._check_dialect` refuses a stated
difference in either direction — deliberately stricter than the model-family
rule, which tolerates silence. A dialect disagreement becomes a message you
answer before kickoff instead of a mutual zero discovered at the audit.

### 8.2 Two things the kit does not settle either

- **The tie award.** App. F table 17 gives `tie_score = 2` as "the score for
  each side when the accumulated score against an opponent ends in a tie" — and
  is silent on whether that *adds* to the sub-game totals or *replaces* them.
  The kit's `report_consensus` vector pins the settlement serialization and says
  nothing about aggregate semantics, so this forks `mutual_agreement.sha256`
  under **either** dialect. We read it as `add` (`[interop].tie_award`), declare
  it in the handshake, and refuse on mismatch.
- **Turn order.** The book genuinely does not fix one. We play cop-first. That
  is a free choice, but not a local one: two peers on opposite orders shake
  hands, play, and only then disagree about the board. Also declared, also
  refused on mismatch.

### 8.3 What we do not claim

`sign_terms` and `group_block`'s `signature` field keep their wire names because
that is what the league reads, but neither is a signature in the cryptographic
sense: both are unkeyed SHA-256 digests over data that travels in the same
document, so any party can recompute them. They detect corruption in transit;
they cannot prove authorship. Book ch. 5.5 asks for signing under a pre-supplied
key, and **this project does not implement that** — stated here rather than left
to be inferred from a field name.

Twelve vectors are conformance-checked byte-for-byte today (`canonical_json`, `commit_reveal`,
`delivery_contract`, `derive_starts`, `game_uid`, `joint_seed`, `locked_model`,
`pairing_declaration`, `pheromone`, `report_consensus`, `scent_book_v3`, `smell_binding`,
`terms_signature`, `uid_declaration`); the remaining report-alignment items (consensus signature
serialization, league bookkeeping fields, mutual sparring series against the kit's own reference
peer) are tracked as open work in `docs/TODO.md` §8.14–§8.15, since they require the kit's own
`sparring.cli` and a live cross-implementation run rather than a static vector.

## 9. Results tables (reproduced from `notebooks/analysis.ipynb`)

No reinforcement learning was used anywhere in this system — every brain is a hand-derived
heuristic, so the learning-curve requirement (README mandatory item 4, ch. 9.4.2) does not
apply. The empirical evidence standing in its place is the exhaustive tournament below:
every strategy generation against every archetype, across all start positions.

| Generation | Design | Capture rate | Mean steps | Max steps | Barrier use |
|---|---|---|---|---|---|
| 0 | Blind (known position, BFS) | n/a (oracle) | shortest-path | — | — |
| 1, attempt 1 | Pinch cop (argmax + corridor pinch) | **0%** (flat sweep) | — | — | — |
| 1, fix | Region cop (safe-region minimization) | **1900/1900** | 7.8 | 11 | ~2 / 14 |
| 2, round 1 | Evolved evader vs. region cop | cop: 12/72 | — | — | — |
| 2, round 2 | Wall cop vs. every archetype | **1900/1900** | — | 29/35 | 8/14 (worst) |
| 2, red team | Wall cop + dance-breaker, post-fix | **1900/1900** | — | 32/35 (worst) | — |
| 2, hybrid | Hybrid vs. weak thieves | **1900/1900** | 12 | — | — |
| 2, hybrid | Hybrid vs. elite evader | **1891/1900** | — | — | — (not default) |

All rows above are **perfect information**. Under belief, from the contract's fixed start:

| Condition (belief, fixed start) | Wall cop | Hybrid cop | Seal cop (shipped) |
|---|---|---|---|
| vs. blind thief | capture @ 24 | capture @ 25 | capture @ 25 |
| vs. enhanced thief | capture @ 24 | capture @ 25 | capture @ 25 |
| vs. elite evader (§6c) | survival | survival | survival |

The belief table is not a notebook figure copied by hand — it is re-derived on every test run.
`scripts/brain_tournament.py` plays every cop brain against every thief brain as full
`MatchRuntime` matches (real commit-reveal, scent, belief and deception layers; only the
transport is replaced by a direct hand-off), and `tests/integration/test_strategy_selection.py`
fails if the two `[strategy]` lines in the private TOMLs are no longer the brains that win.
That gate exists because the tournament numbers above were measured under *perfect information*
and the `[strategy]` choice is only ever paid out under belief — the one condition in which the
hybrid cop is slower, not faster. Steps are reported from the cop's own counter; the thief's
survival declaration lands one step later on its own clock.

| Deception condition (vs. our belief-driven cop) | Belief error |
|---|---|
| Naive lie (measured effect, before policy design) | 0.56 → 2.69 |
| Adaptive lying thief vs. our cop | 0.62 |
| Silence (no hint at all) | 1.00 |

| Reliability observation | Value |
|---|---|
| Timeout-to-technical-loss path (dead tunnel) | ~11 s, no hang |
| Messages per MCP session (was: one) | whole sub-game, held open — 8x faster on loopback, far more over TLS |
| Tunnel drop a turn now survives | 40 s of patience, inside the opponent's 60 s turn wait |
| Rule-47 ending, wire-validated (Blind/Enhanced thieves vs. wall cop) | captured @ step 28, agreed verdicts |
| Elite evader vs. wall cop, wire-validated | only design still surviving |

| Engineering | Value |
|---|---|
| Test suite | 974 tests collected (1 environment-dependent skip; the suite itself verifies this number) |
| Coverage | 97.61% (gate: ≥ 85%, `pyproject.toml fail_under=85`) |
| Token budget utilization (measured, full series) | ~14% of the ~200k series budget |
| Interop conformance vectors, byte-exact | 14 vendored fixtures, 14 dedicated tests |
| Dialect divergence (kit vs book), byte-exact | 8 dedicated tests, both profiles pinned |

Full methodology, every intermediate figure, and the exhaustive 1900-pair validation harness are
executed and version-controlled in `notebooks/analysis.ipynb` (built as code via
`scripts/build_notebook.py` and executed via `nbclient` — regeneration is deterministic, no
hand-edited output cells).

## 10. Screenshots

Captured from real self-play matches (task 9.3): `scripts/capture_live_gui.py` and
`scripts/capture_replay_viewer.py` each play a genuine two-runtime match (the
`tests/integration/test_two_peers.py` pattern) against the shipped `config/`, and
screen-grab the actual Tk windows — not mocked or hand-drawn.

- **Live GUI — belief heatmap.**

  ![Live GUI belief heatmap](docs/img/live_gui_belief_heatmap.png)

  Own position "C", one placed barrier, the belief heatmap with its "T?" argmax marker, and
  the turn banner — never the opponent's true cell, per rules #8/#9.

- **Replay Viewer — Verified OK.**

  ![Replay viewer Verified OK](docs/img/replay_verified_ok.png)

  Stepped to the final turn of a saved `log_<game_id>_g<NN>.json`; the green "Verified OK"
  stamp comes from `domain.replay`'s own re-verification of the sealed commit-reveal chain.

## 11. Cross-repo links

Per rules #49/#50, this development repo is split into two per-role repositories
(`police-agent`, `thief-agent`), each carrying its own README (cross-linking the other),
`config/`, PRDs, `PLAN.md`, `TODO.md`, and an annotated `v1.0-submission` tag. Both are
published, both are publicly reachable, and both links are mirrored into the result JSON's
four-link block (`reports.result_payload`):

- Police-agent repository: <https://github.com/Nell-Kh/police-agent>
- Thief-agent repository: <https://github.com/Nell-Kh/thief-agent>

Both trees are assembled from this repo's git index by `scripts/split_repos.py`, which also
writes each repo's role-banner README; `docs/SUBMISSION.md` §1 carries the runbook that grafts
the real development history underneath that banner, so each role repo shows the full
commit-by-commit story rather than one squashed tree. The same two URLs feed the result JSON's
four-link block from `[game].repos` in both per-peer TOMLs.

Only the front page differs between the two role repos: every other tracked path is
byte-identical to this one. Rule #50 sets a floor, not a ceiling, and the mutual audit obliges
each peer to re-verify the other's physics, so neither repo can be reduced to "its own half" of
the engine — see `scripts/split_repos.py` for the partition decision in full.

## 12. Code-quality self-grade (rule #55)

Rule #55 restricts self-grading to code quality, never the league outcome — the following is
that, and only that, measured against this repository's own standing definition of done
(`docs/TODO.md`, front matter):

- **Tests & coverage:** 974 tests collected, 97.55% coverage against an 85%-floor gate that fails
  the whole suite if crossed — this is a hard CI gate, not an aspiration. The suite count is
  asserted by the suite itself (`test_readme_integrity.py`), so this line cannot silently rot.
- **Lint:** `ruff check .` clean against the configured rule families (E,F,W,I,N,UP,B,C4,SIM),
  line length 100, target py310.
- **150-line law:** every file under `src/`, `scripts/` and `tests/` is within the limit, and
  `tests/unit/test_file_size_law.py` enforces it as a test rather than a claim. The debt list
  `KNOWN_OVER_LIMIT` is **empty**: the three developer scripts that used to sit in it were split
  (`build_notebook.py` 506 → 28 code lines behind `_notebook_part1..5`; the two series drivers
  into CLI, declaration and per-sub-game modules) rather than exempted. The guidelines are
  genuinely ambiguous about whether docstrings count toward the cap — ch. 3.2 excludes blanks
  and comments and is silent on them, the p.24 card counts them in — so rather than argue for
  the lenient reading, **every `src/` module now passes under both**, pinned by a second test.
  The interpretation is no longer load-bearing.
- **Docstrings:** 0 gaps for modules, classes, fixtures and helpers across `src/`, `scripts/`
  and `tests/`. Test *functions* are a declared exception — their names are full sentences, and
  a docstring restating the name adds a line and no information — and the exception is enforced
  by `tests/unit/test_docstring_law.py`, which requires an undocumented test to have at least
  four words after `test_`. It caught 7 short names; all 7 were documented rather than the
  threshold lowered to fit them.
- **Documentation-first process:** every mechanism has a dedicated PRD written and reviewed
  before its code; `docs/PLAN.md` records eight ADRs with trade-offs, not just decisions;
  `docs/COMPLIANCE.md` traces every one of the rulebook's 55 rules to a module and a proving
  test, not to a paragraph of prose.
- **Configuration discipline:** zero hardcoded gameplay values — every binding number traces to
  `config/game.json` or a per-peer TOML, pinned against Appendix ו by
  `test_contract_values.py`.
- **Determinism:** replays are byte-reproducible; brain decisions are a pure function of state,
  not of instance history (§6) — a property we rely on for both testing and red-teaming.
- **Honest failure record:** four production bugs (the parity dance, the pillar-orbit hole, the
  silent-thief concession gap, and the delivery-dedupe gap) are documented in this report and in
  `docs/TODO.md` alongside their fixes, not smoothed over — we consider a project's failure log a
  code-quality signal in its own right, since it is the only honest evidence that the test suite
  is doing real work rather than confirming what was already assumed.

### 12.1 Five decisions the rules do not require

Each of these cost real effort and none is mandated. They are here because the failure it
prevents is *silent* — it does not raise, does not show up in a passing suite, and shows up
instead as points lost in a way that cannot be reconstructed after the fact.

**1. The audit verifies physics, not just hashes.** Rule #19 requires one thing: recompute every
revealed record against its commitment, and treat a mismatch as proven tampering. We do that —
and then `domain/audit.py` re-walks the whole trajectory against the signed contract. A log can
be perfectly hash-consistent and still physically impossible: a teleport between steps, a
diagonal move, a walk through a barrier the opponent itself declared. Hash verification cannot
see any of those, because the opponent hashed exactly what it intended to send. Evidence:
`verify_trajectory` and `verify_concession` in the audit path, `test_logbook_audit.py::
test_a_teleport_fails_physics_even_with_clean_hashes`, and the same engine drives the Replay
Viewer's verdict so the screenshot in §10 is the audit, not a decoration.

**2. A hostile peer forfeits instead of crashing us.** The natural way to write an auditor is a
chain of `.get()` calls over the opponent's disclosure. A peer that sends `records` as a string,
a record as a bare number, or a payload that is not an object then takes *our* process down —
converting their broken submission into our technical loss. `_disclosed_records` does one
structural check up front so such a disclosure fails cleanly and the sender forfeits.
Deliberately a *structure* check and never a schema one: which fields a payload carries is the
peer's own business, so any dict payload passes. Evidence: `test_hostile_wire.py`, 17 tests,
including `test_lawful_scent_passes` as the false-positive control.

**3. The containment alarm accuses our own driver first.** Containing a dead sub-game as a
technical loss is right per sub-game — one dead tunnel must not cost the other five. It is the
wrong lens on a whole series: an opponent failing *every single time* is far less likely than a
fault on our side, and because each containment prints one quiet line and then scores a
normal-looking technical loss, a broken driver otherwise finishes with a tidy summary and no
alarm at all. That is not hypothetical — it is exactly how a `next_step` crash once produced a
clean-looking 2–2 series report while the opponent lay dead. `containment_alarm` now shouts when
contained failures dominate, and says the fault is probably ours. It only warns: it never
raises, and never touches a byte of any artifact, because the report must stay honest about what
actually happened. Evidence: `test_containment_alarm.py`.

**4. A counted claim only arms when it is addressed to count.** `_is_armed` refuses to mark a
report `counted` unless the recipient is the binding league address (rule #51). This is the
fail-safe that decides whether a misconfiguration is an embarrassment or a disqualification: an
external review found `[email].recipient` pointing at a team member's own inbox, which meant
100% of games would have scored nothing — but *reported honestly as friendlies* rather than
claiming credit they could not have (rules #37/#38). The guard is now paired with
`counted_series_blockers`, which refuses to start a counted series that cannot count, naming
both the address and the delivery mode. Evidence: `test_counted_readiness.py`, 7 tests.

**5. Find the handshake refusal the night before.** `validate_terms` refuses a series on any
signed term that disagrees — correct, but expensive: it lands at kickoff, with both teams
waiting and a tunnel already open. Every value in that set is readable from two config files
beforehand, so `shared/preflight.py` finds the same disagreement in seconds the night before,
and `scripts/preflight.py` exits 1 so it can gate a launch script. It reports what it *cannot*
know — the locked-model hashes and the role split are not in either config file — as explicit
questions for the opponent rather than silently assuming agreement. Evidence:
`test_preflight.py`.

**What none of this is.** These are engineering decisions, not results. Rule #55 restricts
self-grading to code quality, and the honest summary is that all five are defences whose value
is *unproven in league conditions* until the counted series in `docs/TODO.md` §11.3 are played
against real opponents. Four of the five were written after a failure we actually hit; the fifth
(#4) was written after an external review found the misconfiguration it guards.

## 13. Limitations & future work

- **Report alignment (kit §6, `docs/TODO.md` §8.14) is open.** Consensus signature
  serialization, trimmed mutual-agreement scope, and league bookkeeping fields (tie/diversity
  handling, `games_played_including_this`) are designed but not yet cross-checked against the
  kit's own example result file.
- **No live sparring run against the kit's reference peer yet** (`docs/TODO.md` §8.15) — our
  conformance today is vector-level (static, byte-exact) rather than a live six-sub-game exchange
  with a second, independently-authored implementation; that is the strongest remaining
  correctness signal we have not yet collected.
- **The hybrid cop is a documented dead end, not a live trade-off.** Under perfect information it
  trades speed for a measurable loss rate against our strongest evader; under belief it loses the
  speed too (§6), leaving no opponent class that prefers it. The open question it leaves is the
  interesting one: how much *other* perfect-information tuning in the literature inverts the same
  way once the pursuer only has a belief to chase.
- **Our cop cannot convert an elite open-field evader under belief.** Wall and hybrid alike end at
  survival against `EvadeThiefBrain` (§6). Against reference-caliber opponents this never binds —
  the kit sparring series finished 90–30 — but it is the ceiling on our cop score, and closing it
  is the single highest-value strategic work left.
- **RL was deliberately out of scope (ADR-2).** The heuristic track met every KPI without
  training cost or convergence risk; a reinforcement-learning cop/thief pair remains an
  interesting, untaken direction for a non-graded extension.
- **Belief modeling stays a grid distribution, not a particle filter** — adequate and transparent
  at the 7×7 floor; would need revisiting only if the league adopted materially larger boards.
- **A handful of files sit slightly over the 150-line law** (§12) pending the scheduled
  verification-pass split — a known, tracked gap rather than a discovered one.

---

## Documentation index

| Document | Purpose |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product requirements (master) |
| [docs/PLAN.md](docs/PLAN.md) | Architecture, C4 model, ADRs |
| [docs/TODO.md](docs/TODO.md) | Task tracking & milestone gates |
| [docs/COMPLIANCE.md](docs/COMPLIANCE.md) | All 55 rules traced to module + test (references verified by `test_compliance_references.py`) |
| [docs/REVIEW_HOSTILE.md](docs/REVIEW_HOSTILE.md) | Adversarial external review — findings, severities, and what each one costs |
| [docs/SECURITY.md](docs/SECURITY.md) | Secrets inventory, rotation runbook, what the hygiene suite enforces |
| docs/PRD_*.md | Dedicated PRD per mechanism (7 files) |
| [docs/TUNNELING.md](docs/TUNNELING.md) | Public-URL exposure for league play |
| [docs/PROMPTS.md](docs/PROMPTS.md) | Prompts book (AI-assisted development log) |
| `notebooks/analysis.ipynb` | Executed research notebook behind §5–§9 of this report |
| [scripts/brain_tournament.py](scripts/brain_tournament.py) | Every brain against every brain under belief — the harness behind the `[strategy]` gate |
| [scripts/probe_peer.py](scripts/probe_peer.py) | Dial a peer's MCP URL and report, in full, what happened |

## License & credits

MIT (see LICENSE). Built with FastMCP, google-api-python-client, Anthropic API. Reference
implementation consulted: rmisegal/Game-P2P-Cop-Chase (educational-use license). Interop
conformance vectors vendored from the league's `copthief-league-protocol` kit (MIT,
`tests/vectors/KIT_LICENSE`).
