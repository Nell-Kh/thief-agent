# Adversarial Review — police-thief-p2p

**Reviewer stance:** maximally hostile. Every claim below was verified against the source,
the git history, a full test run, and the two PDFs — not against `docs/COMPLIANCE.md`.

**Verified environment:** 699 tests pass, 97.8 % coverage, `ruff check .` clean, Python 3.10.
Those three things are real. Almost nothing else that faces *outward* is.

**Sources of authority used, in order:**
1. `instruction/police_thief_p2p.pdf` — Appendix ו (binding parameter table + Mandatory Rules
   1–5), Appendix ה (rules #1–#55), Appendix ג (submission), Appendix ב (config), ch. 3/5/9.
2. `instruction/software_submission_guidelines-V3.pdf` v3.00.
3. The `copthief-league-protocol` kit — **not** an authority. See §H0.

---

## Verdict in one paragraph

The engineering discipline inside this repo is genuinely above student average: real ADRs, a
trajectory audit the reference implementation doesn't have, hostile-wire fuzzing, atomic
checkpointing, a containment alarm that accuses *your own* driver first. None of that is being
graded right now, because the project fails the submission gate on six independent counts before
a grader reads a line of code, and it carries at least eight ways to score zero *jointly with an
innocent opponent* the moment it meets one. This is a system that has been polished exhaustively
against itself and has never once been tested against reality — every artifact in `results/` is
self-play, and `agreed_between` still reads `["YANELL11", "OPPONENT-TBD"]`.

---

## BLOCKERS — these cost the grade regardless of code quality

### B1. One repository. The book demands two.
Rule #49 and the Appendix ג checklist require **two separate GitHub repos** (cop, thief), each
README cross-linking the other, two links on Moodle, four links in the result JSON.

- `git remote -v` → a single `Nell-Kh/police-thief-p2p`.
- `config/police/game.toml:12` and `config/thief/game.toml:12` both declare
  `repos = { cop = ".../police-thief-p2p", thief = ".../police-thief-p2p" }` — **the same URL
  twice**. That value is not cosmetic: it flows into `group_block()` → the signed declaration →
  the "four links" block. Your mandatory report will ship two links duplicated, not four.
- `README.md` §11 is honest about it: *"Police-agent repository: `TBD — task 8.19`"*.

Knowing about a blocker is not the same as not having one. **Fix before anything else.**

### B2. No submission tag.
Rule #41 + Appendix ג: an *annotated* tag `v1.0-submission`, pushed. `git tag` returns nothing.
`docs/COMPLIANCE.md` marks this ⏱ "at submission" — fine, but it is now unmarked and undone.

### B3. Zero games against a real opponent.
Rule #31 sets `min_games_to_pass = 2` counted games against *different* teams; without them, no
passing grade at all. Every artifact on disk is you playing yourself:

```
results/result_self-play-opponent-vs-team-tbd.json
results/sparring_series/…-sparring-local-vs-team-tbd_g01..g06.json
```

The declaration inside them still says `group_name: "TEAM-TBD"`, `members: ["id-TBD"]`,
`repos: https://github.com/TBD/police-agent`. Six sub-games of sparring against your own
process is a unit test, not a league game. **This is the single highest-value thing you can do
today: play one real series against one real team.**

### B4. Every report you send is disarmed.
`config/police/game.toml` and `config/thief/game.toml`:

```toml
[email]
recipient = "yanalserhan3@gmail.com"
mode = "send"
```

Rule #51 and the Appendix ו variables table bind reports to
`rmisegal+uoh26finalgame@gmail.com`. Your own `report_blocks._is_armed()` correctly refuses to
arm a report addressed anywhere else, so today **100 % of games you play score
`counted: false, reason: "counted-blocked"`** — i.e. nothing. The fail-safe is well designed;
it is currently the only thing standing between you and a false `counted` claim, and it is
firing on every single run.

### B5. The mandatory per-game artifacts are git-ignored.
Appendix ו, Mandatory Rules #4: *"חובה לצרף את קובץ התצורה של כל משחק למאגר ה-GitHub"* — every
game's config file **must** be committed. Rule #50 extends this to the lifecycle set.

```
.gitignore:24  logs/*.json
.gitignore:34  results/*.json
.gitignore:35  results/sparring_series/
```

`git ls-files results/ logs/` returns exactly one entry: `results/.gitkeep`. Every
`declaration_*.json`, `config_*_gNN.json`, `log_*_gNN.json` and `result_*.json` you will ever
produce is excluded by construction. The grader cannot reproduce a single match.

Fix: ignore only scratch (`results/**/*.tmp`, `rows_checkpoint.json`, `*.superseded-*`) and
commit the four lifecycle files per counted game.

### B6. The working tree is filthy.
`git status --short` shows 30+ modified tracked files, including `README.md`,
`docs/COMPLIANCE.md`, and **every file in `config/`**. Rule #53 requires the Step-0 declaration
to name the exact commit hash that played. With uncommitted config changes, the hash you seal
is a hash of code that is not what ran — a *false declaration* in a cryptographically sealed
record, which is precisely the thing rule #38 disqualifies for. Commit before you play.

---

## HIGH — protocol landmines. Each one zeroes **you and an innocent opponent**.

### H0. The framing problem: you took the kit as scripture.
The forum post is right that two lawful implementations can each conclude the other cheated.
Your codebase resolved that risk by adopting the conventions of *two other student teams*
(`copthief-league-protocol`) over the printed book, and the docstrings say so out loud —
`shared/interop.py` cites "kit SPEC §6", `domain/audit.py` cites "kit SPEC §3",
`negotiation.py` cites "the kit's promoted truth tables".

The kit is not an authority. The book is. Dr. Segal's reference implementation
(`rmisegal/Game-P2P-Cop-Chase`, named in the Appendix ו variables table) is. You have made a
**bet** that the league converges on the kit; that bet is nowhere stated as a bet, and there is
no book-literal fallback behind a config flag. If the bet is wrong, H1–H4 all fire at once.

Minimum fix: state the bet explicitly in `README.md` §8 as a documented contradiction choice
under the book's academic-freedom clause (which *requires* you to name the contradiction, your
choice, and your reason), and add a `[interop] profile = "kit" | "book"` switch.

