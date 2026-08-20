# yanell11 → uoh-ay26 — first contact

*Paste-ready. Fill item 7 before sending; everything else is verified.*

---

**Team yanell11 → uoh-ay26**

Thanks for the detailed spec sheet — it let us find four incompatibilities before
kickoff instead of at settlement. All four are fixed and pushed; details below.

**1. Group ID / name** — `yanell11` / `YANELL11`

**2. Members** — Nell Khoury; Yanal Serhan

**3. Repositories** — playing branch `yanell11_vs_uoh-ay26` in both (pushed):
- Cop: https://github.com/Nell-Kh/police-agent
- Thief: https://github.com/Nell-Kh/thief-agent

**4. Playing commit SHAs** *(final — both trees clean, both commits pushed)*
- Cop: `91de90a5a7ba3151ca8f02c1b227dde0d0bb367f`
- Thief: `c401c22abc3b5afd34d9eb6a8c87837eda1b926c`

These are what our greeting declares as top-level `git_commit_hash`, and what is
sealed into each Step-0 record as `github_commit`. Note they sit on the branch
above, not on `main`.

**5. MCP endpoints** *(Cloudflare quick tunnels — the hostnames are regenerated on
every `cloudflared` restart, so we will re-send if either restarts before kickoff)*
- Cop: `https://apps-mens-figured-spirituality.trycloudflare.com/mcp`
- Thief: `https://acts-delegation-victorian-incident.trycloudflare.com/mcp`

**6. Automatic-report sender** — `yanalserhan3@gmail.com`

**7. Counted-game history** — **2 counted series played to date**, both won 6–0:

| # | Opponent | Date | Result | Settlement hash (`mutual_agreement.sha256`) |
|---|---|---|---|---|
| 1 | `nis-yar1` | 2026-08-17 | 6–0 yanell11 | `423acb7c63dad4de86f764aad0814d6cf7274bced78286038a2980881cd1e682` |
| 2 | `yamanagh` | 2026-08-19 | 6–0 yanell11 | `35e4d731e92b49a7153a815757ea6bbb9993141772dcfb29e27e2f1daeb68b21` |

Both settled with `mutual_agreement.confirmed: true`. A series against `sharNamr`
on 2026-08-17 ended 3–3; it was uncounted and does not enter this total. We can
share any of these bundles on request.

Counting the proposed series, that would make this our **third** counted game and
our **first** against uoh-ay26 — so `first_meeting_between_groups` is true and we
would pass `--games-played 2`. Please send your own count so neither side has to
infer it.

**8. Series label** — `G010`, as you proposed.

**9. Role schedule** — sub-games 1/3/5: yanell11 **police**, uoh-ay26 **thief**;
sub-games 2/4/6: yanell11 **thief**, uoh-ay26 **police**. We run the rule-1 split:
two processes, two ports, two tunnels, one role each.

**10. Shared configuration**

`config/game.json` file SHA-256 (identical in both our repos; file attached):
`5885b39764f4548fd90a20fe1946b49cead1e501b6c5ce9e4315de54d284e195`

Canonical signed terms — **14 keys**, `sort_keys=True`, `separators=(",", ":")`,
`ensure_ascii=False`:

```json
{"axis_origin_corner":"top-left","axis_start_index":0,"barriers_max":14,"board_size":7,"cop_start":[0,0],"decay_per_step":0.1,"emit_intensity":0.9,"hint_max_words":15,"max_steps":35,"min_center_intensity":0.5,"num_games":6,"setting":"Haifa","smell_grid_size":5,"thief_start":[3,3]}
```

Terms SHA-256: `ad9e1bfd724e9debcde523833381cb7982a5d619d693d3738b59e0da61f4d81a`

`game_uid`: `9d720049-dd3d-6ee2-a7db-67f17fb78f2d`, derived as
`UUID(SHA256(canonical(terms) + "|" + game_id)[:16])` with
`game_id = "uoh-ay26-vs-yanell11-G010"` (the group pair sorted, then the label).
**Please confirm your derivation rule, not just the value** — if yours differs we
need to agree one before kickoff.

---

## What we changed to match you

**Your consensus preimage — adopted.** Ours differed from yours in four ways at
once: we used the full `game_id` where you use the bare label, omitted `game_uid`,
included a derived `aggregate` block, and serialized with spaced separators. We
have implemented yours exactly as published, behind a declared `settlement_scope`
axis that refuses at the handshake on a stated difference. We think yours is the
better scope — excluding the derived aggregate keeps the unsettled
add-vs-substitute tie-award reading out of the one hash rule #35 zeroes both teams
over.

Reproducing your published example verbatim, we now compute:

```
preimage {"game_id":"G010","game_uid":"<shared UUID>","sub_games":[{"result":"survival","roles":{"opponent":"thief","uoh-ay26":"police"},"score":{"opponent":10,"uoh-ay26":5},"sub_game_number":1,"winner_group":"opponent"}]}
SHA-256  1b0b14202a07468112811dc3b5a0613f18473965c77291c0a52a571c9250bea3
```

**`win_claim: {"type": "boxed_in"}` — now accepted.** Our receiver previously took
only `survival` and `capture`; `boxed_in` fell through every branch silently, so
your enclosed thief would have stopped while we recorded no capture at all. Fixed,
with the corroboration we already run against our own barriers left in place.

**`git_commit_hash` — now top-level**, 40 lowercase hex, beside the signed terms so
the terms signature is unchanged. Omitted entirely (never malformed) on an
uncommitted tree.

**`series_consensus` — now told apart from a game disclosure.** It previously
satisfied our `submit_audit` checks and overwrote the real game audit with its
empty record set. It now lands separately, and we refuse an envelope carrying
records, mirroring your own rule.

## Five things to settle before we start

**(a) The `roles` and `score` keys.** Your example uses the literal string
`"opponent"` as a key alongside `"uoh-ay26"`. Ours uses both group ids —
`{"uoh-ay26": ..., "yanell11": ...}`. If you send the literal `"opponent"` our
hashes diverge on every row. Which is it?

**(b) A full worked example.** Please send one fabricated six-row series: the exact
preimage bytes and the resulting SHA. We will match it offline and confirm before
we play. We would rather find a disagreement in a chat message than after six
settled sub-games. In particular we want to see how you spell a row for a sub-game
that ended in a technical loss.

**(c) The consensus exchange window.** After sub-game 6 our series driver writes its
result and exits, closing the port — and with the rule-1 split our consensus SHA
does not exist until the two halves are merged. Do you keep a peer serving to
receive the reciprocal `series_consensus`, and for how long? We propose both sides
stay up 5 minutes past the last audit.

**(d) Signed terms count.** We sign 14 keys including `min_center_intensity: 0.5`.
If your peer signs 13, the terms comparison refuses outright regardless of every
value agreeing. Please confirm your count.

**(e) Turn order.** We declare `cop_first` and refuse a stated difference. Your
sheet does not mention it — confirm if you differ.

We propose the first series be **uncounted (a friendly)** under rule #52, so both
sides can prove the settlement hash agrees before anything is graded. Happy to go
straight to a counted series if you would rather, once (a)–(e) are answered.
