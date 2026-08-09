# TODO — Task Tracking

**Project:** police-thief-p2p | **Version:** 1.00
**Owner:** the team — two members working jointly; individual task ownership is fluid,
so every row is owned by *team* and assignment happens in the daily sync, not in this file.

**Status key:** ☐ not started | ◐ in progress / in review | ✔ completed | ⏱ operational
(external dependency or a physical/manual step performed outside this repo, not code)
**Priority key:** P0 blocking | P1 required for submission | P2 quality/polish

Work follows the rulebook's recommended development order (ch. 10). Every parent task is
expanded into the concrete sub-tasks that were actually performed inside it — the granular
record the guidelines' work-process chapter asks the tracker to preserve.

**Definition of done (applies to every task):** file stays within 150 lines of code,
docstrings on every module, class and function, tests written alongside the code,
`ruff check` clean, coverage not below 85%, this file updated, and the work committed
with a meaningful message.

---

## Phase 0 — Documentation & skeleton (guidelines ch. 2 mandatory work process)

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 0.1 | **Repo skeleton** | P0 | team | ✔ |
| 0.1.1 | Initialize uv project with pyproject.toml and locked dependency set (uv.lock) | P0 | team | ✔ |
| 0.1.2 | Configure ruff: rule families E,F,W,I,N,UP,B,C4,SIM; line-length 100; target py310 | P0 | team | ✔ |
| 0.1.3 | Configure pytest + pytest-cov with the 85% fail_under gate wired into every run | P0 | team | ✔ |
| 0.1.4 | Write .gitignore covering .env, credentials.json, token.json, *.pem, *.key, caches | P0 | team | ✔ |
| 0.1.5 | Write .env-example documenting every environment variable without a single secret | P0 | team | ✔ |
| 0.1.6 | Set package layout src/police_thief with hatchling wheel target | P0 | team | ✔ |
| 0.1.7 | Verify empty-project gates: ruff clean, pytest collects, uv sync reproducible | P0 | team | ✔ |
| 0.2 | **Config skeleton** | P0 | team | ✔ |
| 0.2.1 | Author config/game.json mirroring every Appendix-F binding value verbatim | P0 | team | ✔ |
| 0.2.2 | Author per-peer TOMLs (police 8801, thief 8802) with [network], [strategy] sections | P0 | team | ✔ |
| 0.2.3 | Author config/rate_limits.json (gmail/anthropic/default service profiles) | P0 | team | ✔ |
| 0.2.4 | Author config/setup.json (GUI cell size) and logging_config.json | P0 | team | ✔ |
| 0.2.5 | Cross-check each numeric value against the rendered Appendix-F table page by page | P0 | team | ✔ |
| 0.2.6 | Decide overlay semantics: shared game.json values override private TOML keys | P0 | team | ✔ |
| 0.3 | **docs/PRD.md** | P0 | team | ✔ |
| 0.3.1 | Digest rulebook ch. 1-3 into product goals, actors and constraints | P0 | team | ✔ |
| 0.3.2 | Write functional requirements per subsystem with rule-number traceability | P0 | team | ✔ |
| 0.3.3 | Write non-functional requirements (150-line law, coverage, determinism) | P0 | team | ✔ |
| 0.3.4 | Define acceptance criteria per milestone M1-M8 | P0 | team | ✔ |
| 0.4 | **docs/PLAN.md** | P0 | team | ✔ |
| 0.4.1 | Draw C4 context and container views of the two-peer architecture | P0 | team | ✔ |
| 0.4.2 | Record ADR-1..ADR-6 (repo split, uv, strategy track, verbal-layer chain, transports, seal format) | P0 | team | ✔ |
| 0.4.3 | Define the data contracts: TurnMessage, sealed record, lifecycle files | P0 | team | ✔ |
| 0.4.4 | Map the seven mechanism PRDs to rulebook development-order stages | P0 | team | ✔ |
| 0.4.5 | Record and maintain ADR: one dev repo split at submission | P0 | team | ✔ |
| 0.4.6 | Record and maintain ADR: uv-only toolchain | P0 | team | ✔ |
| 0.4.7 | Record and maintain ADR: enhanced-heuristic strategy track | P0 | team | ✔ |
| 0.4.8 | Record and maintain ADR: verbal chain with template fallback | P0 | team | ✔ |
| 0.4.9 | Record and maintain ADR: transport abstraction | P0 | team | ✔ |
| 0.4.10 | Record and maintain ADR: seal format matches reference | P0 | team | ✔ |
| 0.4.11 | Record and maintain ADR: hidden-position wire (ADR-7) | P0 | team | ✔ |
| 0.4.12 | Record and maintain ADR: interop-kit conformance | P0 | team | ✔ |
| 0.5 | **docs/TODO.md** | P0 | team | ✔ |
| 0.5.1 | Encode the rulebook ch.10 development order as phases with milestones | P0 | team | ✔ |
| 0.5.2 | Define the standing definition-of-done applied to every task | P0 | team | ✔ |
| 0.5.3 | Set priority scheme P0/P1/P2 and status keys | P0 | team | ✔ |
| 0.6 | **Seven mechanism PRDs** | P0 | team | ✔ |
| 0.6.1 | PRD_board_engine: board, laws, scoring, engine, edge cases named | P0 | team | ✔ |
| 0.6.2 | PRD_p2p_mcp: tools, phases, deadline, watchdog, orchestrator seams | P0 | team | ✔ |
| 0.6.3 | PRD_strategy: BrainBase plug points, loader spec, blind then enhanced tracks | P0 | team | ✔ |
| 0.6.4 | PRD_scent_language: emission matrix, belief update, trust, verbal chain | P0 | team | ✔ |
| 0.6.5 | PRD_commit_reveal: seal construction, step-0, logbook, audit layers | P0 | team | ✔ |
| 0.6.6 | PRD_gui_replay: local-truth law, heatmap, replay verification stamps | P0 | team | ✔ |
| 0.6.7 | PRD_reporting_gatekeeper: three gates, lifecycle files, OAuth scope | P0 | team | ✔ |
| 0.7 | **README + docs/PROMPTS.md** | P1 | team | ✔ |
| 0.7.1 | Write the interim README (build, run, layout) pending the final academic report | P1 | team | ✔ |
| 0.7.2 | Open the prompts book with the digestion and scaffolding entries | P1 | team | ✔ |
| 0.7.3 | Adopt the entry template: context, prompt essence, output, lesson | P1 | team | ✔ |
| 0.7.4 | Write prompts-book entry 1 (source digestion) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.5 | Write prompts-book entry 2 (doc-first scaffolding) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.6 | Write prompts-book entry 3 (base logic) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.7 | Write prompts-book entry 4 (p2p layer) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.8 | Write prompts-book entry 5 (blind strategy) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.9 | Write prompts-book entry 6 (language+scent) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.10 | Write prompts-book entry 7 (cloud+tunneling) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.11 | Write prompts-book entry 8 (crypto core) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.12 | Write prompts-book entry 9 (networked loop) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.13 | Write prompts-book entry 10 (gatekeeper+gmail) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.14 | Write prompts-book entry 11 (region cop+concession) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.15 | Write prompts-book entry 12 (arms race) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.16 | Write prompts-book entry 13 (verbal duel) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.17 | Write prompts-book entry 14 (red team) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.18 | Write prompts-book entry 15 (wire fuzzing) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.19 | Write prompts-book entry 16 (speed-margin frontier) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.7.20 | Write prompts-book entry 17 (interop kit) with context/prompt/output/lesson | P1 | team | ✔ |
| 0.8 | **GATE: approve all documents before development starts** | P0 | team | ✔ |
| 0.8.1 | Review pass over all ten documents for internal consistency | P0 | team | ✔ |
| 0.8.2 | Confirm every config value traces to Appendix F | P0 | team | ✔ |
| 0.8.3 | Sign off the gate and record it before the first code commit | P0 | team | ✔ |

## Phase 1 — Base logic (PRD_board_engine) → M1

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 1.1 | **Config layer** | P0 | team | ✔ |
| 1.1.1 | shared/config_io.py: read_json/read_toml with actionable ConfigError | P0 | team | ✔ |
| 1.1.2 | shared/config_io.py: canonical_json (sorted keys, compact separators, raw UTF-8) | P0 | team | ✔ |
| 1.1.3 | shared/config_io.py: sha256_of + apply_overlay (shared beats private) | P0 | team | ✔ |
| 1.1.4 | shared/schema.py: typed frozen dataclasses for every contract section | P0 | team | ✔ |
| 1.1.5 | shared/contract.py: raw dict -> GameContract builder with per-field errors | P0 | team | ✔ |
| 1.1.6 | shared/config.py: ConfigManager.load orchestrating both files per role | P0 | team | ✔ |
| 1.1.7 | constants.py: roles, MOVE_DELTAS (diagonals unrepresentable), phases, file names | P0 | team | ✔ |
| 1.1.8 | shared/version.py: single-source code version | P0 | team | ✔ |
| 1.1.9 | tests: config round-trips, overlay wins, missing-key errors, value pinning | P0 | team | ✔ |
| 1.2 | **domain/board.py** | P0 | team | ✔ |
| 1.2.1 | Square grid with in_bounds/is_free/neighbours/free_neighbours | P0 | team | ✔ |
| 1.2.2 | Irreversible barrier placement with BoardError on illegal cells | P0 | team | ✔ |
| 1.2.3 | tests: geometry, barrier permanence, off-board rejection | P0 | team | ✔ |
| 1.3 | **domain/rules.py** | P0 | team | ✔ |
| 1.3.1 | Move legality: orthogonal-only via destination/validate_move | P0 | team | ✔ |
| 1.3.2 | legal_moves/legal_steps in deterministic tie-break order | P0 | team | ✔ |
| 1.3.3 | Barrier law: stay-turn only, within one step, quota, free cell | P0 | team | ✔ |
| 1.3.4 | is_trapped: blocked cell or all exits blocked (rules 46/47) | P0 | team | ✔ |
| 1.3.5 | tests: 25 cases incl. corner traps, quota edge, diagonal rejection | P0 | team | ✔ |
| 1.4 | **domain/scoring.py** | P0 | team | ✔ |
| 1.4.1 | Outcome dataclass with points_for(role) | P0 | team | ✔ |
| 1.4.2 | capture/survival/technical_loss/tie constructors from ScoringConfig | P0 | team | ✔ |
| 1.4.3 | series_totals aggregation | P0 | team | ✔ |
| 1.4.4 | tests: every termination event against the Appendix-F table | P0 | team | ✔ |
| 1.5 | **SDK + scripted game → M1** | P0 | team | ✔ |
| 1.5.1 | domain/state.py: GameState ground truth + from_contract | P0 | team | ✔ |
| 1.5.2 | domain/engine.py: apply/end_turn with termination detection | P0 | team | ✔ |
| 1.5.3 | sdk/sdk.py: SimulationSdk facade for runners and tools | P0 | team | ✔ |
| 1.5.4 | CLI demo playing a scripted legal game end to end | P0 | team | ✔ |
| 1.5.5 | M1 observed: legal moves, quota rejection, overlap capture | P0 | team | ✔ |

## Phase 2 — FastMCP infrastructure (PRD_p2p_mcp) → M2

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 2.1 | **services/phase_machine.py** | P0 | team | ✔ |
| 2.1.1 | Legal-transition table as data; transition() raising on anything else | P0 | team | ✔ |
| 2.1.2 | tests: every legal edge, every illegal edge refused | P0 | team | ✔ |
| 2.2 | **deadline.py + watchdog.py** | P0 | team | ✔ |
| 2.2.1 | DeadlineTracker with injected clock; expiry -> TECHNICAL_LOSS path | P0 | team | ✔ |
| 2.2.2 | Watchdog with beat/check, on_persist and on_shutdown callbacks | P0 | team | ✔ |
| 2.2.3 | tests: expiry, rescue, no real sleeps anywhere | P0 | team | ✔ |
| 2.3 | **infra/mcp_server.py** | P0 | team | ✔ |
| 2.3.1 | FastMCP server exposing the reference tool set | P0 | team | ✔ |
| 2.3.2 | Tool docs + payload forwarding to InboundHandler | P0 | team | ✔ |
| 2.3.3 | tests: registration, forwarding, documentation of every tool | P0 | team | ✔ |
| 2.4 | **infra/mcp_client.py** | P0 | team | ✔ |
| 2.4.1 | PeerClient with deadline-wrapped calls, retries and backoff from config | P0 | team | ✔ |
| 2.4.2 | Transport protocol + LoopbackTransport + FlakyTransport doubles | P0 | team | ✔ |
| 2.4.3 | tests: retry exhaustion, backoff sequence, unreachable -> technical loss | P0 | team | ✔ |
| 2.5 | **orchestrator + two processes → M2** | P0 | team | ✔ |
| 2.5.1 | Orchestrator as single entry point; wiring.py building subsystems | P0 | team | ✔ |
| 2.5.2 | recovery.py: crash rescue path preserving the logbook | P0 | team | ✔ |
| 2.5.3 | M2 observed: geometric message police -> thief over localhost decoded | P0 | team | ✔ |

