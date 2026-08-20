# uoh-ay26 — interop audit and first-contact reply

Audit of `police-agent` / `thief-agent` at `d0b26e8` / `45a2cb6` against uoh-ay26's published
spec sheet. Four blockers, all of which zero **both** teams under rules #19/#35 if played
through. Three are small; one is a real design disagreement.

---

## BLOCKER 1 — the consensus preimage is not the same object

This is the serious one. Their digest and our `mutual_agreement.sha256` are computed over
**different objects in a different serialization**, so they can never match, and rule #35
zeroes both teams on a settlement mismatch.

| | uoh-ay26 | us (`infra/email/consensus.py`) |
|---|---|---|
| `game_id` value | bare label, `"G010"` | `"uoh-ay26-vs-yanell11-G010"` |
| `game_uid` | **included** | absent |
| `aggregate` | **excluded** ("exclude final totals, and final winner") | **included** |
| separators | `(",", ":")` compact | `(", ", ": ")` spaced, under `profile = "kit"` |
| row keys | `sub_game_number, result, roles, score, winner_group` | same five ✓ |

Demonstrated on one identical row:

```
THEIRS {"game_id":"G010","game_uid":"…","sub_games":[…]}
       -> dfb38c39b54c066cbc86688b85e2157b3e0650abb15ebfec67275dce53dcde4d
OURS   {"aggregate":{…}, "game_id":"uoh-ay26-vs-yanell11-G010", "sub_games":[…]}
       -> f6d144c6e525cea576885d517a2b70315fa6bb06b4bf8fd13746b488f10654a0
```

Note that flipping `[interop].tie_award` or `[interop].profile = "book"` fixes **only the
separators**. The other three divergences survive both dialects, so this cannot be resolved
from config — it needs either a code path that computes their preimage, or their agreement to
compute ours.

**Their scope is arguably the better one.** Our `aggregate` is *derived* from the rows, so
including it in the preimage adds no information and imports the whole add-vs-substitute
tie-award fork straight into the settlement hash — the fork `interop_profile.py`'s own
docstring admits neither dialect settles. Their scope cuts exactly that, and adds `game_uid`,
which pins the identity our own `identity.py` docstring says an unlabelled derivation cannot.

Recommend conceding this one and implementing their preimage for this series. Whichever way it
goes, **agree it in writing before kickoff and put a worked example with a real SHA in the
message**, so the first time both sides compute it is not after six settled sub-games.

## BLOCKER 2 — `win_claim: {"type": "boxed_in"}` is silently ignored

`services/turn_receiving.py::_apply_win_claim` accepts exactly two types: `survival` (from the
thief, at or past the signed threshold) and `capture`. Their spec says a fully enclosed thief
may send `win_claim: {"type": "boxed_in"}`. That message falls through every branch and returns
without settling — no error, no note, nothing in the log.

The failure is the expensive kind: their thief declares itself boxed in and stops, we never
record a capture, and the two sides carry different results for that sub-game into the audit.
Rule #35 then zeroes both.

The fix is one branch — accept `boxed_in` wherever `capture` is accepted today, keeping the
existing corroboration in `verify_concession` (kit finding F-2) so a claimed box is still
checked against our own barriers rather than believed.

Our own direction is already compatible: our trapped thief sends
`claim_response {"claim": […], "caught": true}` as a real STAY turn at the next step
(`services/concession.py`), and their spec handles `caught=true` as terminal.

## BLOCKER 3 — no top-level `git_commit_hash` in the greeting

They require the negotiation identity to carry a top-level `git_commit_hash` of exactly 40
lowercase hex characters. `domain/negotiation.py::build_terms` sends `step0_commit` and
`identity{group_id, group_name, members, repos}`; the 40-char value also sits inside the sealed
Step-0 record as `github_commit`. The key they name is not on the wire under that name.

Add it beside the signed terms — **never inside `terms`** — so the terms signature every
conformant peer verifies is unchanged. One caveat: `_series_lib.git_head()` returns the literal
string `"uncommitted"` when `git rev-parse` fails, which is not 40 hex and would be refused;
worth failing loudly at launch instead of at their validator.

Step-0 itself is already conformant — `domain/sealing.py::step0_record` emits
`{"step": 0, "type": "system_spec", …}` and it is appended to the record set, which is exactly
what their §"Step-0 compatibility convention" asks for.

## BLOCKER 4 — `series_consensus` is a bolt-on, and nothing is listening

`consensus_sha` and `series_consensus` appear nowhere in `src/`. The only implementation is the
root-level `send_consensus.py`, written for yamanagh, which dials `submit_audit` by hand with a
hardcoded envelope and sends `result["mutual_agreement"]["sha256"]` — i.e. our hash, the one
Blocker 1 says is the wrong one.

Two further problems with the reciprocal direction:

- **Their envelope arrives after all six sub-games**, when `friendly_series.py` has written its
  result and exited and the port is closed. There is no process to receive it. Someone has to
  keep a peer serving through the consensus exchange, or both sides have to agree to exchange
  the SHA out of band.
- If it *did* arrive mid-series, `services/inbound.py::submit_audit` accepts any dict with a
  list `records` and assigns `self.audit = payload` — so a `records: []` consensus envelope
  would **overwrite the real game audit**. Their own rule ("a consensus envelope containing game
  records is malformed") has no mirror on our side.

---

## Compatible already — no action

- Tool names and the argument asymmetry: `mcp_server.py` exposes `negotiate`, `receive_turn`,
  `submit_audit`, `receive_control` with `payload` on `submit_audit` and `message` on the other
  three. Exact match.
- Wire event names and shapes: `barrier_placed`, `capture_claim`,
  `claim_response {"claim": [r, c], "caught": bool}`, `win_claim {"type": …}`.
- `capture_claim` is sent on **every** police turn (`turn_taking.py` line 115 is unconditional
  on role, so it covers STAY and barrier-placement turns).
- Result vocabulary is `capture` / `survival` / `technical_loss`; nothing in the codebase ever
  reports `timeout` as a result.
- No retroactive coordinate-equality capture: `verify_concession` corroborates a claimed cell
  against the revealed trail and our own barriers, and refuses otherwise.
- Wire roles are the strings `police` and `thief`.

## To settle in the message, not on the wire

- **Their `game.json` must equal ours byte-for-value.** We sign the kit's **14** keys including
  `min_center_intensity = 0.5`; a book-conformant peer signs 13 and `validate_terms` compares
  the whole object, so the count alone refuses. `setting` is `"Haifa"`.
- **`[interop].tie_award = "add"`** — the kit does not settle add-vs-substitute, and if their
  preimage wins (Blocker 1) it stops mattering for the hash, but it still forks the reported
  totals.
- **Their `game_uid` derivation.** They ask us to supply one and require it to match on both
  sides, but do not publish how they derive it. Ours is
  `UUID(SHA256(canonical(terms) + "|" + game_id)[:16])`, documented in
  `shared/identity.py::derive_game_ids`. Ask them to confirm the rule, not just the value.
- **Turn order.** We declare `turn_order = "cop_first"` in `negotiate_extras` and refuse a
  stated difference. Their sheet does not mention it.

---

# Draft reply — send this

> **Team yanell11 → uoh-ay26**
>
> **1. Group ID / name** — `yanell11` / `YANELL11`
>
> **2. Members** — Nell Khoury; Yanal Serhan
>
> **3. Repositories**
> Cop: https://github.com/Nell-Kh/police-agent
> Thief: https://github.com/Nell-Kh/thief-agent
>
> **4. Playing commit SHAs**
> Cop: `d0b26e8e23f251e9a6c3400fea9bd6438abbbfbb`
> Thief: `45a2cb6399b9c06602da36987680f3dc000ebde7`
> *(These are today's tips. Four interop items below need code changes before we play; we
> will re-send both 40-character SHAs once they are committed and treat those as binding.)*
>
> **5. MCP endpoints**
> Cop (police): `https://apps-mens-figured-spirituality.trycloudflare.com/mcp`
> Thief: `https://acts-delegation-victorian-incident.trycloudflare.com/mcp`
> *(Cloudflare quick tunnels. These hostnames are regenerated every time `cloudflared`
> restarts, so treat them as valid only for the session we agree; we will re-send if either
> tunnel is restarted before kickoff.)*
>
> **6. Automatic-report sender** — `yanalserhan3@gmail.com`
>
> **7. Counted-game history** — `<PENDING — see note below>`
>
> **8. Series label** — `G010`, as you proposed.
>
> **9. Role schedule** — sub-games 1/3/5: yanell11 **police**, uoh-ay26 **thief**;
> sub-games 2/4/6: yanell11 **thief**, uoh-ay26 **police**. We run the rule-1 split: two
> processes, two ports, two tunnels, one role each.
>
> **10. Shared configuration**
> `config/game.json` file SHA-256: `5885b39764f4548fd90a20fe1946b49cead1e501b6c5ce9e4315de54d284e195`
> (identical in both our repos; file attached)
>
> Canonical signed terms — 14 keys, kit dialect, `sort_keys=True`, `separators=(",", ":")`,
> `ensure_ascii=False`:
>
> ```json
> {"axis_origin_corner":"top-left","axis_start_index":0,"barriers_max":14,"board_size":7,"cop_start":[0,0],"decay_per_step":0.1,"emit_intensity":0.9,"hint_max_words":15,"max_steps":35,"min_center_intensity":0.5,"num_games":6,"setting":"Haifa","smell_grid_size":5,"thief_start":[3,3]}
> ```
>
> Terms SHA-256: `ad9e1bfd724e9debcde523833381cb7982a5d619d693d3738b59e0da61f4d81a`
>
> `game_uid`: `9d720049-dd3d-6ee2-a7db-67f17fb78f2d`
> derived as `UUID(SHA256(canonical(terms) + "|" + game_id)[:16])` with
> `game_id = "uoh-ay26-vs-yanell11-G010"` (the group pair sorted, then the label).
> **Please confirm your derivation rule, not just the value** — if yours differs we need to
> agree one before kickoff.
>
> ---
>
> **Five things we need to settle before we start:**
>
> **(a) The consensus preimage.** Ours currently differs from yours in four ways: we use the
> full `game_id` (`uoh-ay26-vs-yanell11-G010`) where you use the bare label, we omit
> `game_uid`, we include a derived `aggregate` block, and we serialize with spaced separators.
> **We are willing to adopt your preimage exactly as published** — it is the cleaner scope,
> since excluding the aggregate keeps the unsettled add-vs-substitute tie-award question out
> of the settlement hash. Please confirm, and send a worked example: one fabricated six-row
> series, the exact preimage bytes, and the resulting SHA, so we can prove agreement offline
> before we play.
>
> **(b) `win_claim: {"type": "boxed_in"}`.** Our receiver currently accepts `survival` and
> `capture` only. We are adding `boxed_in`. Confirm your thief sends it as the sole terminal
> signal in that case, or whether it is accompanied by a `claim_response` with `caught: true`.
>
> **(c) `git_commit_hash`.** We will add it top-level in the greeting, 40 lowercase hex, beside
> the signed terms (never inside them, so the terms signature is unaffected). Confirm you read
> it there and not inside `identity`.
>
> **(d) The consensus exchange window.** After sub-game 6 our series driver writes its result
> and exits, which closes the port. Do you keep a peer serving to receive the reciprocal
> `series_consensus` envelope, and for how long? We would rather agree a window (say both sides
> stay up 5 minutes past the last audit) than have one side dial a closed port.
>
> **(e) Signed terms count.** We sign 14 keys including `min_center_intensity: 0.5`. If your
> peer signs 13, the terms object comparison refuses outright regardless of every value
> agreeing. Please confirm your key count.
>
> Turn order: we declare `cop_first` and refuse a stated difference — confirm if you differ.
>
> Once (a)–(e) are agreed we will send the final two commit SHAs and the two tunnel URLs, and
> propose a kickoff time.

---

## Open on our side before this reply goes out

**Item 7 is not answerable from this checkout, and it is the one field rule #38 disqualifies
for getting wrong.** What this tree actually holds:

| series | date | `league.counted` | result | prior count declared |
|---|---|---|---|---|
| `nis-yar1-vs-yanell11-counted-1` | 2026-08-17 | `true` | 6–0 yanell11 | `0` |
| `yamanagh-vs-yanell11` | 2026-08-19 | `true` | 6–0 yanell11 | `0` |

There is **no sharNamr series** in `results/`, `logs/` or `docs/`, and no artifact anywhere
ending 3–3. Two anomalies to resolve before declaring anything:

1. **Both counted series declared `counted_games_played: 0`.** If both genuinely counted, the
   08-19 yamanagh declaration under-declared and should have said `1`. uoh-ay26's own failure
   policy has an explicit clause for a counted-history declaration that "appears false", so
   this needs to be right before it crosses the wire.
2. **Both were played on `Darwin 24.6.0 / arm64`** — a Mac, not the Windows machine holding
   this checkout. The sharNamr artifacts and the authoritative ledger are almost certainly on
   that machine. Reconcile there, then fill item 7 in.

**Two smaller confirmations:**

- The sender address was given as `yanalserhan3@gmai.com` (missing the `l`); written above as
  `yanalserhan3@gmail.com`. Correct it if that is wrong.
- `token.json` carries an empty `account` field, so the repo cannot prove which Gmail account
  minted it. Its access token expired 2026-08-17 (the refresh token is non-expiring, so it
  still works). Send one test report and read the `From:` header before declaring the sender
  address to an opponent.

---

## Order of work on our side

1. Implement their consensus preimage (or theirs-vs-ours, per their answer to (a)) behind the
   interop profile, with a test that reproduces the worked example they send.
2. Accept `boxed_in` in `_apply_win_claim`, keeping F-2 corroboration.
3. Add top-level `git_commit_hash` to `build_terms`; refuse to launch when `git_head()` is not
   40 hex.
4. Move `series_consensus` out of `send_consensus.py` into `src/`: reject a consensus envelope
   that carries records, never let it overwrite `self.audit`, and keep the peer serving past
   the final audit for the agreed window.
5. Re-run `uv run pytest` and `ruff check`, commit, and re-send both 40-char SHAs.
6. Only then stage tunnels and run `scripts/preflight.py` against their `game.json`.