### H1. Your commit hash is not the book's commit hash.
Book, ch. 5.3.1 (printed formula and printed code):

```python
payload = json.dumps({"state":…, "move":…, "intent":…, "nonce": nonce}, sort_keys=True, …)
h_commit = sha256(payload)          # nonce INSIDE the JSON
```

`domain/crypto.py:41`:

```python
material = f"{canonical_json(payload)}|{nonce}"   # nonce APPENDED outside
```

Against an opponent who implemented the printed formula, **every single step fails the audit**,
in both directions. Rule #19 is the iron law: any mismatch is proven tampering, score 0. Your
own docstring anticipates the objection ("the book's inline example hashes the nonce inside the
JSON instead") and waves it away with the front-matter illustrative-code rule. That defence is
arguable for *you*; it is worth nothing when the opponent's auditor says TAMPERED.

### H2. You put a non-book field in the signed terms.
`config/game.json:52` carries `"pheromone_min_center_intensity": 0.5`. It is not in Appendix ב's
config listing, and the book states the field names are *"קבועים ומחייבים"* (fixed and binding).

Worse, `interop.terms_from_contract()` puts it in the **14-key signed terms**, and
`negotiation.validate_terms()` refuses on `theirs["terms"] != our_terms` — a whole-dict compare.
A book-conformant opponent has no such key, `shared/contract.py:_pheromones` defaults theirs to
`0.5` only *on your side*, so their terms object is 13 keys and yours is 14 → **handshake
refused, series over**. Same class of problem for `map_area: "Haifa"` (signed as `setting`;
Appendix ו says a negotiable parameter must default to the printed example, `"New York"`, absent
explicit agreement) and for the extra top-level `"version"` key.

### H3. Your scent formula has a clamp the book does not.
Book, ch. 4.3: `τ(t+1) = max(0, (1−ρ)·τ(t) + Δτ)`. One clamp, at zero.
`domain/scent.py:advance()` adds a second: `value = min(ceiling, value)`.

This is not a rounding-order nicety — it bites on the very first re-emission:
`0.9·0.9 + 0.9 = 1.71 → 0.9`. Unclamped, that cell converges to 9.0. Your scent grid **crosses
the wire** (`TurnMessage.smell_grid`), so a book-literal opponent reading it sees numbers that
cannot arise from the model you both locked.

And the safety net doesn't catch it: `negotiation._check_models()` refuses *only when both sides
declare a family*. An unmodified reference peer declares nothing → no refusal → you play six
sub-games on divergent physics and find out at the audit. The comment calls refusing silence "a
self-inflicted forfeit"; the alternative is a silent one.

### H4. The settlement hash has two independent ways to fork.
`mutual_agreement.sha256` is the join key the league uses; different hashes zero both teams
under rule #35. Two of your choices are unforced:

1. **Spaced separators.** `consensus.serialize_spaced()` uses `(", ", ": ")` while every other
   hash in the codebase is compact. Justified as "the release's second canonical form" — a
   convention that exists only in the kit.
2. **The tie award is added, not substituted.** `consensus.series_aggregate()` does
   `totals = {g: total + tie_score …}` on a series tie, and `total_score` sits **inside the
   consensus scope**. Appendix ו table 17 says the tie score is *"ניקוד לכל צד כאשר הניקוד
   המצטבר … מסתיים בתיקו"* — read plainly, that is the score *for* a tie, not a bonus *on top
   of* it. An opponent who substitutes gets a different `total_score`, hence a different scope
   hash, hence rule #35, hence both of you get zero.

This is a genuine book ambiguity, which means the academic-freedom clause applies — but only if
you **declare it**. Right now it is a silent choice buried in a helper.

### H5. `mutual_agreement.confirmed` is a lie by construction.
`infra/email/reports.py:128` hardcodes `"confirmed": True`. Grep confirms nothing anywhere ever
sets it `False`. Your report asserts the opponent agreed even when no opponent existed — look at
`results/result_self-play-opponent-vs-team-tbd.json`, which cheerfully claims mutual agreement
with a process you spawned. Rule #35 makes result agreement a *precondition*; #38 disqualifies
false declarations. Wire this to the actual audit outcome or delete the field.

### H6. Nothing in this project is actually signed.
Book ch. 5.5: the Step-0 spec is *"נחתם קריפטוגרפית באמצעות מפתח המסופק מראש"* — signed with a
pre-supplied **key**.

- `interop.sign_terms(terms, nonce) = sha256(canonical(terms) + "|" + nonce)`, and the greeting
  ships `terms`, `nonce` **and** `signature`. Anyone can compute it. It authenticates nothing.
  `validate_terms`' `"terms signature does not verify"` branch is unreachable for any
  well-formed greeting — it is dead code that reads like security.
- `report_blocks.group_block()`: `block["signature"] = "sha256:" + sha256_of(block)`. Same.

These are integrity checksums mislabelled as signatures, and `COMPLIANCE.md` #24 repeats the
label. Either implement HMAC/Ed25519 over a pre-shared key, or rename them `*_sha256` and state
in the report that keyed signing was out of scope. Do not ship the word "signature".

### H7. Turn order is unilateral and unnegotiated.
`domain/engine.py:8`: *"cop first, then thief — a documented choice (the rulebook does not fix
one)"*. Correct that the book doesn't fix it. But it is **not** among the 14 signed terms and
**not** in `negotiate_extras()`, so two peers with opposite orders shake hands successfully and
then disagree about the board. Put it in the declarations, or prove in the report that the
turn-token protocol makes it unobservable.