## Phase 3 — Blind strategy (PRD_strategy) → M3

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 3.1 | **brain/base.py + pathfind.py** | P0 | team | ✔ |
| 3.1.1 | BrainBase with _pick_move/_decide_move plug points | P0 | team | ✔ |
| 3.1.2 | load_brain: package.module:Class loader driven by TOML [strategy] | P0 | team | ✔ |
| 3.1.3 | pathfind: BFS distance_field, step_toward, step_away over live barriers | P0 | team | ✔ |
| 3.1.4 | tests: loader errors, field correctness, deterministic ties | P0 | team | ✔ |
| 3.2 | **Blind police + thief brains** | P0 | team | ✔ |
| 3.2.1 | BlindPoliceBrain: BFS pursuit + adjacent trap placement | P0 | team | ✔ |
| 3.2.2 | BlindThiefBrain: safety scoring with DEAD_END_PENALTY | P0 | team | ✔ |
| 3.2.3 | Rewrote unsatisfiable dead-end veto as bounded penalty (recorded lesson) | P0 | team | ✔ |
| 3.2.4 | tests: pursuit shortening, evasion lengthening, penalty firing | P0 | team | ✔ |
| 3.3 | **Wire brains into runtime → M3** | P0 | team | ✔ |
| 3.3.1 | services/runtime.py: configured_brain + LocalMatchRunner | P0 | team | ✔ |
| 3.3.2 | M3 observed: shortest-path execution with no manual intervention | P0 | team | ✔ |

## Phase 4 — Language + scent (PRD_scent_language) → M4

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 4.1 | **domain/scent.py** | P0 | team | ✔ |
| 4.1.1 | Figure-4 emission with pre-series lock surface | P0 | team | ✔ |
| 4.1.2 | Verbatim update rule tau'=clamp((1-rho)tau+delta,0,0.9) | P0 | team | ✔ |
| 4.1.3 | expected_fresh_trail yardstick (0.81) | P0 | team | ✔ |
| 4.1.4 | tests: matrix digit-for-digit, decay curve, clamp both ends | P0 | team | ✔ |
| 4.2 | **domain/belief.py** | P0 | team | ✔ |
| 4.2.1 | BeliefMap: uniform prior, diffuse over legal motion model | P0 | team | ✔ |
| 4.2.2 | observe_scent multiplicative update + normalization off barriers | P0 | team | ✔ |
| 4.2.3 | observe_region hook + exclude negative evidence | P0 | team | ✔ |
| 4.2.4 | tests: convergence, barrier zeroing, degenerate renormalization | P0 | team | ✔ |
| 4.3 | **domain/trust.py** | P1 | team | ✔ |
| 4.3.1 | Hint parsing to cardinal directions; region_for halves/quadrants | P1 | team | ✔ |
| 4.3.2 | EWMA trust; corroborate/contradict verdicts vs the 0.81 yardstick | P1 | team | ✔ |
| 4.3.3 | tests: ch.4 worked example, liar erosion, landmark neutrality | P1 | team | ✔ |
| 4.4 | **infra/llm base + template** | P0 | team | ✔ |
| 4.4.1 | HintRequest/HintProvider contract with 15-word clip | P0 | team | ✔ |
| 4.4.2 | TemplateProvider: deterministic landmark hints per arena | P0 | team | ✔ |
| 4.4.3 | tests: word cap, determinism, direction wording, lie opposites | P0 | team | ✔ |
| 4.5 | **Paid providers + chain** | P1 | team | ✔ |
| 4.5.1 | claude_api (Haiku) with measured usage; ollama; claude_cli | P1 | team | ✔ |
| 4.5.2 | Chain: fallback(throttle(budget_guard(paid), template)) | P1 | team | ✔ |
| 4.5.3 | tests: no-key rescue, throttle routing, budget cutoff | P1 | team | ✔ |
| 4.6 | **Enhanced brains** | P1 | team | ✔ |
| 4.6.1 | EnhancedPoliceBrain: corridor pinch + barrier reserve | P1 | team | ✔ |
| 4.6.2 | EnhancedThiefBrain: trap-risk veto over blind safety | P1 | team | ✔ |
| 4.6.3 | tests: pinch fires, reserve held, veto prices adjacency | P1 | team | ✔ |
| 4.7 | **Token ledger → M4** | P1 | team | ✔ |
| 4.7.1 | TokenLedger: per-step and series totals against the 200k budget | P1 | team | ✔ |
| 4.7.2 | M4 observed: report -> inference; scent decays; hint truth or lie | P1 | team | ✔ |

## Phase 5 — Cloud & tunneling → M5

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 5.1 | **Public-URL support** | P0 | team | ✔ |
| 5.1.1 | infra/http_transport.py: MCP-over-HTTP behind the Transport protocol | P0 | team | ✔ |
| 5.1.2 | services/peer_boot.py + peer CLI subcommand (serve + handshake) | P0 | team | ✔ |
| 5.1.3 | docs/TUNNELING.md: tunnel setup, reconnect policy | P0 | team | ✔ |
| 5.1.4 | Timeout path proven: dead opponent -> technical loss in 11s, no hang | P0 | team | ✔ |
| 5.2 | **Remote round → M5** | P0 | team | ✔ |
| 5.2.1 | Two real processes over HTTP: handshake observed OK | P0 | team | ✔ |
| 5.2.2 | M5 observed: full round over a public-style URL | P0 | team | ✔ |

## Phase 6 — Security & crypto (PRD_commit_reveal) → M6

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 6.1 | **domain/crypto.py** | P0 | team | ✔ |
| 6.1.1 | new_nonce via secrets.token_hex(16); never random | P0 | team | ✔ |
| 6.1.2 | digest_of = sha256(canonical|nonce); seal/verify with compare_digest | P0 | team | ✔ |
| 6.1.3 | audit_records over a full disclosure | P0 | team | ✔ |
| 6.1.4 | tests: uniqueness, stability, smallest-change break, wrong nonce | P0 | team | ✔ |
| 6.2 | **Commit -> reveal flow** | P0 | team | ✔ |
| 6.2.1 | Wire carries commitment only; reveal deferred to audit (ADR-7) | P0 | team | ✔ |
| 6.2.2 | tests: cleartext position refused at the message layer | P0 | team | ✔ |
| 6.3 | **Step-0 record** | P0 | team | ✔ |
| 6.3.1 | sealing.step0_record: hardware spec, model, code_version, github_commit, budget | P0 | team | ✔ |
| 6.3.2 | shared/sysinfo.hardware_spec: os/machine/python/cpu/ram/gpu | P0 | team | ✔ |
| 6.3.3 | tests: mandatory fields, seal verifies, commit hash carried | P0 | team | ✔ |
| 6.4 | **domain/logbook.py** | P0 | team | ✔ |
| 6.4.1 | Append-only sealed records; commitments-only public view | P0 | team | ✔ |
| 6.4.2 | save/load as log_<game_id>_gNN.json with mandated name | P0 | team | ✔ |
| 6.4.3 | tests: append-only, name format, round-trip | P0 | team | ✔ |
| 6.5 | **domain/audit.py** | P0 | team | ✔ |
| 6.5.1 | Layer 1: re-hash every revealed record; one mismatch -> TAMPERED | P0 | team | ✔ |
| 6.5.2 | Layer 2: trajectory physics (start cell, displacement, barrier law) | P0 | team | ✔ |
| 6.5.3 | tests: clean pass, forged hash, hash-consistent teleport caught | P0 | team | ✔ |
| 6.6 | **domain/negotiation.py v1 → M6** | P0 | team | ✔ |
| 6.6.1 | Terms with contract digest, scent lock, game count, step0 commitment | P0 | team | ✔ |
| 6.6.2 | M6 observed: commit->reveal verifies; step-0 verified | P0 | team | ✔ |

## Phase 7 — Reporting & visualization shell → M7

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 7.1 | **Networked turn loop (ADR-7)** | P0 | team | ✔ |
| 7.1.1 | Rewrote wire to negotiate/receive_turn/submit_audit tool set | P0 | team | ✔ |
| 7.1.2 | world_view.py: local truth + inference only, no opponent position field | P0 | team | ✔ |
| 7.1.3 | turn_taking.py: decide -> validate -> seal -> compose message | P0 | team | ✔ |
| 7.1.4 | turn_receiving.py: scent->belief, hint->trust, events, endings | P0 | team | ✔ |
| 7.1.5 | match_runtime.py: one peer's full mini-game engine | P0 | team | ✔ |
| 7.1.6 | Integration: full match, agreed verdict, mutual two-layer audit | P0 | team | ✔ |
| 7.2 | **bucket.py + gatekeeper.py** | P0 | team | ✔ |
| 7.2.1 | TokenBucket with verbatim tokens<-min(C,tokens+r*dt); injected clock | P0 | team | ✔ |
| 7.2.2 | Gatekeeper: daily quota, bucket, DOS lock; FIFO queue; monitoring log | P0 | team | ✔ |
| 7.2.3 | tests: refill math, gate order, lock, drain, overflow visibility | P0 | team | ✔ |
| 7.3 | **Gmail OAuth + sender** | P0 | team | ✔ |
| 7.3.1 | oauth.py: gmail.send single scope; token reuse/refresh/consent flow | P0 | team | ✔ |
| 7.3.2 | sender.py: MIME with JSON attachment; draft/send modes; 429 -> backoff | P0 | team | ✔ |
| 7.3.3 | configured_sender wiring recipient/mode/limits purely from config | P0 | team | ✔ |
| 7.3.4 | tests: all Google modules doubled; no network anywhere | P0 | team | ✔ |
| 7.4 | **reports.py lifecycle files** | P0 | team | ✔ |
| 7.4.1 | declaration/config/result payload builders sharing game_uid | P0 | team | ✔ |
| 7.4.2 | write_lifecycle_file in canonical bytes matching the mailed copy | P0 | team | ✔ |
| 7.4.3 | tests: sealed declaration verifies, totals recomputed, names derived | P0 | team | ✔ |
| 7.5 | **Live GUI** | P0 | team | ✔ |
| 7.5.1 | heatmap.py: belief reds, T? argmax, C self, barriers | P0 | team | ✔ |
| 7.5.2 | banner.py YOUR TURN/LOCKED; live.py window; coverage-excluded rendering | P0 | team | ✔ |
| 7.6 | **Replay viewer** | P0 | team | ✔ |
| 7.6.1 | replay.py: step fwd/back, per-step verify, Verified OK / TAMPERED | P0 | team | ✔ |
| 7.6.2 | tests: clean log verified, one edited byte voids the match | P0 | team | ✔ |
| 7.7 | **End-to-end shell → M7** | P0 | team | ✔ |
| 7.7.1 | scripts/m7_report_demo.py: play, write lifecycle files, gated send | P0 | team | ✔ |
| 7.7.2 | M7 observed with stub Gmail; real draft path documented for OAuth day | P0 | team | ✔ |

