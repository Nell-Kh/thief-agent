# yanell11 → uoh-ay26 — reply 2

*Send after re-running the suite and re-pushing; the commit SHAs below must be refreshed.*

---

**Team yanell11 → uoh-ay26**

Everything you confirmed matches us exactly — label, UID derivation, terms SHA,
`game_uid`, the 14-key count, the role schedule, and `game_id "G010"` +
`game_uid` in the consensus preimage. Thank you for confirming the `roles` /
`score` keys are real group ids; that was the one place our two published
examples could still have diverged silently, and it would have broken every row.

**Turn order: you are right, and we were wrong in a way worth explaining.**

We declared `cop_first`. Our code has always played **thief first** — our one
networked turn loop sends the thief's move before waiting for the opponent, and
our own runtime docstring says so ("the thief moves first, as in the reference
implementation"). The `cop_first` value was a constant nothing sequenced from,
contradicting the loop it claimed to describe.

That shape is dangerous in both directions: a peer declaring the truth gets
refused by us at the handshake, while a peer who believed our declaration and
implemented cop-first would be accepted and then silently diverge. We have
corrected the constant to `thief_first` and the two docstrings that repeated the
error. **No change to the turn loop was needed** — we now declare what we have
always played, and we agree with you.

**Updated commit SHAs** (the turn-order correction lands after the ones we sent):

- Cop: `<REFRESH>`
- Thief: `<REFRESH>`

Same branch `yanell11_vs_uoh-ay26` in both repos, pushed.

## Four things still open

**1. Your commit hashes.** Send both when you have pushed, and we will treat them
as binding. We will not start before we have them.

**2. Your `game.json`.** Please attach the file itself. We run a pre-match
checker against it the night before, and the one term that has actually refused
a handshake for us in the past is `setting` — ours is `"Haifa"`.

**3. One worked six-row example.** You confirmed the key question, but we would
still like to match a full series offline before we play. What we most want to
see is **how you spell a row for a sub-game that ended in a technical loss** —
`result`, `winner_group`, and both `score` entries. That is the row shape our
two implementations are most likely to disagree about, and it only shows up when
something has already gone wrong.

**4. The consensus window — we have a constraint you should know about.**

Rule 1 / §2.4.2 makes us run cop and thief as two completely separate processes,
one role each. Neither holds the whole series: each plays three windows and
writes three rows, and our six-row result — and therefore our consensus SHA —
does not exist until a separate merge step joins the two halves off disk. Both
playing processes have exited by then.

So we cannot answer a `series_consensus` the instant g06 settles. Concretely we
propose:

- g06 settles; both our halves finish and write their rows.
- We merge (local, seconds) and compute the consensus SHA.
- We dial your endpoint with our `series_consensus` envelope
  (`records: []`, `consensus_sha`) within **5 minutes** of g06 settling.
- You keep a peer serving for **10 minutes** past g06 to receive it, and we keep
  one serving for the same window to receive yours.

If your finalizer expects the exchange inside a shorter window, tell us now and
we will keep a listener up through the whole series rather than starting one
after the merge. We would rather agree the timing than have your report settle
`confirmed: false` because we were still merging.

As a belt-and-braces measure for this first friendly only: shall we also post our
consensus SHA to each other in writing once computed? The wire exchange stays
authoritative — this is just so that if the timing fails, both sides can see
whether the hashes agreed.

We propose the first series be uncounted, as before.