### H8. `min(threshold, ceiling)` silently redefines survival.
`domain/engine.py:110`: `if state.step >= min(threshold, ceiling)`. Today both are 35, so it is
invisible. Both are **"minimum"-status** parameters that may be independently negotiated
*upward*. Raise `survival_threshold` to 50 and you declare survival at 35 while a book-literal
opponent declares it at 50 — a hash-clean log with a divergent winner, i.e. rule #35 again. Use
`survival_threshold` for survival and let `max_moves` end the game on its own terms.

---

## MEDIUM

### M1. Your hardware declaration is zeros.
`shared/sysinfo.py` reads `/proc/cpuinfo` and `os.sysconf("SC_PHYS_PAGES")` — **Linux only**.
Your own declaration says `"os": "Windows 10"`, and accordingly ships
`"cpu_mhz": 0.0, "ram_gb": 0.0`. Rule #24's sanction is loss of the computational-fairness
bonus, and the book's normalization is explicitly a *bonus for doing more with less* — you are
declaring a machine with no memory and no clock. Use `platform`/`psutil`/WMI, or at minimum
`os.cpu_count()` plus `ctypes.windll.kernel32.GlobalMemoryStatusEx`.

### M2. Live secrets at rest in a OneDrive folder.
`.env` currently holds a live `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GMAIL_APP_PASSWORD` and
`MCP_AUTH_TOKEN`; `token.json` holds a live OAuth access token; `credentials.json` holds the
Google client config.

Credit where due: **git history is clean** — I swept every tree in every commit on every ref and
found nothing but `.env-example`. `.gitignore` covers all of it. Rules #39/#40 hold.

