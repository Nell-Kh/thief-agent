# Reply to uoh-ay26 — g03 boundary handoff

Thanks — that matches exactly what we saw from our side, and it turns out the
g03 boundary bit both of us, symmetrically.

Your read is right: g03 negotiates early because your endpoint is up, but the
first *turn* has to wait for your one sequential driver to cross g02→g03, and a
normal ~120s turn timeout can't cover that. Good call writing a diagnostic
`technical_loss` on that path too — a silent exit with no g03 files was the part
that made it hard to diagnose from the outside. Noted your new commits:

- cop:   `1f9f6621b6ec9d7620d164ce2d019790afe1b28c`
- thief: `f87a0cc8b650616e8b1c2ffa70475847c537b5d3`

## What we found on our side (the receiving end of the same boundary)

Our two-process split has the mirror of your problem: while your driver is still
crossing the boundary, *we're* the one sitting and waiting for your first turn.
Our patience for that first turn was being derived from our `--wait` flag, whose
default is 120s — so unless the flag was set high, our first-turn window
collapsed to ~180s and would have timed *you* out mid-handoff, scoring a g03
technical loss against a peer that was doing nothing wrong. That's the wait you
saw us abandon.

Fixed on our side now:

- The first-turn window (and the greeting/audit waits at a boundary) is floored
  at **1200s**, independent of any launch flag — it matches the boundary window
  you declared, so neither side can time the other out during the crossing.
- Every turn *after* the first keeps the normal 180s contract deadline, so a
  genuine mid-game stall still fails fast — only the boundary crossing gets the
  long window.
- We also added a heartbeat to the wait so a healthy 1200s hold prints progress
  instead of looking like a hang (that's on us — we interrupted a working wait
  by hand last run).

Net effect: both directions now tolerate g02→g03 (and every other boundary), so
a clean replay shouldn't trip on it from either side.

## Replay

Agreed, ready to replay from g01. Nothing else changed on our end:

- `G010`, `game_uid 9d720049-dd3d-6ee2-a7db-67f17fb78f2d`, 14-term SHA
  `ad9e1bfd724e9debcde523833381cb7982a5d619d693d3738b59e0da61f4d81a`,
  `thief_first`, role schedule as before.
- `technical_loss` → `0/0` / `winner_group null`, replay-on-technical-loss,
  consensus exchange after g06.
- Endpoints unchanged; we'll dial your thief at `thief.uohay26game.com` and your
  cop at `cop.uohay26game.com`, and keep our two tunnels up without restarts.

Propose a launch T and we'll do the usual: both sides up by T-10, mutual 5/5
probe by T-5 (we'll confirm our playing commits then, same as you did), start
drivers at T. Name a time and we're go.
