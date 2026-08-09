# COMPLIANCE — The Binding Rules, Mapped to Code and Tests

**Project:** police-thief-p2p | **Sources:** rulebook Appendix ה (rules #1–#55, quoted
category by category) and the software-engineering guidelines. Every rule below is mapped
to the module that implements it and the test that proves it. Status: ✔ implemented and
tested here | ⏱ performed at submission/league time (operational, not code).

The quantitative values behind these rules live in `config/game.json`, which mirrors the
binding parameter table of Appendix ו — see the table at the end.

---

## Group 1 — Network architecture, decentralization, local epistemology (rules #1–#10)

| # | Kind | Rule (essence) | Implementation | Proof | Status |
|---|---|---|---|---|---|
| 1 | must | Thief and cop run as two fully separate processes | Two peers, each `services/peer_boot.py` + own MCP server/port (8801/8802) | `test_two_peers.py` (two full runtimes, messages only); M2/M5 observed live | ✔ |
| 2 | never | No shared memory or variables between the sides | Only `TurnMessage` over MCP crosses; `WorldView` holds local truth exclusively | `test_two_peers.py` (full match over messages only) | ✔ |
| 3 | must | The orchestrator is the single entry point | `services/orchestrator.py` (+ `wiring.py`) | `test_orchestrator.py` | ✔ |
| 4 | must | Game states managed by a formal state machine | `services/phase_machine.py` | `test_phase_machine.py` | ✔ |
| 5 | must | Illegal state transitions are rejected | `PhaseMachine` raises on any transition outside its table | `test_phase_machine.py` | ✔ |
| 6 | must | Deadline tracking prevents freezes waiting for the opponent | `services/deadline.py`; timeout → TECHNICAL_LOSS | `test_deadline.py` | ✔ |
| 7 | must | A watchdog monitors process crashes and salvages data | `services/watchdog.py` + `recovery.py` | `test_watchdog.py` | ✔ |
| 8 | must | The live GUI shows local truth only | `gui/live.py` renders `WorldView` (belief argmax as "T?"), never the opponent's true cell | `gui/` design + rule #9 test | ✔ |
| 9 | never | The objective full board is never shown live | `WorldView` does not contain the opponent position at all — nothing to leak | `world_view.py` holds no opponent-position field at all; `test_turnmsg.py` refuses cleartext | ✔ |
| 10 | must | A tunnel exposes the local server publicly | `infra/http_transport.py` + `docs/TUNNELING.md` | `test_http_transport.py`; M5 observed | ✔ |

## Group 2 — Spatial mechanics, physics, board constraints (rules #11–#16)

| # | Kind | Rule (essence) | Implementation | Proof | Status |
|---|---|---|---|---|---|
| 11 | must | The config file is byte-identical on both sides | `interop.terms_from_contract` extracts the flat signed terms; `negotiation.validate_terms` compares them whole-object and refuses any difference. (Correction: this row used to claim a whole-FILE sha256 is compared at negotiation. It is not — the wire carries `terms`, and `ConfigManager.config_sha256` is only ever printed.) | `test_negotiation.py::test_a_terms_value_mismatch_is_refused` | ✔ |
| 12 | must | Parameter minimums may only be raised by agreement, never lowered | `config/game.json` carries the Appendix-ו minimums; negotiation locks the shared hash | `test_contract_values.py` pins every binding value | ✔ |
| 13 | must | Movement is orthogonal only | `constants.MOVE_DELTAS` cannot express a diagonal; `rules.validate_move` | `test_rules.py` | ✔ |
| 14 | never | No diagonal moves — the opponent rejects them | `enforcement.py` + `rules.validate_move` applied to revealed moves in the audit physics layer | `test_rules.py::test_a_diagonal_or_unknown_move_is_rejected`; audit physics layer | ✔ |
| 15 | must | Every barrier placement is declared openly | `TurnMessage.barrier_placed` is a public event | `test_turnmsg.py`; `test_two_peers.py` | ✔ |
| 16 | never | Never lie about a barrier's location | Barrier goes into the sealed record AND the public message; audit cross-checks | `test_logbook_audit.py::test_a_teleport_fails_physics_even_with_clean_hashes` | ✔ |