## Phase 8 — Research, strategy escalation, interop, compliance

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 8.1 | **Research notebook** | P1 | team | ✔ |
| 8.1.1 | scripts/build_notebook.py: notebook authored as code, executed via nbclient | P1 | team | ✔ |
| 8.1.2 | Section 1: pinch sweep -> flat 0% capture surface | P1 | team | ✔ |
| 8.1.3 | Section 2: parity-dance diagnosis with distance trace | P1 | team | ✔ |
| 8.1.4 | Section 3-4: region cop + sensitivity sweep + crippled control | P1 | team | ✔ |
| 8.1.5 | Section 5-6: thief penalty sweep; exhaustive 1900-pair validation | P1 | team | ✔ |
| 8.1.6 | Every figure a real executed output; regeneration deterministic | P1 | team | ✔ |
| 8.1.7 | Author, execute and verify notebook section: pinch-sweep heatmap | P1 | team | ✔ |
| 8.1.8 | Author, execute and verify notebook section: parity-dance trace | P1 | team | ✔ |
| 8.1.9 | Author, execute and verify notebook section: region cop results | P1 | team | ✔ |
| 8.1.10 | Author, execute and verify notebook section: MIN_SHRINK×ENDGAME sensitivity + crippled control | P1 | team | ✔ |
| 8.1.20 | **Corrected §4's control, which proved the opposite of what it claimed.** The "barriers disabled" control set `MIN_SHRINK=100, ENDGAME=0` and concluded the barrier logic was load-bearing — but those knobs gate only `_barrier_options`; `RegionPoliceBrain` inherits `_can_trap` from `BlindPoliceBrain` and checks it *first*, so the finishing stone never stopped firing (the crippled run still spent 1.00 barriers/capture). §13's conclusion then asserted "the barrier-disabled control collapses to 0%" while the notebook's own output printed 100% — a self-contradiction. Added a real control (`_can_trap` and `_barrier_options` both stubbed): movement alone still converts 100% of the grid, just slower (12.2 vs 9.0 mean steps), so barriers buy speed, not the win. Notebook re-executed end to end; §4 prose and §13 conclusion rewritten to the measured truth | P1 | team | ✔ |
| 8.1.11 | Author, execute and verify notebook section: thief first defense sweep | P1 | team | ✔ |
| 8.1.12 | Author, execute and verify notebook section: exhaustive 1900-pair validation | P1 | team | ✔ |
| 8.1.13 | Author, execute and verify notebook section: arms race round 1 (evader) | P1 | team | ✔ |
| 8.1.14 | Author, execute and verify notebook section: round 2 (wall cop) + histogram | P1 | team | ✔ |
| 8.1.15 | Author, execute and verify notebook section: red team + post-fix live check | P1 | team | ✔ |
| 8.1.16 | Author, execute and verify notebook section: belief transfer check over the wire | P1 | team | ✔ |
| 8.1.17 | Author, execute and verify notebook section: verbal duel table | P1 | team | ✔ |
| 8.1.18 | Author, execute and verify notebook section: token budget analysis | P1 | team | ✔ |
| 8.1.19 | Author, execute and verify notebook section: three-generation conclusions | P1 | team | ✔ |
| 8.2 | **Region cop** | P1 | team | ✔ |
| 8.2.1 | brain/region.py: safe-region minimization, exits tie-break, quota guards | P1 | team | ✔ |
| 8.2.2 | Fixed distance_field -1 semantics via _reach | P1 | team | ✔ |
| 8.2.3 | 1900/1900 captures, mean 7.8, max 11, ~2 stones | P1 | team | ✔ |
| 8.2.4 | tests: region math, endgame sealing, no-quota fallback | P1 | team | ✔ |
| 8.3 | **Concession protocol v1** | P0 | team | ✔ |
| 8.3.1 | Found: trapped thief went silent, winner never learned (first networked capture) | P0 | team | ✔ |
| 8.3.2 | concession_message sealed + auditable; on_turn returns the reply | P0 | team | ✔ |
| 8.3.3 | tests: emit once, sealed, cop accepts, wrong-side ignored | P0 | team | ✔ |
| 8.4 | **Arms race: evader + wall cop** | P1 | team | ✔ |
| 8.4.1 | Weight-blend search: lexicographic orders lose, blends win | P1 | team | ✔ |
| 8.4.2 | brain/evade.py: worst-case region + distance + openness + mobility (60/72 vs region cop) | P1 | team | ✔ |
| 8.4.3 | Minimax cop and anti-dance attempts recorded as failed designs | P1 | team | ✔ |
| 8.4.4 | brain/wall.py: center wall with guarded door, then region hunt | P1 | team | ✔ |
| 8.4.5 | Exhaustive: 1900/1900 vs every archetype, max 29/35, max 8/14 stones | P1 | team | ✔ |
| 8.4.6 | Notebook sections 7-8; regression tests pin the frontier | P1 | team | ✔ |
| 8.5 | **Verbal duel** | P1 | team | ✔ |
| 8.5.1 | Measured lie damage: 0.56 -> 2.69 belief error vs a hint-following cop | P1 | team | ✔ |
| 8.5.2 | Temporal TrustModel: scent-centroid displacement dot claimed direction | P1 | team | ✔ |
| 8.5.3 | DeceptionPolicy: honest/mislead/vague/adaptive off claim-gap feedback | P1 | team | ✔ |
| 8.5.4 | Vague style through template + Haiku prompts; 'right now' leak caught | P1 | team | ✔ |
| 8.5.5 | Result: lying at us (0.62) worse than silence (1.00); we poison naive cops | P1 | team | ✔ |
| 8.5.6 | Notebook section 10; config [deception] sections both peers | P1 | team | ✔ |
| 8.6 | **Red team** | P1 | team | ✔ |
| 8.6.1 | DoorCamper/SideFlipper/WallBlocker built against our own cop | P1 | team | ✔ |
| 8.6.2 | Pillar-orbit hole found (2/192): hunt stone became a merry-go-round | P1 | team | ✔ |
| 8.6.3 | Dance-breaker: repeated state buys an anchored hunt-preserving stone | P1 | team | ✔ |
| 8.6.4 | Re-validated exhaustively: six archetypes, 1900/1900, worst 32/35 | P1 | team | ✔ |
| 8.6.5 | Determinism redefined: fresh brain same state same decision | P1 | team | ✔ |
| 8.7 | **Wire hardening** | P0 | team | ✔ |
| 8.7.1 | services/enforcement.py: step continuity, scent physics, barrier law, claim permissions | P0 | team | ✔ |
| 8.7.2 | Type-safe TurnMessage.from_wire; NaN/inf/off-board scent refused | P0 | team | ✔ |
| 8.7.3 | Step-35 survival forgery closed by monotonicity | P0 | team | ✔ |
| 8.7.4 | 23-test hostile fuzz battery; violations land on the sender | P0 | team | ✔ |
| 8.8 | **Hybrid cop + claim pin** | P2 | team | ✔ |
| 8.8.1 | brain/hybrid.py: three commit tripwires; irreversible wall commitment | P2 | team | ✔ |
| 8.8.2 | Exhaustive truth: 1900/1900 vs weak at mean 12; 1891/1900 vs elite -> NOT default | P2 | team | ✔ |
| 8.8.3 | Verified-claim pin: cop scent corroborates claim -> thief belief pins (25x) | P2 | team | ✔ |
| 8.8.4 | Config documents both cop profiles with published numbers | P2 | team | ✔ |
| 8.9 | **Token cost analysis** | P2 | team | ✔ |
| 8.9.1 | Calls/tokens per mini-game and series; 14% budget utilization | P2 | team | ✔ |
| 8.9.2 | Parametric cost cell; fallback ladder bounds worst case at zero | P2 | team | ✔ |
| 8.10 | **Interop kit: vectors + conformance** | P0 | team | ✔ |
| 8.10.1 | Cloned class kit; read SPEC.md fully (1032 lines) | P0 | team | ✔ |
| 8.10.2 | Vendored MIT vectors into tests/vectors with license | P0 | team | ✔ |
| 8.10.3 | tests/interop/test_kit_vectors.py: 11 byte-exact conformance tests | P0 | team | ✔ |
| 8.10.4 | Fixed kernel IEEE drift: verbatim lookup replaces computed values | P0 | team | ✔ |
| 8.10.5 | Scent lock replaced by the registered multiplicative_book_v1 doc | P0 | team | ✔ |
| 8.10.6 | Vendor + conformance-check fixture `canonical_json` | P0 | team | ✔ |
| 8.10.7 | Vendor + conformance-check fixture `commit_reveal` | P0 | team | ✔ |
| 8.10.8 | Vendor + conformance-check fixture `delivery_contract` | P0 | team | ✔ |
| 8.10.9 | Vendor + conformance-check fixture `derive_starts` | P0 | team | ✔ |
| 8.10.10 | Vendor + conformance-check fixture `game_uid` | P0 | team | ✔ |
| 8.10.11 | Vendor + conformance-check fixture `joint_seed` | P0 | team | ✔ |
| 8.10.12 | Vendor + conformance-check fixture `locked_model` | P0 | team | ✔ |
| 8.10.13 | Vendor + conformance-check fixture `pairing_declaration` | P0 | team | ✔ |
| 8.10.14 | Vendor + conformance-check fixture `pheromone` | P0 | team | ✔ |
| 8.10.15 | Vendor + conformance-check fixture `report_consensus` | P0 | team | ✔ |
| 8.10.16 | Vendor + conformance-check fixture `scent_book_v3` | P0 | team | ✔ |
| 8.10.17 | Vendor + conformance-check fixture `smell_binding` | P0 | team | ✔ |
| 8.10.18 | Vendor + conformance-check fixture `terms_signature` | P0 | team | ✔ |
| 8.10.19 | Vendor + conformance-check fixture `uid_declaration` | P0 | team | ✔ |
| 8.11 | **Interop handshake** | P0 | team | ✔ |
| 8.11.1 | shared/interop.py: terms_from_contract (flat 14 keys), sign_terms, derive_game_ids | P0 | team | ✔ |
| 8.11.2 | negotiate_extras: pairing declaration + three locked-model hashes | P0 | team | ✔ |
| 8.11.3 | negotiation.py rewritten: value-equal terms, signature verify, truth-table refusals | P0 | team | ✔ |
| 8.11.4 | Omission-never-refuses honored both directions | P0 | team | ✔ |
| 8.11.5 | min_center_intensity plumbed through schema/contract/game.json | P0 | team | ✔ |
| 8.11.6 | InboundHandler + wiring + all fixtures migrated | P0 | team | ✔ |
| 8.12 | **At-least-once delivery (kit 7.1)** | P0 | team | ✔ |
| 8.12.1 | Dedupe on commit: same step+commit absorbed idempotently | P0 | team | ✔ |
| 8.12.2 | Same step different commit stays loud (equivocation) | P0 | team | ✔ |
| 8.12.3 | Duplicates never renew deadlines | P0 | team | ✔ |
| 8.12.4 | Conformance test over delivery_contract.json decision table | P0 | team | ✔ |
| 8.12.5 | Review resolved: accounting delivered; suite grew 580 → 588 | P0 | team | ✔ |
| 8.12.6 | Review resolved: capacity-2 reorder buffer + in-order replay, tested | P0 | team | ✔ |
| 8.13 | **Kit-shape capture final (kit 3.1)** | P0 | team | ✔ |
| 8.13.1 | Thief final: claim_response {claim:[own cell], caught:true} | P0 | team | ✔ |
| 8.13.2 | Zero-step final exemption in step law and dedupe | P0 | team | ✔ |
| 8.13.3 | Cop side: answer vs concession distinction; legacy win_claim tolerated | P0 | team | ✔ |
| 8.13.4 | Deferred to report alignment: audit-side concession corroboration (kit 3.1) | P0 | team | ✔ |
| 8.14 | **Report alignment (kit 6)** | P0 | team | ✔ |
| 8.14.1 | Consensus signature: spaced serialization, sign-then-insert Hebrew key | P0 | team | ✔ |
| 8.14.2 | mutual_agreement trimmed scope (game_id, aggregate, trimmed sub_games) | P0 | team | ✔ |
| 8.14.3 | Tie +2 added into total_score; diversity +10 never baked into totals | P0 | team | ✔ |
| 8.14.4 | League fields: games_played_including_this map with legal nulls; first_meeting; diversity flags | P0 | team | ✔ |
| 8.14.5 | Email = canonical bytes as body AND same file attached; recipient-gated arming | P0 | team | ✔ |
| 8.14.6 | Cross-check against kit examples/pairing-artifacts result file | P0 | team | ✔ |
| 8.14.7 | Audit-side rule-47 concession corroboration: re-derive is_trapped from the last turn's board, closing 8.13.4 | P0 | team | ✔ |
| 8.15 | **Sparring series (kit)** | P0 | team | ✔ |
| 8.15.1 | Run kit verify_vectors.py locally on the Mac | P0 | team | ✔ |
| 8.15.2 | python -m sparring.cli selfplay: full six-sub-game series | P0 | team | ✔ |
| 8.15.3 | Fix every refusal the sparring peer explains until series is clean | P0 | team | ✔ |
| 8.15.4 | Both audits clean; artifacts joinable by game_id and game_uid | P0 | team | ✔ |
| 8.15.1w | Windows equivalent of 8.15.1: cloned `github.com/Imreec/copthief-league-protocol` to `..\copthief-league-protocol`; ran `verify_vectors.py` on the local Python 3.12.0 install (`C:\...\Python312\python.exe`, matching the kit's stated floor) — **ALL VECTORS PASS**, 113 checks across 14 fixtures (7 CORE, 3 PROMOTED, 2 PROPOSED, 2 ENH); separately diffed all 14 files in `vectors/` against our vendored `tests/vectors/*.json` — byte-identical, zero drift | P0 | team | ✔ |
| 8.15.2w | Windows equivalent of 8.15.2: `python -m sparring.cli selfplay` on Python 3.12 — exit 0, six sub-games settled (series tied 45-45, 3 sub-games each), 14 artifacts written under `runs/sparring_<uid>/`; ran the kit's own `tools/check_artifacts.py` against that run — **ALL ARTIFACT CHECKS PASS** (uid re-derivation, totals-from-rows, tie/diversity legality, all 27 checks) | P0 | team | ✔ |
| 8.15.3w | Windows equivalent of 8.15.3/8.15.4, sub-game 1 of 6: `pip install fastmcp` for Python 3.12; wrote a one-shot driver (`Orchestrator` + `MatchRuntime` glue that did not exist anywhere in this repo before) serving our police peer on :8801 against `sparring.cli serve --port 8931 --peer http://127.0.0.1:8801/mcp --role thief`. Two REAL refusals hit and fixed: (1) `terms mismatch on ['setting']` — our `world.map_area="New York"` vs. the peer's default `setting="Haifa"`, a genuine unagreed value, not a bug, resolved for this rehearsal by aligning the scratch config to `"Haifa"`; (2) `scent_model_sha256 mismatch` — the peer defaults to `subtractive_chebyshev_v1`, ours is the registered `multiplicative_book_v1`; resolved with `--scent-model multiplicative_book_v1`, one of the two models the peer itself ships. After both: a full real sub-game played out (29 real turns, real hints both directions, template fallback firing correctly), settled `capture` for police (us) at step 29, **both mutual audits Verified OK** (their audit of our disclosure, and our own `audit_disclosure` of theirs) | P0 | team | ✔ |
| 8.15.4w | Persistent driver written: `scripts/sparring_series.py` (new; the 8.15.3w one-shot script was never committed and is gone). Runs our peer as one long-lived FastMCP server on :8801 across all 6 sub-games — a `SwappableHandler` swaps in a fresh `InboundHandler`+`MatchRuntime` pair at each sub-game boundary instead of the process exiting, which is exactly what fixed the prior `sub-game mismatch: we are playing 1, they declare 2` refusal. Role alternates police/thief/police/... starting police (complementary to the kit's `--role thief`, confirming the kit's own `role_for` alternation). REAL run, both processes started independently and left to finish on their own (`.venv` Python 3.10.20 driving us, Python 3.12 at `C:\Users\yanal\AppData\Local\Programs\Python\Python312\python.exe` driving `python -m sparring.cli serve --port 8931 --peer http://127.0.0.1:8801/mcp --role thief --group-id sparring-local --scent-model multiplicative_book_v1`): all 6 sub-games settled — g01 capture 20-5 (police/us), g02 survival 10-5 (thief/us, 34-35 steps), g03 capture 20-5 (police/us), g04 survival 10-5 (thief/us), g05 capture 20-5 (police/us), g06 survival 10-5 (thief/us) — steps matched exactly on both sides (kit log: 29/34/29/34/29/34; ours: 29/34/29/34/29/35 with the one-step discrepancy being each side's own turn-count perspective, not a disagreement `check_artifacts.py` flags). **Every one of the 6 mutual audits Verified OK** on both sides. Both peers independently derived the identical `game_id=sparring-local-vs-team-tbd` and `game_uid=b82a3810-66bd-da32-8475-1439f28b9de6` (the same uid 8.15.3w's single sub-game produced, confirming `derive_game_ids` matches the kit's `kitref.game_uid` byte-for-byte). Final series: us (team-tbd) 90, them (sparring-local) 30, `winner_group=team-tbd`, `series_tie=false`. Wrote our own 14 artifacts (1 declaration + 6 config + 6 log + 1 result) to `results/sparring_series/` via `infra/email/reports.py`'s payload builders; the kit wrote its own 14 to `runs/sparring_b82a3810-66bd-da32-8475-1439f28b9de6/`. Ran the kit's `tools/check_artifacts.py <ours> <theirs>` (Python 3.12) — **exit code 0, 167 PASS / 0 FAIL**, ending in `ALL SETS AGREE`: both bundles independently pass every per-directory structural/derivation check, then the cross-team join agrees on `game_uid`, `total_score`, `sub_games_won`, `winner_group`, `ties`, `series_tie`, `tokens_total_series`, `first_meeting_between_groups`, `diversity_reward_applied`, per-row scores, and — the one machine-checkable must-match value — `mutual_agreement.sha256` byte-for-byte identical across both independently-computed reports. One benign timing race observed twice (sub-game 2 and sub-game 4 boundaries): our handler swap landed a beat after the kit's next-sub-game greeting arrived, raising `HandshakeRejectedError: sub-game mismatch` inside our own FastMCP tool call; the kit's `McpClient` session-retry-once logic absorbed it transparently on the next attempt and every later step (negotiation, turn exchange, audits, artifacts) shows no trace of it — not a correctness bug, just a cosmetic exception in our server log, left as-is rather than papered over. Full raw process logs from this exact run are preserved in the scratchpad (`our_driver.log`, `kit_peer.log`, `check_artifacts_out.log`) for anyone who wants to re-examine them | P0 | team | ✔ |
| 8.20 | **Wire-endgame finding: root cause was the unspoken rule-47 ending, now conceded** | P0 | team | ✔ |
| 8.20.1 | Reproduce: wall cop vs Enhanced thief over the wire ends survival at 35 | P0 | team | ✔ |
| 8.20.2 | Root cause found instead: thief never SAID the rule-47 ending (kit 3.1) - concession added in on_turn | P0 | team | ✔ |
| 8.20.3 | Belief-mass sealing judged unnecessary: with rule 47 spoken, the cop converts reference-caliber thieves | P2 | team | ✔ |
| 8.20.4 | Claim-answer negative evidence already active (belief.exclude); no further work needed | P2 | team | ✔ |
| 8.20.5 | Wire-validated: Blind and Enhanced captured @28 with agreed verdicts; only our own elite evader survives | P0 | team | ✔ |
| 8.16 | **docs/COMPLIANCE.md** | P1 | team | ✔ |
| 8.16.1 | Re-read Appendix E rules 1-55 verbatim from the rulebook | P1 | team | ✔ |
| 8.16.2 | Six rule groups mapped to module + proving test each | P1 | team | ✔ |
| 8.16.3 | Every cited test name verified to exist in the suite | P1 | team | ✔ |
| 8.16.4 | Guidelines checklist with live evidence; binding parameter table | P1 | team | ✔ |
| 8.16.5 | Trace rule #1 (two fully separate processes) to its module and proving test | P1 | team | ✔ |
| 8.16.6 | Trace rule #2 (no shared memory between sides) to its module and proving test | P1 | team | ✔ |
| 8.16.7 | Trace rule #3 (orchestrator sole entry point) to its module and proving test | P1 | team | ✔ |
| 8.16.8 | Trace rule #4 (formal state machine) to its module and proving test | P1 | team | ✔ |
| 8.16.9 | Trace rule #5 (illegal transitions rejected) to its module and proving test | P1 | team | ✔ |
| 8.16.10 | Trace rule #6 (deadline tracking vs freezes) to its module and proving test | P1 | team | ✔ |
| 8.16.11 | Trace rule #7 (watchdog + data rescue) to its module and proving test | P1 | team | ✔ |
| 8.16.12 | Trace rule #8 (live GUI local truth only) to its module and proving test | P1 | team | ✔ |
| 8.16.13 | Trace rule #9 (objective board never shown) to its module and proving test | P1 | team | ✔ |
| 8.16.14 | Trace rule #10 (tunnel to the public internet) to its module and proving test | P1 | team | ✔ |
| 8.16.15 | Trace rule #11 (byte-identical config both sides) to its module and proving test | P1 | team | ✔ |
| 8.16.16 | Trace rule #12 (minimums raised only by agreement) to its module and proving test | P1 | team | ✔ |
| 8.16.17 | Trace rule #13 (orthogonal movement only) to its module and proving test | P1 | team | ✔ |
| 8.16.18 | Trace rule #14 (diagonals rejected by the opponent) to its module and proving test | P1 | team | ✔ |
| 8.16.19 | Trace rule #15 (barriers declared openly) to its module and proving test | P1 | team | ✔ |
| 8.16.20 | Trace rule #16 (no lying about barrier location) to its module and proving test | P1 | team | ✔ |
| 8.16.21 | Trace rule #17 (SHA-256 commit-reveal) to its module and proving test | P1 | team | ✔ |
| 8.16.22 | Trace rule #18 (nonces secret until game end) to its module and proving test | P1 | team | ✔ |
| 8.16.23 | Trace rule #19 (hash mismatch = technical disqualification) to its module and proving test | P1 | team | ✔ |
| 8.16.24 | Trace rule #20 (replay viewer verifies the log) to its module and proving test | P1 | team | ✔ |
| 8.16.25 | Trace rule #21 (truth on capture) to its module and proving test | P1 | team | ✔ |
| 8.16.26 | Trace rule #22 (no false capture declarations) to its module and proving test | P1 | team | ✔ |
| 8.16.27 | Trace rule #23 (scent model locked pre-game) to its module and proving test | P1 | team | ✔ |
| 8.16.28 | Trace rule #24 (hardware declaration sealed) to its module and proving test | P1 | team | ✔ |
| 8.16.29 | Trace rule #25 (LLM never decides the move) to its module and proving test | P1 | team | ✔ |
| 8.16.30 | Trace rule #26 (free natural language only) to its module and proving test | P1 | team | ✔ |
| 8.16.31 | Trace rule #27 (no numeric-position protocol) to its module and proving test | P1 | team | ✔ |
| 8.16.32 | Trace rule #28 (token-bucket limiter for reports) to its module and proving test | P1 | team | ✔ |
| 8.16.33 | Trace rule #29 (DOS detector guards the account) to its module and proving test | P1 | team | ✔ |
| 8.16.34 | Trace rule #30 (gmail.send scope only) to its module and proving test | P1 | team | ✔ |
| 8.16.35 | Trace rule #31 (minimum counted games vs different teams) to its module and proving test | P1 | team | ✔ |
| 8.16.36 | Trace rule #32 (automatic Gmail reporting) to its module and proving test | P1 | team | ✔ |
| 8.16.37 | Trace rule #33 (report is standard JSON) to its module and proving test | P1 | team | ✔ |
| 8.16.38 | Trace rule #34 (never free-text reports) to its module and proving test | P1 | team | ✔ |
| 8.16.39 | Trace rule #35 (agreed result + two separate reports) to its module and proving test | P1 | team | ✔ |
| 8.16.40 | Trace rule #36 (mutual audit each game) to its module and proving test | P1 | team | ✔ |
| 8.16.41 | Trace rule #37 (exact games-count declaration) to its module and proving test | P1 | team | ✔ |
| 8.16.42 | Trace rule #38 (no false count declarations) to its module and proving test | P1 | team | ✔ |
| 8.16.43 | Trace rule #39 (no secrets in the repo ever) to its module and proving test | P1 | team | ✔ |
| 8.16.44 | Trace rule #40 (credentials in .gitignore) to its module and proving test | P1 | team | ✔ |
| 8.16.45 | Trace rule #41 (tagged submission version) to its module and proving test | P1 | team | ✔ |
| 8.16.46 | Trace rule #42 (comprehensive academic report) to its module and proving test | P1 | team | ✔ |
| 8.16.47 | Trace rule #43 (Moodle form saved as PDF untouched) to its module and proving test | P1 | team | ✔ |
| 8.16.48 | Trace rule #44 (individual Moodle submission per member) to its module and proving test | P1 | team | ✔ |
| 8.16.49 | Trace rule #45 (unique 8-char team code) to its module and proving test | P1 | team | ✔ |
| 8.16.50 | Trace rule #46 (barrier on thief's cell is capture) to its module and proving test | P1 | team | ✔ |
| 8.16.51 | Trace rule #47 (thief with no legal move is captured) to its module and proving test | P1 | team | ✔ |
| 8.16.52 | Trace rule #48 (score by the fixed table) to its module and proving test | P1 | team | ✔ |
| 8.16.53 | Trace rule #49 (two repos, cross-links, four JSON links) to its module and proving test | P1 | team | ✔ |
| 8.16.54 | Trace rule #50 (repo carries README/config/PRD/PLAN/TODO) to its module and proving test | P1 | team | ✔ |
| 8.16.55 | Trace rule #51 (reports to the binding agent address) to its module and proving test | P1 | team | ✔ |
| 8.16.56 | Trace rule #52 (one counted game per opponent) to its module and proving test | P1 | team | ✔ |
| 8.16.57 | Trace rule #53 (step-0 declares the commit hash) to its module and proving test | P1 | team | ✔ |
| 8.16.58 | Trace rule #54 (final JSON reports total tokens) to its module and proving test | P1 | team | ✔ |
| 8.16.59 | Trace rule #55 (self-grade code quality only) to its module and proving test | P1 | team | ✔ |
| 8.17 | **README.md academic report** | P0 | team | ✔ |
| 8.17.1 | Dec-POMDP formalism: states, observations, uncertainty | P0 | team | ✔ |
| 8.17.2 | FastMCP orchestration dilemmas: turns, failures, gatekeeper/orchestrator | P0 | team | ✔ |
| 8.17.3 | Strategy chapters: three generations with measured tables | P0 | team | ✔ |
| 8.17.4 | Verbal layer + deception findings; interop conformance section | P0 | team | ✔ |
| 8.17.5 | Screenshot slots: Live GUI belief map + Replay Verified OK (owner-supplied) | P0 | team | ✔ |
| 8.17.6 | Cross-repo link section; code-quality self-grade (rule 55) | P0 | team | ✔ |
| 8.17.7 | Abstract and system overview with the C4 view | P0 | team | ✔ |
| 8.17.8 | Dec-POMDP: state space, action space, observation model, reward | P0 | team | ✔ |
| 8.17.9 | Belief machinery: scent evidence, motion judge, negative evidence, claim pin | P0 | team | ✔ |
| 8.17.10 | Strategy generation 0-1: pinch failure and the region cop | P0 | team | ✔ |
| 8.17.11 | Strategy generation 2: wall cop, red team, hybrid frontier table | P0 | team | ✔ |
| 8.17.12 | Deception chapter: measured lie economics and the adaptive policy | P0 | team | ✔ |
| 8.17.13 | Orchestration dilemmas: turn-taking, failures, watchdog, gatekeeper | P0 | team | ✔ |
| 8.17.14 | Interop chapter: the kit, the vectors, the bytes we fixed | P0 | team | ✔ |
| 8.17.15 | Results tables reproduced from the notebook | P0 | team | ✔ |
| 8.17.16 | Limitations and future work | P0 | team | ✔ |
| 8.18 | **Verification pass** | P0 | team | ✔ |
| 8.18.1 | ruff clean, coverage >= 85%, 150-line audit across every file | P0 | team | ✔ |
| 8.18.2 | Guidelines section 11.5 checklist walked item by item | P0 | team | ✔ |
| 8.18.3 | Full suite + notebook regeneration from clean clone | P0 | team | ✔ |
| 8.18.4 | Audit every src file against the 150-code-line law (report the top five) | P0 | team | ✔ |
| 8.18.5 | Audit every test file against the 150-code-line law | P0 | team | ✔ |
| 8.18.6 | Docstring sweep: module, class, function coverage across src | P0 | team | ✔ |
| 8.18.7 | Hardcoded-value sweep: every literal traced to config or constants | P0 | team | ✔ |
| 8.18.8 | Secrets sweep: history and working tree | P0 | team | ✔ |
| 8.18.9 | Determinism sweep: replay two full matches byte-identically | P0 | team | ✔ |
| 8.18.10 | Re-run kit verify_vectors.py + our 11-test conformance suite | P0 | team | ✔ |
| 8.18.11 | Regenerate the notebook from scratch and diff committed outputs | P0 | team | ✔ |
| 8.18.12 | Fresh-clone build: uv sync, full suite, demo scripts on a clean machine | P0 | team | ✔ |
| 8.19 | **Repo split + tag** | P0 | team | ☐ |
| 8.19.1 | Create police-agent and thief-agent repos from the dev repo | P0 | team | ☐ |
| 8.19.2 | Per-repo configs, docs, cross-links in both READMEs | P0 | team | ☐ |
| 8.19.3 | Two Moodle links; four links in the result JSON | P0 | team | ☐ |
| 8.19.4 | Tag v1.0-submission in both; verify grader access | P0 | team | ☐ |
| 8.19.5 | Decide per-repo file partition (shared domain vs role-specific config) | P0 | team | ☐ |
| 8.19.6 | Scrub dev-only artifacts (.sync, scratch results) from both trees | P0 | team | ☐ |
| 8.19.7 | Author police-agent README with cross-link to thief-agent | P0 | team | ☐ |
| 8.19.8 | Author thief-agent README with cross-link to police-agent | P0 | team | ☐ |
| 8.19.9 | Verify both repos pass the full gates independently | P0 | team | ☐ |
| 8.19.10 | Grant grader access / set visibility per rule 49 | P0 | team | ☐ |
| 8.19.11 | Record both URLs into configs, step-0 and the result links block | P0 | team | ☐ |

## Phase 9 — League operations (human + agent, from the pairing playbook)

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 9.1 | **Gmail OAuth day** | P0 | team | ✔ |
| 9.1.1 | Cloud Console project created; Gmail API enabled | P0 | team | ✔ |
| 9.1.2 | OAuth consent screen (External, Testing) + owner's account added as a Test user - first attempt hit Google's "Access blocked" (test user missing), fixed by adding it in Console, no code change | P0 | team | ✔ |
| 9.1.3 | Scope restricted to gmail.send only - already true in code (`infra/email/oauth.py`'s `GMAIL_SEND_SCOPE` is the single scope ever requested); `token.json`'s minted `scopes` field verified to contain exactly that one URL | P0 | team | ✔ |
| 9.1.4 | Desktop-app OAuth Client ID (`"installed"` key, `client_id`/`client_secret`, `redirect_uris: ["http://localhost"]` - confirmed desktop, not web); `credentials.json` verified present at repo root and `git check-ignore` confirms it is ignored | P0 | team | ✔ |
| 9.1.5 | First authorization flow ran (`InstalledAppFlow.run_local_server`, real browser consent) -> `token.json` minted with a `refresh_token`, `scopes == ["gmail.send"]`, `valid == True`; verified git-ignored | P0 | team | ✔ |
| 9.1.6 | REAL FINDING: `mode="draft"` calls Gmail's `drafts().create()`, which the API itself requires `gmail.compose` for - broader than the `gmail.send`-only scope rule #30 mandates, so draft mode can never work under a compliant scope (not a bug in our code, a hard Google API constraint) - confirmed by a live 403 `insufficientPermissions` on the first attempt. Real games use `mode="send"` anyway (`sender.py`'s FR-14), which needs only `gmail.send`, so both `config/police/game.toml` and `config/thief/game.toml` were switched `draft` -> `send` for the rehearsal (recipient still the owner's own address, not the binding league address, so `league.counted` stayed `false`/`"friendly"` - nothing armed). Re-ran `scripts/m7_report_demo.py`: gatekeeper log `status: sent`; a real email landed in the inbox with the canonical JSON as both body and attachment; owner confirmed receipt and its `mutual_agreement.sha256` (`81861ae2...`) was independently diffed byte-for-byte against the `results/result_*.json` written to disk - identical, confirming rule #34 | P0 | team | ✔ |
| 9.2 | **Identity** | P0 | team | ✔ |
| 9.2.1 | Team code chosen: `yanell11` (8 chars, no spaces) | P0 | team | ✔ |
| 9.2.2 | `config/{police,thief}/game.toml`: `group_id`/`group_name` -> `yanell11`/`YANELL11`, `members` -> real git identity, `repos.cop`/`repos.thief` -> the real dev repo (`github.com/Nell-Kh/police-thief-p2p`, both keys - repo split is 8.19, not yet done) on both roles; shared `config/game.json`'s descriptive `agreed_between[0]` -> `YANELL11` (`[1]` stays `OPPONENT-TBD` - genuinely unknown until a real opponent is arranged; the field isn't read by any code, purely descriptive) | P0 | team | ✔ |
| 9.2.3 | Step-0 group fields flow automatically from config (`match_runtime.py`'s `group_name=config.private_value("game", "group_name", ...)`), no code change needed - verified live: a fresh `MatchRuntime` for `police` sealed `step0.payload.group_name == "YANELL11"`. Full suite re-run after the 9.2.2 identity change: **621 passed**, 97.83% coverage (>= the 85% gate) | P0 | team | ✔ |
| 9.3 | **Screenshots** | P0 | team | ✔ |
| 9.3.1 | `scripts/capture_live_gui.py`: plays a real two-runtime local match (`test_two_peers.py` pattern) against shipped `config/`, drives police's `LiveWindow` every turn, DPI-aware screen-grabs the real Tk window once belief committed to an argmax (step 5) — `docs/img/live_gui_belief_heatmap.png`: own position "C", one placed barrier, heatmap gradient, "T?" argmax, "LOCKED" banner, "step 5 \| barriers used 2" — never the thief's true cell (rules #8/#9) | P0 | team | ✔ |
| 9.3.2 | `scripts/capture_replay_viewer.py`: same two-runtime local match, `police.book.save(logs/)` to the real on-disk `Logbook` format, opens the real `ReplayWindow` on that file, steps to the final turn (34, `survival`/thief), asserts `session.overall_verdict() == "Verified OK"` before capturing — `docs/img/replay_verified_ok.png`: green "Verified OK" banner, step 34, the closing hint, board with barriers, back/forward controls | P0 | team | ✔ |
| 9.3.3 | Both `docs/img/*.png` embedded into README §10 (Markdown image links, real captions, no more `[screenshot pending]` placeholders) | P0 | team | ✔ |
| 9.4 | **Friendlies** | P0 | team | ◐ |
| 9.4.0 | **Readiness audit + driver.** A pre-friendly audit found the repo could not actually *run* one: `python -m police_thief peer` only probes the handshake (`check_connectivity`) and never plays; `local_two_process_match.py` plays but writes no artifacts (so 9.4.3/9.4.4 were impossible with it); `sparring_series.py` writes artifacts but is hardwired to the kit (`OPPONENT_GROUP_ID` a module constant, forced scratch config, fixed role alternation). Wrote `scripts/friendly_series.py`: every opponent-specific value an argument (`--peer`, `--opponent-group-id`, `--start-role`, `--rounds`, `--port`, `--host`, `--public-url`, `--games-played`, `--config-dir`), all four artifact kinds written, uncounted by default, and a hard exit if a friendly ever reports `counted=true`. Extracted the machinery both drivers duplicated into `scripts/_series_lib.py` (`SwappableHandler`, `start_server`, `wait_for`, `play_networked`, `score_for`, `git_head`) and refactored `sparring_series.py` onto it, deleting ~100 duplicated lines | P0 | team | ✔ |
| 9.4.1 | Exchange first-contact message (turn order, model locks, ledger counts) | P0 | team | ☐ |
| 9.4.2 | Stage tunnels; handshake against a real opponent | P0 | team | ☐ |
| 9.4.3 | Play uncounted friendly; disarmed league fields verified — **driver + gate proven, real opponent still pending.** REAL two-process rehearsal of `friendly_series.py` (a second identity in a scratch `config/` with `group_id=rehearse`, played against our own shipped identity over real HTTP/MCP): 2 sub-games, roles alternating, both mutual audits **Verified OK**, and the written result carried `league: {"counted": false, "reason": "friendly"}` on **both** sides — the disarmed-fields check this task asks for. Still ☐ only because it has not been run against a real external opponent | P0 | team | ◐ |
| 9.4.4 | Diff both sides' artifacts; fix any divergence — **proven, no divergence.** Both bundles independently derived the identical `game_uid` (`46ad88dc-…`) and byte-identical `mutual_agreement.sha256`; the league kit's own `tools/check_artifacts.py <ours> <theirs>` (Python 3.12) returned **ALL ARTIFACT CHECKS PASS** then **ALL SETS AGREE** across all 13 cross-team join checks | P0 | team | ✔ |
| 9.4.5 | **Signed-term default corrected.** `config/game.json`'s `world.map_area` shipped as `"New York"` while every successful interop run used `"Haifa"` via a throwaway scratch copy — and `setting` is one of the 14 *signed* terms, so a kit-derived opponent refuses the handshake outright (exactly the refusal 8.15.3w hit). Committed default moved to `"Haifa"` (the kit peer's own default, so a friendly now agrees with zero pre-negotiation). Knock-on found and fixed: `infra/llm/template.py` keyed landmarks by arena and had no `"Haifa"` pool, so the shipped arena silently degraded to `GENERIC_LANDMARKS` — real Haifa landmarks added, and `test_the_shipped_arena_has_real_landmarks` now fails if any future arena change loses its pool. Docs corrected (`COMPLIANCE.md`, `PRD_scent_language.md` ×3) | P0 | team | ✔ |
| 9.4.6 | **Hybrid-cop guidance corrected — a perfect-information result that inverts under belief.** `config/police/game.toml` advertised `HybridPoliceBrain` as the speed profile to switch to against reference-fork opponents, on the notebook's perfect-information figure (~12 steps vs the wall's ~25). Re-measured under belief from the contract's fixed start — the only condition a league match is ever played in — the ordering **inverts**: wall captures Blind/Enhanced at step 28, hybrid at step 34, and both lose to the elite evader. Following the old comment mid-series would have cost real tempo. Corrected in `brain/hybrid.py`, `config/police/game.toml`, `README.md` §6 + results tables + limitations, and notebook §9b; the class and its tests stay as the documented research result | P1 | team | ✔ |
| 9.4.7 | **`ruff check` restored to clean.** 3 errors had accumulated in `scripts/` (2× SIM105 in the capture scripts, 1× import-order in `sparring_series.py`) after 8.18.1's clean sweep — the definition-of-done gate had quietly gone red | P2 | team | ✔ |
| 9.4.9 | **Kit conformance sweep: every check the league kit offers, run against the current tree.** Refreshed the `copthief-league-protocol` clone (already at `origin/main`, `596aaf4`) and ran all four: `verify_vectors.py` — **ALL VECTORS PASS**, 113 checks / 14 fixtures; `tools/check_artifacts.py` on two independently-produced bundles — **ALL ARTIFACT CHECKS PASS** then **ALL SETS AGREE**; `tools/probes/run_all.py` — **ALL PROBES GREEN** (7/7); `tools/netcheck.py` — documented in TUNNELING.md but not runnable until a real tunnel exists (9.4.2). The probes test the *kit*, so the real work was reading what each finding is ABOUT and auditing our own code for the same property. Two hits and one clean, below | P0 | team | ✔ |
| 9.4.10 | **Kit finding F-1 reproduced in OUR audit, and fixed: we accused honest peers of tampering.** SPEC §3 is explicit that "the payload schema itself is not an interop constraint" — a peer may legally seal `action+state` with no `position` key — and §3's degradation clause warns that treating our own schema as everyone's "is how a checker comes to call an honest, sealed, counted series *tampered*; that mistake has been made once in this kit and must not get a second home". We had made it **twice**: `verify_trajectory` appended `"unreadable position or move"` for *every* step of such a peer (failing the whole audit), and `verify_concession` returned `"...board/position is unreadable"`. Against an honest opponent with a legal schema this settles `tamper_forfeit` — and under rule 35 contradictory reports zero BOTH teams. Fixed per the spec's own prescription: new `sealing.parse_self_cell` reads the reference `self=` spelling as a second source, `audit.revealed_cell` tries `position` → `state` → degrades, and both layers now skip the checks the evidence cannot support while still running those it can (an illegal move is still caught without any position). The parse is STRICT as §3 demands — a malformed `state` degrades to `None` rather than resolving to a wrong cell, since a loose parse "invents a new way to accuse an honest peer, wearing a helpful hat". Two old tests that asserted the buggy `"unreadable"` behaviour were rewritten: they had encoded the bug as the expectation | P0 | team | ✔ |
| 9.4.11 | **Kit finding F-2 reproduced and fixed: a self-declared capture was believed, never checked.** `turn_receiving._apply_claim_response` set `result = capture` on any `caught: true` with zero corroboration, and the audit only ever looked at `type == "concession"` records with reason `boxed in (rule 47)` — so a `caught: true` echoing the cell the cop broadcasts every turn as `capture_claim` bypassed checking entirely. The kit calls this the worse lie: it pays the thief 5 AND the cop 20, "so both peers profit and neither has an incentive to look". `verify_concession` now corroborates a claimed cell against two independent sources — the revealed trail (must actually have reached it) and *our own barriers* (must already explain a capture there, rule 46 or 47) — ANDing whichever exist, and classifies answer-vs-concession by whether the claim echoes our own broadcast cell. Crucially the degradation NARROWS rather than switches off: a position-less concession over a cell our stones never touched is **still refused**, which is the third case the kit's probe guards precisely because F-1's fix could otherwise quietly repeal F-2's. Evidence is threaded from local state only — new `WorldView.final_claim`/`final_claim_is_answer`, new `MatchRuntime.audit_evidence()`, consumed by all three drivers — so nothing trusts a byte of the opponent's reveal. All 8 cases of the kit's own `probe_f1_concession_corroboration.py` ported verbatim into `test_logbook_audit.py` and passing | P0 | team | ✔ |
| 9.4.12 | **Kit finding D3 checked and NOT present.** The kit's stale-step probe shows `ref_delivery_decision` computing `step - next`, which is negative for a step below `next` and therefore always "buffer" — a buffer entry that can never drain, because draining only ever looks for `next`. Our `InboundHandler.receive_turn` tests `message.step < self.next_step` **first** (inbound.py:108) and absorbs the stale arrival idempotently, before any window arithmetic, so the unpinned state cannot arise. Verified by reading, no change needed. D1 (astral-key sort order) likewise cannot bite us: our only non-ASCII key is the Hebrew consensus key, which is BMP where Python's code-point sort and UTF-16 code-unit sort coincide | P1 | team | ✔ |
| 9.4.13 | **Opening handshake made a rendezvous in the play drivers too (not just `peer`).** After 9.4.8 fixed `peer`, `friendly_series.py` still had the same race in the place that actually matters: `client.negotiate` carried the in-match budget (~15s) while the very next line waited a patient 180s for *their* greeting — so an opponent more than ~15s late killed the driver at sub-game 1. Added `_series_lib.negotiate_patiently` (retry only `PeerUnreachableError`, propagate a refusal at once since no waiting fixes a digest mismatch), wired into all three drivers, with `--wait` on `friendly_series.py` (default 120s). Verified live: police started, thief joined **20s later**, both sub-games played, both audits Verified OK, and `check_artifacts.py` on the two bundles printed ALL SETS AGREE. `docs/TUNNELING.md` rewritten accordingly — it still described the old fail-fast behaviour — and now also documents `netcheck.py`'s loopback proof and the refusal-vs-silence distinction | P0 | team | ✔ |
| 9.4.14 | **Operational note from kit probe P5 (archive sweep).** `check_artifacts.py`'s two-directory join collects with `rglob` while the single-directory check uses non-recursive `glob`, so pointing the join at a tree containing *several* archived series makes honest history look like the rule-35 contradictory-report shape — "the single scariest verdict the tool can emit". `friendly_series.py` writes each series into its own `results/friendly_<game_id>/` folder, which is the layout that triggers it, so the join must always be pointed at the two specific series folders (`check_artifacts.py results/friendly_<id> <theirs>`), never at `results/` | P2 | team | ✔ |
| 9.4.8 | **Two-terminal handshake race fixed — `peer --role thief` + `peer --role police` now both succeed.** REAL bug reported from a two-terminal run: whichever peer was started *first* always reported `handshake FAILED: opponent unreachable`, and only the second succeeded. Two compounding causes. (1) `check_connectivity` fired exactly one handshake the instant it booted, and `PeerClient.call`'s budget is only `max_retries=3 × retry_backoff_sec=5` ≈ 15s — deliberately short so a *mid-match* silence becomes a technical loss fast, which is precisely the wrong budget for an opening handshake between two terminals a human starts seconds apart. (2) That single attempt went through `Orchestrator.run_guarded`, which converts `PeerUnreachableError` into `fail()` → `PHASE_TECHNICAL_LOSS` — and `TRANSITIONS[PHASE_TECHNICAL_LOSS]` is `frozenset()`, i.e. terminal with no exits, so the orchestrator was permanently poisoned after the first miss and no retry was even possible. Fixed with a real rendezvous in `services/peer_boot.py`: a new `rendezvous()` retries `start_match` *directly* (never via `run_guarded`) across a bounded window (`--wait`, default 120s), announcing "opponent not up yet - waiting"; and because the peer that shakes hands first would otherwise exit while the slower side was still dialling — the mirror-image race — it then lingers, still serving, for `--linger` (default 15s). A refusal (contract/lock mismatch) is distinguished from a silence and reported verbatim *without* retrying, since no amount of waiting fixes a digest mismatch; a one-sided handshake (we heard them, they can't hear us) now names `[network].opponent_url` as the likely cause. Verified live in BOTH start orders with a 25–30s gap: thief-first and police-first, both peers report `handshake OK`. 5 regression tests added (`test_http_transport.py`), incl. the exact race, the bounded window, the no-retry-on-refusal rule and the linger | P0 | team | ✔ |
| 9.5 | **Counted series** | P0 | team | ☐ |
| 9.5.1 | Pre-T exchange of declared counts (rule 37) | P0 | team | ☐ |
| 9.5.2 | Counted six-sub-game series vs opponent one | P0 | team | ☐ |
| 9.5.3 | Counted series vs opponent two (min_games_to_pass=2) | P0 | team | ☐ |
| 9.5.4 | Both reports emailed; ledger advanced after each series | P0 | team | ☐ |

## Phase 10 — Test-suite inventory (every file, kept green under every refactor)

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 10.1 | Maintain `integration/test_blind_strategy.py` (7 tests) green under every refactor | P0 | team | ✔ |
| 10.2 | Maintain `integration/test_inference_loop.py` (4 tests) green under every refactor | P0 | team | ✔ |
| 10.2b | Maintain `integration/test_determinism.py` (2 tests) green under every refactor | P0 | team | ✔ |
| 10.3 | Maintain `integration/test_local_game.py` (13 tests) green under every refactor | P0 | team | ✔ |
| 10.4 | Maintain `integration/test_two_peers.py` (7 tests) green under every refactor | P0 | team | ✔ |
| 10.5 | Maintain `interop/test_kit_vectors.py` (11 tests) green under every refactor | P0 | team | ✔ |
| 10.5b | Maintain `interop/test_kit_delivery.py` (3 tests) green under every refactor | P0 | team | ✔ |
| 10.6 | Maintain `unit/test_constants.py` (15 tests) green under every refactor | P0 | team | ✔ |
| 10.7 | Maintain `unit/test_domain/test_belief.py` (17 tests) green under every refactor | P0 | team | ✔ |
| 10.8 | Maintain `unit/test_domain/test_board.py` (18 tests) green under every refactor | P0 | team | ✔ |
| 10.9 | Maintain `unit/test_domain/test_brains.py` (16 tests) green under every refactor | P0 | team | ✔ |
| 10.10 | Maintain `unit/test_domain/test_crypto.py` (12 tests) green under every refactor | P0 | team | ✔ |
| 10.11 | Maintain `unit/test_domain/test_engine.py` (18 tests) green under every refactor | P0 | team | ✔ |
| 10.12 | Maintain `unit/test_domain/test_enhanced_brains.py` (9 tests) green under every refactor | P0 | team | ✔ |
| 10.13 | Maintain `unit/test_domain/test_hybrid_brain.py` (6 tests) green under every refactor | P0 | team | ✔ |
| 10.14 | Maintain `unit/test_domain/test_logbook_audit.py` (15 tests) green under every refactor | P0 | team | ✔ |
| 10.15 | Maintain `unit/test_domain/test_negotiation.py` (10 tests) green under every refactor | P0 | team | ✔ |
| 10.16 | Maintain `unit/test_domain/test_pathfind.py` (16 tests) green under every refactor | P0 | team | ✔ |
| 10.17 | Maintain `unit/test_domain/test_region_brain.py` (10 tests) green under every refactor | P0 | team | ✔ |
| 10.18 | Maintain `unit/test_domain/test_replay.py` (8 tests) green under every refactor | P0 | team | ✔ |
| 10.19 | Maintain `unit/test_domain/test_rules.py` (25 tests) green under every refactor | P0 | team | ✔ |
| 10.20 | Maintain `unit/test_domain/test_scent.py` (12 tests) green under every refactor | P0 | team | ✔ |
| 10.21 | Maintain `unit/test_domain/test_scoring.py` (13 tests) green under every refactor | P0 | team | ✔ |
| 10.22 | Maintain `unit/test_domain/test_sealing.py` (8 tests) green under every refactor | P0 | team | ✔ |
| 10.23 | Maintain `unit/test_domain/test_state.py` (13 tests) green under every refactor | P0 | team | ✔ |
| 10.24 | Maintain `unit/test_domain/test_trust.py` (18 tests) green under every refactor | P0 | team | ✔ |
| 10.25 | Maintain `unit/test_domain/test_turnmsg.py` (13 tests) green under every refactor | P0 | team | ✔ |
| 10.26 | Maintain `unit/test_domain/test_wall_and_evade.py` (11 tests) green under every refactor | P0 | team | ✔ |
| 10.27 | Maintain `unit/test_infra/test_email_oauth.py` (5 tests) green under every refactor | P0 | team | ✔ |
| 10.28 | Maintain `unit/test_infra/test_email_reports.py` (12 tests) green under every refactor | P0 | team | ✔ |
| 10.29 | Maintain `unit/test_infra/test_email_sender.py` (10 tests) green under every refactor | P0 | team | ✔ |
| 10.30 | Maintain `unit/test_infra/test_http_transport.py` (11 tests) green under every refactor | P0 | team | ✔ |
| 10.31 | Maintain `unit/test_infra/test_llm.py` (16 tests) green under every refactor | P0 | team | ✔ |
| 10.32 | Maintain `unit/test_infra/test_llm_providers.py` (10 tests) green under every refactor | P0 | team | ✔ |
| 10.33 | Maintain `unit/test_infra/test_mcp_client.py` (9 tests) green under every refactor | P0 | team | ✔ |
| 10.34 | Maintain `unit/test_infra/test_mcp_server.py` (4 tests) green under every refactor | P0 | team | ✔ |
| 10.35 | Maintain `unit/test_infra/test_transport.py` (5 tests) green under every refactor | P0 | team | ✔ |
| 10.36 | Maintain `unit/test_services/test_concession.py` (8 tests) green under every refactor | P0 | team | ✔ |
| 10.37 | Maintain `unit/test_services/test_deadline.py` (13 tests) green under every refactor | P0 | team | ✔ |
| 10.38 | Maintain `unit/test_services/test_deception.py` (9 tests) green under every refactor | P0 | team | ✔ |
| 10.39 | Maintain `unit/test_services/test_hostile_wire.py` (14 tests) green under every refactor | P0 | team | ✔ |
| 10.40 | Maintain `unit/test_services/test_inbound.py` (13 tests) green under every refactor | P0 | team | ✔ |
| 10.41 | Maintain `unit/test_services/test_orchestrator.py` (13 tests) green under every refactor | P0 | team | ✔ |
| 10.42 | Maintain `unit/test_services/test_phase_machine.py` (14 tests) green under every refactor | P0 | team | ✔ |
| 10.43 | Maintain `unit/test_services/test_watchdog.py` (9 tests) green under every refactor | P0 | team | ✔ |
| 10.44 | Maintain `unit/test_services/test_wiring.py` (4 tests) green under every refactor | P0 | team | ✔ |
| 10.45 | Maintain `unit/test_shared/test_bucket.py` (6 tests) green under every refactor | P0 | team | ✔ |
| 10.46 | Maintain `unit/test_shared/test_config.py` (15 tests) green under every refactor | P0 | team | ✔ |
| 10.47 | Maintain `unit/test_shared/test_config_io.py` (16 tests) green under every refactor | P0 | team | ✔ |
| 10.48 | Maintain `unit/test_shared/test_contract_values.py` (7 tests) green under every refactor | P0 | team | ✔ |
| 10.49 | Maintain `unit/test_shared/test_gatekeeper.py` (7 tests) green under every refactor | P0 | team | ✔ |
| 10.50 | Maintain `unit/test_shared/test_version.py` (11 tests) green under every refactor | P0 | team | ✔ |

## Phase 11 — Adversarial review remediation (`docs/REVIEW_HOSTILE.md`)

External hostile review, run against the two PDFs rather than against `docs/COMPLIANCE.md`.
Findings are transcribed here verbatim in severity order. Every row carries the rule number or
guideline section it answers to, so a closed row can be checked against the source and not
against a claim in this file.

**Ground rules for this phase.** A row is ✔ only when the artifact on disk proves it — not when
the code that would produce the artifact exists. 11.3 in particular cannot be closed by editing
any file in this repository.

### 11.1 — BLOCKERS (submission gate; these fail before any code is read)

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 11.1 | **Submission blockers — the six gates that fail independently of code quality** | P0 | team | ◐ |
| 11.1.0 | **Pin line endings to LF (`.gitattributes` + `git add --renormalize`).** Discovered while starting 11.1.11: the tree's 193 "modified" files were a whole-repo CRLF conversion with zero content change (`git diff --ignore-cr-at-eol` empty). Committing it would have rewritten the byte-exact `tests/vectors/` fixtures and buried real history under a 22.8k-line diff | P0 | team | ✔ |
| 11.1.1 | Split the dev repo into `police-agent` and `thief-agent`, both accessible to the lecturer (rule #49, App. ג) | P0 | team | ☐ |
| 11.1.2 | Cross-link the two READMEs: cop README → thief repo, thief README → cop repo (rule #49) | P0 | team | ☐ |
| 11.1.3 | Fix `repos = { cop = …, thief = … }` in BOTH per-peer TOMLs — currently the same URL twice, so the report's four-link block ships two duplicates (rule #49). **Blocked by 11.1.1**: needs the two real URLs | P0 | team | ☐ |
| 11.1.4 | Fill `README.md` §11 with the two real URLs, replacing `TBD — task 8.19`. **Blocked by 11.1.1** | P0 | team | ☐ |
| 11.1.5 | Carry `README`, `config/`, all `PRD_*`, `PLAN.md`, `TODO.md` into both repos (rule #50). **Blocked by 11.1.1** | P0 | team | ☐ |
| 11.1.6 | Point `[email] recipient` at `rmisegal+uoh26finalgame@gmail.com` in both TOMLs — `_is_armed()` was correctly disarming every report, so 100 % of games scored `counted: false` (rules #32/#51). Also pinned `mode = "draft"` as the committed resting state so no demo can mail the lecturer | P0 | team | ✔ |
| 11.1.7 | Add a preflight assertion that refuses to start a counted series when the reporting config cannot score. Landed as `shared.preflight.counted_series_blockers()` covering BOTH the address (#51) and delivery mode (#32); `friendly_series.py` delegates to it, `scripts/preflight.py --counted` checks it the night before and exits 1. 7 regression tests | P1 | team | ✔ |
| 11.1.8 | Un-ignore the four lifecycle artifacts: `.gitignore` narrowed to scratch only (`*.tmp`, `rows_checkpoint.json`, `*.superseded-*`) — App. ו Mandatory Rules #4 requires every game's config file in the repo | P0 | team | ✔ |
| 11.1.9 | Commit `declaration_*.json`, `config_*_gNN.json`, `log_*_gNN.json`, `result_*.json`. Rehearsal set (self-play + 6-game sparring) now tracked with `results/README.md` stating plainly that it is `counted: false, reason: friendly` and not league play. **Re-open per counted game** as 11.3.2/11.3.3 land | P0 | team | ◐ |
| 11.1.10 | Verify with `git ls-files results/ logs/` that the artifacts are actually tracked — was returning only `results/.gitkeep`, now returns 21 files | P0 | team | ✔ |
| 11.1.11 | Commit the working tree. Resolved via 11.1.0: the 193 modifications were line-endings, not work. Tree is clean; the sealed Step-0 commit hash is now meaningful (rules #53/#38) | P0 | team | ✔ |
| 11.1.12 | Create and push the annotated tag `v1.0-submission` on both repos (rule #41, App. ג checklist). **Deliberately deferred**: the tag must mark the submission commit on each of the two final repos, so tagging the pre-split dev repo would point it at the wrong place. **Blocked by 11.1.1** | P0 | team | ☐ |
| 11.1.13 | Verify the tag with `git show v1.0-submission` and confirm it points at the commit that actually played. **Blocked by 11.1.12** | P1 | team | ☐ |
| 11.1.14 | `git push origin main` — the 11.1 commits are local only; the environment they were authored in has no push credentials | P0 | team | ☐ |

### 11.2 — Interop landmines (each zeroes US **and** an innocent opponent under rule #35/#19)

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 11.2 | **The kit-vs-book bet, made explicit and made reversible** | P0 | team | ☐ |
| 11.2.1 | Write the bet down in `README.md` §8: the project adopts `copthief-league-protocol` conventions over the printed book in four places. The book's academic-freedom clause permits this ONLY if the contradiction, the choice and the reason are all stated | P0 | team | ☐ |
| 11.2.2 | Add `[interop] profile = "kit" \| "book"` to the per-peer TOML, defaulting to `kit`, covering all four deviations below | P0 | team | ☐ |
| 11.2.3 | **Seal format.** `crypto.digest_of` computes `sha256(canonical(payload) + "\|" + nonce)`; the book ch. 5.3.1 prints the nonce INSIDE the JSON. Against a book-literal opponent every step fails the audit in both directions (rule #19). Implement the book variant behind the profile switch | P0 | team | ☐ |
| 11.2.4 | **Scent clamp.** `scent.ScentField.advance` applies `min(ceiling, …)`; the book ch. 4.3 formula has only `max(0, …)`. It bites on the first re-emission (`0.9·0.9+0.9 = 1.71 → 0.9`) and the grid crosses the wire as `smell_grid`. Implement the unclamped variant behind the profile switch | P0 | team | ☐ |
| 11.2.5 | **Consensus serialization.** `consensus.serialize_spaced` uses `(", ", ": ")` while every other hash is compact. Implement the compact variant behind the profile switch | P0 | team | ☐ |
| 11.2.6 | **Tie-award semantics.** `consensus.series_aggregate` ADDS `tie_score` into `total_score`, which sits inside the settlement scope. App. ו table 17 reads as the score *for* a tie, not a bonus on top. Implement substitution behind the profile switch and declare the ambiguity in the report | P0 | team | ☐ |
| 11.2.7 | Remove `pheromone_min_center_intensity` from `config/game.json` and from the 14 signed terms, or make `validate_terms` tolerate its absence. A book-conformant opponent has 13 keys to our 14 → handshake refused (App. ב: field names are fixed and binding) | P0 | team | ☐ |
| 11.2.8 | Remove the extra top-level `"version"` key from `config/game.json` (not in the App. ב listing) | P1 | team | ☐ |
| 11.2.9 | Decide `map_area`: App. ו says a negotiable parameter defaults to the printed example (`"New York"`) absent explicit agreement. `"Haifa"` is a signed term (`setting`) and refuses a kit-naive opponent. Either revert the default or negotiate it in writing before every series | P1 | team | ☐ |
| 11.2.10 | Wire `mutual_agreement.confirmed` to the real audit outcome — `reports.py:128` hardcodes `True` and nothing anywhere sets it `False`, so the report asserts agreement with an opponent that may not exist (rules #35/#38) | P0 | team | ☐ |
| 11.2.11 | Stop calling unkeyed hashes "signatures". `interop.sign_terms` and `report_blocks.group_block` are `sha256` over data that travels beside them; the `"terms signature does not verify"` branch is unreachable for any well-formed greeting. Either implement keyed signing (book ch. 5.5 says "מפתח המסופק מראש") or rename to `*_sha256` and state the scope decision in the report | P1 | team | ☐ |
| 11.2.12 | Negotiate turn order. `engine.py:8` hardcodes cop-first and correctly notes the book does not fix one — but it is absent from the 14 signed terms AND from `negotiate_extras`, so two peers with opposite orders shake hands and then disagree about the board. Add it to the declarations or prove in the report that the turn-token makes it unobservable | P1 | team | ☐ |
| 11.2.13 | Replace `engine.end_turn`'s `min(threshold, ceiling)` with `survival_threshold` alone. Both are "minimum"-status params negotiable upward independently; if they ever differ we declare survival early and a book-literal opponent does not → divergent winner, rule #35 | P1 | team | ☐ |
| 11.2.14 | Add a regression test per deviation asserting BOTH profiles produce their intended digest, so a future refactor cannot collapse them | P1 | team | ☐ |

### 11.3 — League conduct (cannot be closed by editing this repository)

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 11.3 | **Play real opponents** — every artifact in `results/` is currently self-play | P0 | team | ⏱ |
| 11.3.1 | Run `scripts/friendly_series.py` against a real external team as a warm-up (rule #52 permits uncounted friendlies) | P0 | team | ⏱ |
| 11.3.2 | Play counted series #1 against a real team: 6 sub-games, clean audits, both sides mail their own report (rules #31/#35). **Runbook: set `[email].mode = "send"` in both TOMLs first** — it is committed as `draft` so nothing can mail the lecturer by accident, and `friendly_series.py --counted` will refuse until it is flipped | P0 | team | ⏱ |
| 11.3.3 | Play counted series #2 against a DIFFERENT team — `min_games_to_pass = 2`, and without it there is no passing grade at all (rule #31) | P0 | team | ⏱ |
| 11.3.4 | Confirm both opponents' reports reached the league inbox and agree with ours field-for-field (rule #35 zeroes both teams on a contradiction) | P0 | team | ⏱ |
| 11.3.5 | Replace `agreed_between: ["YANELL11", "OPPONENT-TBD"]` with the real counterparty per series | P0 | team | ☐ |
| 11.3.6 | Purge `TEAM-TBD` / `id-TBD` / `github.com/TBD/…` placeholders from every committed artifact | P1 | team | ☐ |
| 11.3.7 | Run `shared/preflight.py` against each opponent's `game.json` the night before, per the review's own recommendation | P1 | team | ☐ |

### 11.4 — Security

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 11.4 | **Secrets hygiene** — git history verified clean; the exposure is at rest | P0 | team | ☐ |
| 11.4.1 | Rotate `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GMAIL_APP_PASSWORD`, `MCP_AUTH_TOKEN` in `.env` — all four were readable in plaintext during review | P0 | team | ☐ |
| 11.4.2 | Revoke and re-issue `token.json` (live OAuth access token) and the `credentials.json` OAuth client | P0 | team | ☐ |
| 11.4.3 | Move the repo out of `OneDrive\Desktop`, or add it to OneDrive's exclusion list — the four secrets are currently synced to Microsoft's cloud | P0 | team | ☐ |
| 11.4.4 | Re-verify after the move: `git log --all` tree sweep shows no secret ever committed (confirmed clean at review time — keep it that way) | P1 | team | ☐ |

### 11.5 — Documentation honesty

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 11.5 | **`docs/COMPLIANCE.md` misquotes its own codebase** — six of six spot-checked cells were wrong | P1 | team | ☐ |
| 11.5.1 | Rule #23 cites `negotiation.scent_lock_for` — no such symbol exists. Correct to `interop.scent_model_lock` / `scent.lock_sha256` | P1 | team | ☐ |
| 11.5.2 | Rule #46 cites `_apply_barrier` as the engine's; that name lives in `services/turn_receiving.py`, the engine's is `_place_barrier` | P1 | team | ☐ |
| 11.5.3 | Rule #47 says `is_trapped` is checked in `engine.end_turn`; it is checked in `_check_termination` | P1 | team | ☐ |
| 11.5.4 | Rule #49 cites `result_payload(repositories=…)` — no such parameter; it is `links` | P1 | team | ☐ |
| 11.5.5 | Rule #54 cites `result_payload(tokens_total=…)` — no such parameter; the total is derived from rows | P1 | team | ☐ |
| 11.5.6 | Correct the counts: "689 tests" and "613 tests" both appear; actual is 699. `.gitignore` "lines 2–5" is 2–6. "largest src file `turn_taking.py`, 92 code lines" is `series_guard.py`, 102 | P1 | team | ☐ |
| 11.5.7 | Generate the rule→symbol references mechanically (or drop them) so the matrix cannot drift again | P2 | team | ☐ |
| 11.5.8 | Update rule #45's status — the 8-char code `YANELL11` already exists; the row still says "to be finalized" | P2 | team | ☐ |
| 11.5.9 | Fold `docs/REVIEW_HOSTILE.md` into the documentation index in `README.md` §"Documentation index" | P2 | team | ☐ |

### 11.6 — Guidelines compliance

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 11.6 | **Residual guideline debt** | P1 | team | ☐ |
| 11.6.1 | Split `src/police_thief/services/series_guard.py` — 160 lines under the guidelines' own plain wording (§3.2: blanks and comments excluded, docstrings NOT mentioned as excluded). Clean seam: checkpointing ↔ containment | P1 | team | ☐ |
| 11.6.2 | Note the counting-rule tension in `test_file_size_law.py`: guidelines p.24 lists "קבצים עד 150 שורות קוד, הערות ו-docstrings", which cuts against excluding docstrings. Our test currently exempts the one `src/` file that fails the plain reading | P1 | team | ☐ |
| 11.6.3 | Split `scripts/build_notebook.py` (514 code lines), `scripts/friendly_series.py` (291), `scripts/sparring_series.py` (227) — over the cap on ANY reading, currently on the `KNOWN_OVER_LIMIT` debt list | P1 | team | ☐ |
| 11.6.4 | Fix `shared/sysinfo.py` on Windows: `_cpu_frequency_mhz` reads `/proc/cpuinfo` and `_total_ram_gb` uses `os.sysconf`, both Linux-only, so the sealed declaration ships `cpu_mhz: 0.0, ram_gb: 0.0` on our actual machine. Rule #24's sanction is loss of the computational-fairness bonus, and it is a false declaration besides | P1 | team | ☐ |
| 11.6.5 | Add a test asserting the hardware spec has non-zero CPU and RAM on the platform that will actually play | P1 | team | ☐ |
| 11.6.6 | Resolve `config/rate_limits.json`'s dead `anthropic` and `default` blocks — read by no code path (self-admitted, ADR-3). Wire them or delete them (guidelines §7.2) | P2 | team | ☐ |
| 11.6.7 | Complete the `tests/` docstring sweep still owed from the 8.18 pass | P2 | team | ☐ |

### 11.7 — Strengths to defend rather than fix

| # | Task | Priority | Owner | Status |
|---|---|---|---|---|
| 11.7 | **Make the genuinely strong work visible to the grader** | P2 | team | ☐ |
| 11.7.1 | Foreground `domain/audit.py`'s trajectory layer in `README.md` — a hash-clean log that teleports or crosses a barrier still fails, which the reference implementation does not do | P2 | team | ☐ |
| 11.7.2 | Foreground `test_hostile_wire.py` + `_disclosed_records` structural hardening: a malicious peer forfeits instead of crashing us | P2 | team | ☐ |
| 11.7.3 | Foreground `series_guard.containment_alarm()` — a warning that accuses our own driver first when every sub-game contains | P2 | team | ☐ |
| 11.7.4 | Foreground `report_blocks._is_armed()` as the fail-safe that keeps a recipient misconfiguration from becoming a rule-#38 false claim | P2 | team | ☐ |
| 11.7.5 | Foreground `shared/preflight.py` — finding a handshake refusal the night before instead of at kickoff | P2 | team | ☐ |

## Test Accounting (delivery + capture-final work, from the 580 baseline to 588)
- `tests/interop/test_kit_vectors.py`: +3 (`test_delivery_contract_arrivals`, `test_no_reorder_window`, `test_buffered_steps_replay_in_order`)
- `tests/unit/test_services/test_concession.py`: +2 (`test_the_police_accepts_the_new_kit_shape_concession`, `test_a_claim_response_from_the_police_is_a_violation`)
- `tests/unit/test_services/test_inbound.py`: +2 (`test_a_concession_records_the_final_commit_without_overwriting`, `test_a_same_step_survival_claim_with_a_new_commit_is_refused`)
- `tests/unit/test_services/test_deadline.py`: +1 (`test_tolerated_traffic_never_renews_the_deadline`)

## Test Accounting (verification pass 8.18 + report alignment 8.14, from 611 to 621)
- `tests/interop/test_kit_vectors.py` split into `test_kit_vectors.py` + new `test_kit_delivery.py` (150-line law); same 19 tests, no net change.
- `tests/integration/test_determinism.py`: +2, new file (`test_two_full_matches_from_the_same_start_reach_the_same_trajectory`, `test_replaying_the_same_log_twice_is_byte_identical`)
- `tests/unit/test_infra/test_email_reports.py`: +2 (`test_a_counted_claim_arms_when_addressed_to_the_binding_league_address`, `test_a_counted_claim_disarms_when_the_recipient_is_not_the_binding_address`)
- `tests/unit/test_infra/test_email_sender.py`: +1 (`test_the_email_body_carries_the_same_canonical_bytes_as_the_attachment`)
- `tests/unit/test_domain/test_logbook_audit.py`: +5 (`test_a_true_rule_47_concession_corroborates_and_passes`, `test_a_false_rule_47_concession_is_caught_by_the_audit`, `test_verify_concession_ignores_non_rule47_reasons`, `test_verify_concession_flags_a_rule47_claim_with_no_prior_turn`, `test_verify_concession_flags_an_unreadable_last_turn`)

## Milestones

- **M1** two agents move legally on 7×7; quota-excess barrier rejected; overlap captures.
- **M2** a geometric message crosses localhost between the two peers and decodes.
- **M3** shortest-path pursuit executes with no manual intervention.
- **M4** free-language report → inference; scent decays; hints truth or lie.
- **M5** a remote agent connects via tunnel and plays a full round.
- **M6** commit→reveal verifies; Step-0 seals hardware and the commit hash.
- **M7** Gmail summary sent; live GUI shows local truth; replay stamps Verified OK.
- **M8** both submission repos tagged, cross-linked, checklist clean.
- **M9** Phase 11 clear: the six submission blockers closed, the kit-vs-book bet declared and
  reversible behind `[interop] profile`, secrets rotated, and two counted series played against
  two different real teams with both sides' reports agreeing field-for-field.
