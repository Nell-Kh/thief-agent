# `results/` — the per-game lifecycle artifacts

App. F Mandatory Rules #4 requires every game's config file to live in the
repository, and rule #50 wants the whole set, so a grader can replay a match
rather than take our word for it. Chapter 9.3.3 names the four files, all
derived from one `game_id` so files from different games can never mix:

| File | Role |
|---|---|
| `declaration_<game_id>.json` | pre-game: teams, members, repos, hardware, model, token ceiling |
| `config_<game_id>_gNN.json` | the locked terms for one sub-game, with `config_sha256` |
| `log_<game_id>_gNN.json` | one sub-game's sealed commit-reveal records, for the Replay Viewer |
| `result_<game_id>.json` | the final report mailed to the league address |

## What is in here right now is **not** a league game

Every artifact currently committed is a **rehearsal against ourselves**, and each
one says so in its own `league` block:

```json
"league": { "counted": false, "reason": "friendly" }
```

- `result_self-play-opponent-vs-team-tbd.json` — one sub-game, self-play.
- `sparring_series/` — six sub-games against a local sparring peer.

The group identity in them is still placeholder (`team-tbd`, `id-TBD`,
`github.com/TBD/…`) because no real opponent has been played yet. They are
committed as evidence that the pipeline emits the four files in the right shape
and that the audit passes end to end — not as evidence of league play.

Counted games against real opponents (`docs/TODO.md` 11.3) land here alongside
them, and are distinguishable without reading a filename: `league.counted` is
`true` and `reason` is `counted`. Nothing else in the tree makes that claim.

## What is deliberately *not* committed

`.gitignore` excludes scratch only — `*.tmp`, `rows_checkpoint.json` (the
crash-recovery file `services/series_guard.py` writes; evidence for us, never a
document the league reads) and `*.superseded-*` archives of re-run series.