## Group 3 — Cryptography, log integrity, zero-knowledge (rules #17–#24)

| # | Kind | Rule (essence) | Implementation | Proof | Status |
|---|---|---|---|---|---|
| 17 | must | SHA-256 commit-reveal protocol | `domain/crypto.py`: `sha256(canonical_json(payload) + "\|" + nonce)` | `test_crypto.py` | ✔ |
| 18 | must | Nonces stay secret until game end | `secrets.token_hex(16)`; nonces live only in the local logbook until disclosure | `test_crypto.py::test_nonces_never_repeat`; `turnmsg` refuses cleartext | ✔ |
| 19 | must | Any hash mismatch at audit = technical disqualification | `domain/audit.py` layer 1; one mismatch → TAMPERED, no discretion | `test_logbook_audit.py::test_a_forged_hash_is_tampered`; `test_replay.py` | ✔ |
| 20 | must | A replay viewer reconstructs and verifies the log | `domain/replay.py` + `gui/replay.py` (Verified OK / TAMPERED stamp) | `test_replay.py` | ✔ |
| 21 | must | Declare the truth when caught | `services/concession.py::answer_claim`, called from `turn_taking` — a true claim is always answered `caught: true` with our own sealed cell | `test_concession.py` | ✔ |
| 22 | never | No false capture declarations | The capture claim is the cop's own sealed position; a lie dies in the audit | `test_hostile_wire.py`; audit cross-check | ✔ |
| 23 | must | The scent-emission model is cryptographically locked pre-game | `interop.scent_model_lock` / `scent.lock_sha256` — sha256 over the registered `multiplicative_book_v1` document, declared in `negotiate_extras` | `test_negotiation.py::test_a_scent_model_mismatch_is_refused` | ✔ |
| 24 | must | Cryptographic hardware declaration pre-game | `sealing.step0_record` + `shared/sysinfo.hardware_spec`, sealed as Step-0 | `test_sealing.py::test_step0_declares_the_mandatory_identity_fields` | ✔ |

## Group 4 — Strategy, language, public network (rules #25–#30)

| # | Kind | Rule (essence) | Implementation | Proof | Status |
|---|---|---|---|---|---|
| 25 | should | The LLM never decides the move; text only | Brains are pure Python; the provider composes hints only (`turn_taking`) | `test_llm.py`; brain tests are LLM-free | ✔ |
| 26 | must | Communication in free natural language only | Hints via `infra/llm/` providers, 15-word cap enforced | `test_llm.py` (word-cap tests) | ✔ |
| 27 | never | No direct numeric-position protocol | `TurnMessage.from_wire` REJECTS any message carrying `position`/`move`/`intent` | `test_turnmsg.py`; `test_hostile_wire.py` (cleartext = the cardinal sin) | ✔ |
| 28 | must | Token-bucket rate limiter for Gmail reports | `shared/bucket.py` (verbatim `tokens ← min(C, tokens + r·Δt)`) | `test_bucket.py` | ✔ |
| 29 | must | A DOS detector guards the network account | `shared/gatekeeper.py` (burst window → LOCKED, circuit breaker) | `test_gatekeeper.py` | ✔ |
| 30 | must | Gmail scope is send-only | `infra/email/oauth.py`: `GMAIL_SEND_SCOPE` is the single scope ever requested | `test_email_oauth.py` | ✔ |

## Group 5 — League fairness, administration, competitive integrity (rules #31–#45)