But the repo lives under `C:\Users\yanal\OneDrive\Desktop\` — those four secrets are synced to
Microsoft's cloud, and any process or agent granted folder access reads them in plaintext (I
just did). **Rotate all four now**, and move the repo out of OneDrive or add the folder to
OneDrive's exclusion list.

### M3. `docs/COMPLIANCE.md` misquotes its own codebase.
A rules-to-code traceability matrix is only worth the accuracy of its cells. Spot-checking six:

| Claim | Reality |
|---|---|
| #23 → `negotiation.scent_lock_for` | **no such symbol anywhere** (it's `interop.scent_model_lock` / `scent.lock_sha256`) |
| #46 → `_apply_barrier` ends the thief's game | `_apply_barrier` is in `services/turn_receiving.py`; the engine's is `_place_barrier` |
| #47 → `is_trapped` checked in `engine.end_turn` | it's checked in `_check_termination`; `end_turn` only does the survival clock |
| #49 → `reports.result_payload(repositories=…)` | no such parameter — it's `links` |
| #54 → `result_payload(tokens_total=…)` | no such parameter — derived from rows |
| "689 tests" / "613 tests" / ".gitignore lines 2–5" | 699 / 699 / lines 2–6 |

A grader who spot-checks three cells finds three wrong and stops trusting the document — which
would be a shame, because §"Verification-pass findings" is the most impressive writing in the
repo. Regenerate the symbol references mechanically, or drop them.

### M4. The 150-line rule is being graded on a reading you wrote yourself.
Guidelines §3.2: *"כל קובץ קוד לא יעלה על 150 שורות קוד (שורות ריקות ושורות הערה לא נספרות)"*.
Blanks and **comments** excluded. `tests/unit/test_file_size_law.py` additionally excludes
**docstrings**, with a reasoned defence in its own docstring — but guidelines p.24 lists
*"קבצים עד 150 שורות קוד, הערות ו-docstrings"*, which reads the other way.

Measured both ways:

| Reading | Files over 150 |
|---|---|
| Guidelines' plain wording (docstrings count) | 4 — incl. **`src/police_thief/services/series_guard.py` at 160** |
| Your test's reading (docstrings excluded) | 3 — all `scripts/` |

The one `src/` file that fails the plain reading is exactly the file your law-test's reading
exempts. That is not fraud, but it is the kind of thing a hostile grader notices. Split
`series_guard.py` (checkpointing ↔ containment is a clean seam) and the three scripts, and the
argument goes away entirely.

### M5. Dead configuration.
`config/rate_limits.json`'s `anthropic` and `default` service blocks are read by no code path —
self-admitted in COMPLIANCE.md §17.2 (ADR-3 routes the LLM through
`fallback(throttle(budget_guard(paid), template))` instead of `Gatekeeper`). Guidelines §7.2
bans hardcoded values; this is the mirror image and equally a smell. Either wire them or delete
them.

### M6. Placeholder identity everywhere it counts.
`agreed_between: ["YANELL11", "OPPONENT-TBD"]`; `results/**` declarations say `TEAM-TBD`,
`members: ["id-TBD"]`, `repos: github.com/TBD/…`; COMPLIANCE #45 still says the 8-char group
code is "to be finalized" though `group_name = "YANELL11"` is already 8 characters. Sweep.

---

## What is actually good (and should be defended in the README)

- 699 tests, 97.8 % coverage against a hard `fail_under=85` gate, `ruff` clean. Real.
- `domain/audit.py` verifies **trajectory physics** on top of hashes — a hash-clean log that
  teleports or walks through a barrier still fails. The reference implementation doesn't do
  this. Say so louder.
- `_disclosed_records()` structural hardening + `test_hostile_wire.py`: a malicious peer
  forfeits instead of crashing you. Correct instinct, correctly scoped.
- `series_guard.containment_alarm()` — a warning that accuses *your own driver first* when every
  sub-game contains. That is unusually mature failure engineering.
- `report_blocks._is_armed()` — fail-safe arming. It is the reason B4 is a misconfiguration and
  not a rule-#38 disqualification.
- `shared/preflight.py` — finding the handshake refusal the night before. Exactly right.
- `TurnMessage.from_wire` rejecting cleartext `position`/`move`/`intent`. Rule #27, enforced at
  the door.

---

## Do these, in this order

1. **Split the repo in two, cross-link the READMEs, fix `repos=` in both TOMLs.** (B1)
2. **Point `[email] recipient` at `rmisegal+uoh26finalgame@gmail.com`.** One line. (B4)
3. **Un-ignore the four lifecycle artifacts; commit them per counted game.** (B5)
4. **Rotate the four secrets in `.env`/`token.json`; move the repo off OneDrive.** (M2)
5. **Commit the working tree, then tag `v1.0-submission -a`.** (B6, B2)
6. **Play one real counted series against one real team.** Everything above is theatre until
   this happens. (B3)
7. **Add `[interop] profile = "kit" | "book"`** covering the seal format, the scent clamp, the
   consensus serialization and the tie-award semantics — and write the bet down in README §8 as
   a declared contradiction choice. (H0–H4)
8. Fix the hardware probe (M1), regenerate COMPLIANCE's symbol references (M3), split
   `series_guard.py` and the three scripts (M4).
9. Wire `mutual_agreement.confirmed` to the real audit outcome, and stop calling unkeyed hashes
   "signatures" (H5, H6).
