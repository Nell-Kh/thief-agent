# G010 friendly — shared run procedure (yanell11 ↔ uoh-ay26)

We've had clean probes on both sides but the match keeps not starting. Every failure
so far has been coordination, not code: a `502` (peer not serving yet), then a
one-sided handshake (you were dialing a tunnel of ours that had changed). This note
pins down exactly how both sides run it so g01 actually negotiates. Please read it in
full — a couple of points are non-obvious and are the reason the earlier attempts died.

## 1. The handshake is MUTUAL — both sides dial each other

For every sub-game, each peer is both a server and a client. It is not enough that we
can reach you; **you must also reach us**, because your greeting is delivered by *you*
calling *our* endpoint. If either direction fails, the sub-game times out and scores a
technical loss. Both our last two failures were this: your side up, ours reachable, but
your greeting never arrived at our peer because you held a stale URL for us.

## 2. There is a hard 180-second greeting window

Once one side reaches the other, it waits **180 seconds** for the reciprocal greeting,
and no longer. A long `--wait` only governs reaching a peer that hasn't started; it does
**not** extend this 180s. So both sides must be fully up within about a minute of each
other. That is why we're fixing a wall-clock launch time rather than "start when ready."

## 3. Current endpoints (frozen — neither side restarts tunnels)

**Ours (yanell11), Cloudflare quick tunnels:**
- our COP peer:   `https://plenty-warehouse-bibliography-making.trycloudflare.com/mcp`
- our THIEF peer: `https://capabilities-dragon-awarded-baghdad.trycloudflare.com/mcp`

**Yours (uoh-ay26):**
- your COP:   `https://cop.uohay26game.com/mcp`
- your THIEF: `https://thief.uohay26game.com/mcp`

If either of us restarts a quick tunnel, its hostname changes and the other side is
instantly dialing a dead URL. **Neither side restarts a tunnel after this point.** If a
tunnel dies, we abort, re-exchange, and pick a new time — we do not play through it.

## 4. We both run the rule-1 split — which endpoint plays which role

We each run cop and thief as two separate processes on two separate tunnels. Roles
alternate by sub-game. The routing for the whole series:

| sub-game | yanell11 role | uoh-ay26 role | dials our… | dials your… |
|---|---|---|---|---|
| g01, g03, g05 | police | thief | your THIEF (`thief.uohay26game.com`) | our COP (`plenty-warehouse…`) |
| g02, g04, g06 | thief  | police | your COP (`cop.uohay26game.com`)   | our THIEF (`capabilities-dragon…`) |

So when we are police (odd games) our cop peer dials your thief, and **your thief must
dial our cop tunnel back**. When we are thief (even games) our thief peer dials your cop,
and **your cop must dial our thief tunnel back**. Both your processes need to be serving
for the whole series, not started per window.

## 5. Launch sequence

1. **T-10 min:** both sides bring up all tunnels and all peers, and leave them running.
2. **T-5 min:** mutual probe. We list-tools your cop and thief; you do the same to our two
   endpoints. Both sides confirm **5/5 on each endpoint** in writing before we proceed.
   Anything short of 5/5 = someone isn't fully up; we hold, we don't launch.
3. **At T:** both sides start their series drivers within the same minute. Whoever's
   greeting lands first waits (inside the 180s) for the other's.

## 6. Agreed game rules for G010 (already settled, restated for the record)

- label `G010`; `game_uid` `9d720049-dd3d-6ee2-a7db-67f17fb78f2d`
- 14 signed terms SHA `ad9e1bfd724e9debcde523833381cb7982a5d619d693d3738b59e0da61f4d81a`
- turn order `thief_first`; role schedule as in §4
- `response_timeout_sec` 120, `watchdog_timeout_sec` 180
- `technical_loss` row → `score 0/0`, `winner_group null`
- **replay-on-technical-loss:** if any sub-game ends `technical_loss`, we both stop, post
  our rows and SHA for diagnosis, and replay the series — we do not settle that run.
- consensus after g06: uid-scope preimage, `game_id "G010"` + `game_uid`, records `[]`;
  we merge our two halves, dial you with the consensus SHA within 5 minutes of g06, and
  post the SHA in writing too as a backup. Please keep a peer serving ≥10 min past g06.

## 7. What each side verifies before walking away

Each process prints its `game_id`, playing `commit`, and `setting` at startup. Both of
our processes will show `game_id = uoh-ay26-vs-yanell11-G010` and `setting 'Haifa'`.
Please confirm the same on your side. If the two sides' `game_id` or `setting` differ,
stop — the handshake will refuse and we fix config before retrying.

Propose a launch time and we'll confirm. From then it's: both up by T-10, mutual 5/5
probe by T-5, launch at T, no tunnel restarts.