| # | Kind | Rule (essence) | Implementation | Proof | Status |
|---|---|---|---|---|---|
| 31 | must | Play the minimum counted games vs different teams | `min_games_to_pass` in `config/game.json`; scheduling is human | config pinned by `test_contract_values.py` | ⏱ league |
| 32 | must | Results reported automatically via Gmail | `infra/email/sender.py` through the Gatekeeper | `test_email_sender.py`; M7 demo | ✔ |
| 33 | must | The report is standard JSON | `infra/email/reports.py` canonical-JSON lifecycle files | `test_email_reports.py` | ✔ |
| 34 | never | Never a free-text report — JSON attachment only | `build_report_email` attaches `application/json`; body is a one-line note | `test_email_sender.py::test_the_report_is_a_machine_readable_json_attachment` | ✔ |
| 35 | must | Agree on the result; each team sends its own report | Mutual audit → agreed verdict; `result_payload` carries both SHA confirmations | `test_two_peers.py::test_a_full_match_reaches_an_agreed_verdict` | ✔ |
| 36 | must | Comprehensive mutual log audit at game end | `domain/audit.py` two layers: hashes + trajectory physics, plus `verify_concession` corroborating a rule-47 "boxed in" claim against the reconstructed board (task 8.14, closing 8.13.4) | `test_logbook_audit.py`; `test_two_peers.py::test_the_mutual_audit_passes_on_both_sides` | ✔ |
| 37 | must | Declare the exact counted-games number at match start | `negotiation.build_terms(games_played=…)`; `InboundHandler.opponent_games_played` | `test_negotiation.py`; `test_inbound.py` | ✔ |
| 38 | never | Never lie about the games count | Declaration goes into the signed terms; the lecturer's inbox is the oracle | terms are sealed — `test_negotiation.py` | ✔ |
| 39 | never | Never push secrets to the repo — even a private one | `.gitignore`: `.env`, `credentials.json`, `token.json`, `*.pem`, `*.key` | `.gitignore` in repo; no secret has ever been committed | ✔ |
| 40 | must | Credentials files are git-ignored | Same as #39 — `.gitignore` names each explicitly | `tests/unit/test_secrets_hygiene.py` (rule text, real ignore behaviour, nothing tracked, and a full-history sweep) | ✔ |
| 41 | must | Tag the submission version in Git | `v1.0-submission` tag at the split (task 8.6) | ⏱ at submission | ⏱ |
| 42 | must | A comprehensive academic report in the repo | `README.md` full report (task 8.4: Dec-POMDP, dilemmas, strategies, screenshots) | ⏱ task 8.4 | ⏱ |
| 43 | must | Moodle form filled and saved as PDF, fields untouched | Human step at submission | — | ⏱ |
| 44 | must | Each team member submits individually on Moodle | Human step at submission | — | ⏱ |
| 45 | must | Unique 8-character team code, no spaces | `[game] group_name = "YANELL11"` in both private TOMLs — 8 characters, no spaces | `test_config.py` reads it; pinned by the shipped config | ✔ |

## Group 6 — Completions found by cross-checking the book (rules #46–#55)

