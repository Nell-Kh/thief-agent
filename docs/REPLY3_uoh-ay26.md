# yanell11 → uoh-ay26 — reply 3 (technical-loss row)

*Refresh the two commit SHAs before sending.*

---

**Team yanell11 → uoh-ay26**

Thank you for the six-row example — it did exactly what we hoped and found a real
fork before kickoff rather than after it.

We verified your two commits resolve publicly, and that
`SERIES_CONSENSUS_TIMEOUT_SECONDS = 600.0` is really in them. Confirming your
window and flow: we merge locally after g06 and dial you within 5 minutes; we will
also keep a peer serving to receive yours; and we will post our SHA in writing as
a debugging backup, with the wire exchange authoritative.

## Your example: four rows agree exactly, two do not

We reproduced your preimage byte-for-byte from your own bytes and got your stated
`42d7d258…`, so your serialization and ours agree completely.

Taking your **four non-technical-loss rows alone** — g01, g02, g04, g05 — our
implementation produces a byte-identical preimage, hashing to:

```
14df2290efe2a74c...
```

So `survival` and `capture` rows, `roles`, `score`, `winner_group`, key ordering
and separators are all settled between us. That is the bulk of the format and it
is now proven, not assumed.

**The two `technical_loss` rows diverge, on two fields each.**

| field | uoh-ay26 (g03) | yanell11 (g03) |
|---|---|---|
| `score` | `{"uoh-ay26": 20, "yanell11": 0}` | `{"uoh-ay26": 0, "yanell11": 0}` |
| `winner_group` | `"uoh-ay26"` | `null` |

Our six-row SHA for the same six outcomes is therefore
`d3eff951328452b0ee523c8af0ae8859796e5d3ae8fe19589232d2b6a5ce2cbd`, against your
`42d7d258fd8d1e983c0a9d83a4acec2f574587a3274569cafab763651a2b68ed`.

## Why we read it as 0/0, and the one part of yours we cannot source

We think both readings are defensible in spirit — a forfeit arguably should not
let the failing side deny an innocent opponent the points it would have earned.
But we can only derive one of them from the terms we both signed:

**`scoring.technical_loss` is a single value, not a pair.** The Mandatory
Parameters Table carries one number, `0`. Every other outcome in that table is
role-specific and named in pairs — `capture_cop: 20` / `capture_thief: 5`,
`survival_cop: 5` / `survival_thief: 10`. A lone `technical_loss: 0` reads most
naturally as the score the row carries, not as "0 for one side and something else
for the other."

**In your g03 the beneficiary is the thief, and receives 20.** The signed terms
give a thief `capture_thief: 5` or `survival_thief: 10`. There is no 20 available
to a thief anywhere in the table — `20` is `capture_cop`. So the award in that row
is a flat maximum rather than a value the contract provides for that role, and we
cannot see where to derive it from.

We also keep `winner_group: null` deliberately: our aggregate treats a zeroed row
as a sanction credited to nobody, which preserves the identity
`won_a + won_b + ties + zeroed == num_sub_games`. Naming a winner on a row nobody
scored breaks that count.

## What we propose

**Primary: adopt `score: 0/0` and `winner_group: null` for `technical_loss`.** It
is the reading derivable from the signed terms, and it needs no code change on our
side. If you would rather we adopt yours, we will — but we would want the 20 for a
thief justified from the parameters table first, because whichever we pick we both
have to defend it at the audit.

**Fallback, and we think it is the right answer for this first friendly
regardless:** your own shared failure policy already says that if a tunnel drops
mid-game, both sides should *"agree in writing whether the specification requires a
technical loss or a fresh non-counted replay."* For G010 we propose the second:
**if any sub-game ends in `technical_loss`, we do not settle a forked hash — we
stop, both post our rows, and replay the series.** That way the disagreement above
can never decide a result, and we can settle it properly before anything counted.

## Two things still outstanding

**Your `config/game.json` did not arrive** — the message referenced an attachment
but none came through. Please re-send it; we want to run our pre-match checker
against the file itself rather than against the fields quoted in a message.

**Our refreshed commit SHAs** (the turn-order correction):
- Cop: 7843265d4c0e8539191f48cc779a3c685ad8750b
- Thief: 03af6099e8726ba42f360c20d6ba8f300d0b3f8a

Once we have your `game.json` and agreement on the technical-loss row, we are ready
to name a kickoff time.