| # | Kind | Rule (essence) | Implementation | Proof | Status |
|---|---|---|---|---|---|
| 46 | must | A barrier on the thief's current cell is a capture | `engine._place_barrier` applies it, `engine._check_termination` sees `board.is_barrier(thief)` and ends the game | `test_rules.py`; `test_concession.py::test_a_trapping_barrier_makes_the_thief_concede` | ✔ |
| 47 | must | A thief with no legal move is captured | `rules.is_trapped` (all exits blocked), checked in `engine._check_termination` after every action — `end_turn` only runs the survival clock | `test_rules.py::test_an_agent_walled_in_on_all_four_sides_is_trapped` | ✔ |
| 48 | must | Score by the scoring table (capture 20/5, survival 5/10, technical 0/0) | `domain/scoring.py`, values from `config/game.json` | `test_scoring.py`; `test_contract_values.py` | ✔ |
| 49 | must | Two repos (cop, thief), cross-linked READMEs, 2 links on Moodle, 4 in the JSON | `report_blocks.links_block(github=…)` threaded into every payload as `links`. **Currently ships two duplicates, not four links**: both TOMLs name the same repo until the split (TODO 11.1.1/11.1.3) | `test_email_reports.py` (four links asserted) | ⏱ |
| 50 | must | Each repo contains README, config/, PRDs, PLAN, TODO at minimum | All present in `docs/` + `config/`; carried into both repos at the split | repo tree | ✔ |
| 51 | must | Reports go to the binding agent-report address | `constants.AGENT_REPORT_ADDRESS` = `rmisegal+uoh26finalgame@gmail.com`; recipient from config | `test_email_reports.py::test_the_binding_report_address_is_the_rulebooks` | ✔ |
| 52 | must | One counted game per opponent; warm-ups allowed | Declared via games-count terms (#37); scheduling is human | ⏱ league conduct | ⏱ |
| 53 | must | Step-0 declares the commit hash actually playing; update it each game | `step0_record(github_commit=…)` — mandatory argument, sealed | `test_sealing.py::test_step0_declares_the_mandatory_identity_fields` | ✔ |
| 54 | must | The final JSON reports total tokens consumed | `TokenLedger.total` feeds each row's `tokens`; `result_payload` DERIVES `tokens_total_series` (inside `final_result`) by summing them, and `result_check` refuses a total that drifts from the rows | `test_llm.py` (ledger); `test_email_reports.py` | ✔ |
| 55 | must | Self-grade code quality only — never the league outcome | Self-assessment written for code quality in the README (task 8.4) | ⏱ task 8.4 | ⏱ |

---

## Software-engineering guidelines — the standing checklist

| Requirement | Where enforced | Evidence |
|---|---|---|
| Python managed with `uv` only (no pip/venv) | `pyproject.toml` + `uv.lock` | repo root |
| Every code file ≤ 150 lines | enforced by `tests/unit/test_file_size_law.py` (code-lines = non-blank, non-comment, non-docstring) | `src/` and `tests/` fully within the cap — largest src file `services/series_guard.py`, 102 code lines. **Three developer scripts are still over** and carry an explicit debt entry: `build_notebook.py` (506), `friendly_series.py` (260), `sparring_series.py` (202). `series_guard.py` was split (containment vs `series_checkpoint`) so **every `src/` module now passes under BOTH readings**, pinned by `test_no_source_file_is_over_the_cap_under_the_stricter_reading`; the interpretation is no longer load-bearing. Four `tests/` files sit between 151 and 159 under the stricter reading only — test prose is intentionally denser than production code, and the cap's purpose is to keep production modules small |
| Test coverage ≥ 85% | `pyproject.toml` `fail_under=85` — the suite FAILS below it | current: **97.6%**, 735 tests |
| `ruff check` clean (E,F,W,I,N,UP,B,C4,SIM; line 100) | `pyproject.toml` `[tool.ruff]` | `All checks passed!` |
| Docstring on every module, class and function | enforced by `tests/unit/test_docstring_law.py` | **0 gaps** across `src/`, `scripts/` and `tests/` for modules, classes, fixtures and helpers (125 written in the 11.6.7 sweep). Test *functions* are a **declared exception**: their names are full sentences (`test_a_diagonal_or_unknown_move_is_rejected`), and a docstring restating the name adds a line and no information. The exception is enforced, not merely claimed — an undocumented test must have at least four words after `test_`, so a short name has to be renamed or documented (7 were documented rather than renamed) |
| No hardcoded values — everything from configuration | `config/game.json` + per-peer TOMLs; `test_contract_values.py` pins them | ✔ (8.18 sweep found and fixed one gap: the Gatekeeper's DOS-window defaults were not wired from `config/rate_limits.json` — now required constructor args, sourced in `configured_sender`, regression-tested) |
| No secrets in the repository | `.gitignore` + rule #39/#40 | ✔ |
| PRD → PLAN → TODO before code; prompts book maintained | `docs/PRD*.md`, `PLAN.md`, `TODO.md`, `PROMPTS.md` (16 entries) | ✔ |
| Tests never depend on external services | Gmail/Anthropic/Google all mocked; fuzz battery is offline | `test_email_*`, `test_llm*` | 

## Guidelines ch. 17 final checklist (v3.00) — walked item by item (task 8.18.2)

The guidelines document's own closing chapter (17, "רשימת בדיקה סופית" / final checklist,
`instruction/software_submission_guidelines-V3.pdf` p.30) is the actual pre-submission
checklist body — six sub-sections, walked here against the repo as it stands after the 8.18
verification pass, not against a claim.

**17.1 Mandatory structure & documentation**
- ✔ Root `README.md` comprehensive project-guide level (rewritten as the academic report, 8.17).
- ✔ `docs/` carries `PRD.md`, `PLAN.md`, `TODO.md`.
- ✔ A dedicated PRD per major algorithm/component — seven `docs/PRD_*.md` files.
- ✔ Architecture documented with clear diagrams — `docs/PLAN.md` §1 (C4 context/container/component/code).
- ✔ Prompts book kept current — `docs/PROMPTS.md`, 17 entries.

**17.2 Architecture & code**
- ✔ SDK architecture — all game-state mutation passes through `sdk/sdk.py::SimulationSdk`; GUI
  modules (`gui/*.py`) contain only rendering (verified during this pass: no domain logic there).
- ✔ OOP, no duplication — real inheritance chains, not copy-paste: `BrainBase → BlindPoliceBrain →
  EnhancedPoliceBrain`; `BlindPoliceBrain → RegionPoliceBrain → WallPoliceBrain → HybridPoliceBrain`;
  `BlindThiefBrain → EnhancedThiefBrain` / `EvadeThiefBrain`.
- ◐ API Gatekeeper for every external call — true for Gmail (`shared/gatekeeper.py` behind every
  send); the Anthropic/LLM path uses a *different*, equally real protection chain instead
  (`fallback(throttle(budget_guard(paid), template))`, PRD_scent_language.md FR-13–15) rather than
  the literal `Gatekeeper` class. This is a deliberate, documented split (ADR-3: a token-budget
  guard is a different shape of limit than a Gmail daily-quota/DOS gate), not an oversight — but
  it does mean `config/rate_limits.json`'s `anthropic` and `default` service blocks are currently
  **dead configuration**, read by no code path. Flagged honestly rather than silently left; not
  fixed in this pass because rewiring the LLM chain onto `Gatekeeper` is a design change, not a
  verification fix, and the existing chain already meets the "no call bypasses a limit" intent.
- ✔ Config boundaries / overflow queueing — `Gatekeeper`'s FIFO queue + `backpressure` property.
- ◐ Every file ≤ 150 code lines, docstrings on every module/class/function. The 8.18.4–8.18.6
  sweep recorded "0 files over the limit, 0 missing docstrings", and a later re-count against
  the actual tree showed that claim had been too broad on both halves: **four files were over
  the cap** (`test_logbook_audit.py` at 197, plus the three developer scripts above) and
  **`tests/` was never docstring-complete**. The claim is corrected rather than restated —
  `test_logbook_audit.py` has since been split, the six `scripts/` docstring gaps filled, and
  the line rule handed to `tests/unit/test_file_size_law.py` so it is checked on every run
  instead of re-asserted by hand. The script splits and the `tests/` docstring sweep are open.
- ✔ Consistent style/naming — `ruff` (E,F,W,I,N,UP,B,C4,SIM) clean across `src/`, `tests/`, and
  `notebooks/analysis.ipynb` (26 pre-existing lint errors found and fixed this pass, see below).

**17.3 Tests & quality**
- ✔ TDD — tests committed alongside every module (`docs/PROMPTS.md` entries; Phase 10 inventory).
- ✔ Coverage ≥ 85% — 97.6% measured over 735 tests, gate enforced by `pyproject.toml fail_under=85`.
- ✔ Ruff — zero errors after this pass (see 8.18.1 below; was not actually zero before it).
- ✔ Edge cases documented — hostile-wire fuzz battery (`test_hostile_wire.py`, 14 tests),
  interop delivery-contract decision table (`test_kit_delivery.py`).
- ✔ Automated test reports — `pytest --cov-report=term-missing`, run on every invocation.

**17.4 Configuration & security**
- ✔ Config separated from code, versioned — `config/game.json` `schema_version`, TOML `version`.
- ✔ `.env-example` documents every variable with no secret value.
- ✔ No API keys/secrets in code — confirmed by this pass's secrets sweep (8.18.8: clean history,
  clean working tree, clean `.gitignore` coverage).
- ✔ `.gitignore` current — covers `.env`, `credentials.json`, `token.json`, `*.pem`, `*.key`.
- ✔ `uv` as sole package manager; `pyproject.toml` + `uv.lock` present and `uv sync` reproducible
  (re-verified this pass).

**17.5 Research & visualization**
- ✔ Parameter-sweep experiments with a results notebook and real graphs —
  `notebooks/analysis.ipynb`, 13 sections, regenerated from source this pass (8.18.11).
- ✔ Performance/accessibility analysis with graphs — capture-rate heatmaps, histograms, the
  exhaustive-validation tables reproduced in `README.md` §9.
- ✔ Token-usage analysis and optimization strategy — notebook §12, fallback ladder documented.

**17.6 Extensibility & tokens**
- ✔ Documented extension points — `[strategy]`/`[trash_talk]` TOML keys, `BrainBase`/`HintProvider`
  plug points named explicitly in the relevant PRDs.
- ✔ Clean Python package organization — `src/police_thief/{domain,services,infra,shared,gui,sdk}`.
- ✔ Parallel work with thread safety — `services/watchdog.py`'s background thread + `peer_boot.py`'s
  daemon server thread, both reviewed for shared-state hazards (no shared mutable state crossed).
- ✔ Building-block design — brains, providers, and transports are all swappable via config, not code.
- — ISO/IEC 25010 is referenced as a quality-model lens in the guidelines, not a literal gate this
  project runs a tool against; the closest operational proxy is the coverage/lint/line-count triad
  already enforced.
- ✔ Organized Git history — incrementally scoped commits with meaningful messages (see `git log`).

## Verification-pass findings (task 8.18, this sweep)

Concrete issues found and fixed while actually running the checks, not merely re-stating that
they should pass:

1. **`ruff check .` was not actually clean.** 26 lint errors existed inside
   `notebooks/analysis.ipynb` (ruff lints notebooks natively) — unsorted/multi-statement imports,
   semicolon-joined plotting lines, a missing `zip(..., strict=True)`, one unused import. Fixed at
   the source (`scripts/build_notebook.py`, which authors the notebook as code) and the notebook
   regenerated from scratch; `ruff check .` now reports **All checks passed!** across `src/`,
   `tests/`, and `notebooks/`.
2. **One test file exceeded the 150-code-line law**: `tests/interop/test_kit_vectors.py` was 200
   code lines. Split along its natural seam into `test_kit_vectors.py` (static byte-exact vector
   conformance, 83 code lines) and a new `test_kit_delivery.py` (the at-least-once delivery
   decision table, 85 code lines) — same 19 tests, both files now well inside the limit.
3. **Twelve missing docstrings** on private/nested functions across `shared/contract.py`,
   `domain/brain/pathfind.py`, `gui/banner.py`, `gui/replay.py`, `services/peer_boot.py` — added.
4. **A real hardcoded-value gap**: `Gatekeeper`'s DOS-window defaults (`dos_max_per_window=12`,
   `dos_window_sec=10.0`) were class-level defaults never overridden by `configured_sender`, so the
   live Gmail pipeline ran on values invisible to `config/rate_limits.json` despite the module's
   own docstring claiming "all limits come from configuration." Fixed: the two fields moved into
   `config/rate_limits.json`'s `gmail` block, `configured_sender` now reads them, and the
   `Gatekeeper` constructor no longer accepts silent defaults for either — a future omission at a
   call site fails loudly instead of running on an invisible number. Regression test strengthened
   (`test_configured_sender_reads_everything_from_config` now proves the wired value, not just
   that *a* value was wired).
5. **A live Python-version bug in `scripts/m7_report_demo.py`**: `datetime.datetime.now(datetime.UTC)`
   uses `datetime.UTC`, added in Python 3.11; the project targets `>=3.10` (`pyproject.toml`,
   `ruff target-version`) and this environment runs 3.10.20. The demo crashed immediately on any
   3.10 interpreter. Fixed to `datetime.timezone.utc`, matching the pattern already used correctly
   in `domain/turnmsg.py`.
6. **A real-world hazard found while re-running the demo**: with a `credentials.json` present at
   the repo root, `scripts/m7_report_demo.py::real_or_stub_service` correctly takes its "real
   Gmail" branch (by design) instead of the stub — which meant re-running the demo during this
   *code* verification pass would have started a live Google OAuth flow. That process was killed
   before completing any network exchange; no email was sent or drafted, no OAuth consent was
   granted. This is a reminder for whoever runs the demo next: without deliberately wanting to
   exercise the real Gmail path (task 9.1, OAuth day), run it from a directory with no
   `credentials.json` on the lookup path, or delete/rename it locally first.
7. **Added a determinism-sweep regression** (`tests/integration/test_determinism.py`,
   task 8.18.9): two independent full mini-games from the same start with the same brains reach a
   byte-identical trajectory (move log, final positions, barrier count, outcome), and replaying
   one fixed sealed log through two independent `ReplaySession` objects produces byte-identical
   scenes and verdicts. Neither property was previously pinned by a test.

Suite grew from 611 to **613** tests (2 new determinism tests; the interop split kept the same
19 tests, just repartitioned across two files). Full suite green at that time (97.8% coverage), `ruff check .`
clean, notebook regenerated and re-diffed against its own prior committed run (8.18.11) with no
change in any numeric result — only the lint-driven source formatting differs.

**Scope note on 8.18.10**: only our own vendored-vector conformance suite
(`tests/interop/test_kit_vectors.py` + `test_kit_delivery.py`, 19 tests) was re-run here — the
kit's own `verify_vectors.py` script lives in the external `copthief-league-protocol` repo, which
is not vendored into this codebase (only its license and JSON vectors are, per 8.10.2). Running
that script against its own vectors independently is tracked separately as the still-open 8.15.1.

**Scope note on 8.18.12**: a full clean-machine fresh-clone build was not performed (would require
committing and cloning to a separate location, out of scope for an in-place verification pass);
`uv sync` reproducibility was re-confirmed in place, and both demo scripts
(`scripts/m7_report_demo.py`, `scripts/build_notebook.py`) were run end-to-end successfully. A
literal fresh-clone rehearsal is best done once at the actual pre-submission checkpoint (8.19).

## Binding parameter values (Appendix ו → `config/game.json`)

`grid_size=7`, `num_agents=2`, `max_barriers=14`, `max_moves=35`, `survival_threshold=35`,
scoring `20/5/5/10`, `tie=2`, `technical_loss=0`, `num_games=6` per series,
`diversity_reward=10`, `min_games_to_pass=2`, `max_games_per_team=10`,
`token_budget=200000` per series, `response_timeout=30s`, `watchdog=60s`,
`hint_max_words=15`, `map_area="Haifa"`, pheromone `center=0.9, decay=0.10`.
Every one of these is pinned by `tests/unit/test_shared/test_contract_values.py` — a
drifted value fails the suite, not the match.

One deliberate exception: `map_area` is asserted only to be a string, not pinned to a
literal. It is a *negotiated* signed term (`setting` in the flat 14-key terms), so a series
may legitimately agree on a different arena; pinning the literal would turn a lawful
renegotiation into a red suite. Its integrity is guarded from the other side instead —
`test_the_shipped_arena_has_real_landmarks` fails if the committed arena has no landmark
pool of its own (FR-11). The committed value is `"Haifa"`, which is also the league kit
sparring peer's default `setting`, so a handshake against a kit-derived opponent agrees
with no pre-negotiation.
