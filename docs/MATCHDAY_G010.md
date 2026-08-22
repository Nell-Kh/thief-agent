# G010 friendly vs uoh-ay26 — match-day runbook

Uncounted friendly. Rule-1 split: two processes, two ports, two tunnels, one role each.

| | folder | our role | windows | port |
|---|---|---|---|---|
| A | `police-agent` | police | g01, g03, g05 | 8801 |
| B | `thief-agent`  | thief  | g02, g04, g06 | 8802 |

Their endpoints are **named** tunnels and stable — note the deliberate misspelling of the thief host:

```
their cop   : https://cop.uohay26game.com/mcp
their thief : https://theif.uohay26game.com/mcp
```

Agreed and verified: `game_id` label `G010`, `game_uid`
`9d720049-dd3d-6ee2-a7db-67f17fb78f2d`, 14 signed terms
`ad9e1bfd…`, `thief_first`, technical-loss rows `0/0` + `winner_group: null`,
uid settlement scope, replay-on-technical-loss, 600 s consensus window.

---

## 1. Bring up two fresh tunnels

```powershell
# Terminal T1 — fronts the POLICE process
cloudflared tunnel --url http://127.0.0.1:8801

# Terminal T2 — fronts the THIEF process
cloudflared tunnel --url http://127.0.0.1:8802
```

Note both printed hostnames, append `/mcp`, and **send them to uoh-ay26**. Do not
restart either agent after sending — a restart mints a new hostname and the URL
they hold goes dead.

## 2. Start both peers

confirm their endpoint is alive before committing to a run:

uv run python scripts/probe_peer.py https://thief.uohay26game.com/mcp --repeat 5 --gap 3
uv run python scripts/probe_peer.py https://cop.uohay26game.com/mcp --repeat 5 --gap 3


Both commands take **`--start-role police`** — the same value in each. It is the
origin of the window arithmetic; `--play-windows` is only the filter on top. Two
different values silently give both processes the same three windows.

```powershell
# Terminal 1 — POLICE half
cd C:\Users\yanal\OneDrive\Desktop\police-agent
uv run python scripts/friendly_series.py `
    --peer        https://cop.uohay26game.com/mcp `
    --peer-thief  https://theif.uohay26game.com/mcp `
    --opponent-group-id uoh-ay26 `
    --opponent-repos "cop=https://github.com/aishadahesh/uoh-ay26-final-project-cop,thief=https://github.com/aishadahesh/uoh-ay26-final-project-thief" `
    --start-role police `
    --play-windows police `
    --port 8801 `
    --public-url https://capabilities-dragon-awarded-baghdad.trycloudflare.com/mcp `
    --series-label G010 `
    --games-played 2 `
    --rounds 6 --wait 3600 --turn-patience 60
```

```powershell
# Terminal 2 — THIEF half
cd C:\Users\yanal\OneDrive\Desktop\thief-agent
uv run python scripts/friendly_series.py `
    --peer        https://cop.uohay26game.com/mcp `
    --peer-thief  https://theif.uohay26game.com/mcp `
    --opponent-group-id uoh-ay26 `
    --opponent-repos "cop=https://github.com/aishadahesh/uoh-ay26-final-project-cop,thief=https://github.com/aishadahesh/uoh-ay26-final-project-thief" `
    --start-role police `
    --play-windows thief `
    --port 8802 `
    --public-url https://new-contests-coordinates-factory.trycloudflare.com/mcp `
    --series-label G010 `
    --games-played 2 `
    --rounds 6 --wait 3600 --turn-patience 60
```

**`--series-label G010` is not optional.** The uid settlement preimage takes its
`game_id` from that label; without it the preimage carries the wrong value and
the consensus SHA cannot match theirs.

**No `--counted`.** This is a friendly, and the gate would refuse anyway.

`--peer` is their **cop** and `--peer-thief` their **thief**: we dial their thief
exactly when we are police.

## 3. Check the three header lines each process prints

```
game_id  = uoh-ay26-vs-yanell11-G010
commit   = <sha>   <- verify this is the code you meant to play
setting  = 'Haifa' (a signed term - must match the opponent)
```

Both processes must print the **same `game_id`**. The commits must be
`fe89f40f95071225580ec6851a57660a395fd706` (police) and
`adabe4b578db52443b989e99672fce8c8a9d132c` (thief) — the two you gave uoh-ay26.
If either differs, stop: you are about to play code you did not declare.

## 4. After g06 — merge, then consensus, inside their 600 s window

Each half exits with `windows [...] settled` and prints the `games_played` the
opponent declared **on the wire**. Use that number; do not invent one.

```powershell
cd C:\Users\yanal\OneDrive\Desktop\police-agent
uv run python scripts/merge_series.py `
    ..\police-agent\results\friendly_uoh-ay26-vs-yanell11-G010_police `
    ..\thief-agent\results\friendly_uoh-ay26-vs-yanell11-G010_thief `
    --opponent-group-id uoh-ay26 `
    --opponent-games-played <what they declared> `
    --series-label G010 `
    --games-played 2 `
    --opponent-repos "cop=https://github.com/aishadahesh/uoh-ay26-final-project-cop,thief=https://github.com/aishadahesh/uoh-ay26-final-project-thief"
```

Read `mutual_agreement.sha256` out of the written result, **post it to them in
writing immediately** (the agreed debugging backup), then send it on the wire:

```powershell
uv run python send_consensus.py https://cop.uohay26game.com/mcp `
    results\friendly_uoh-ay26-vs-yanell11-G010\result_uoh-ay26-vs-yanell11-G010.json thief
```

### The rough edge, stated plainly

Nothing in `src/` sends the consensus envelope — `send_consensus.py` is a
root-level bolt-on — and both playing processes have exited by the time the SHA
exists, so **we have no listener up to receive theirs**. Their 600 s window
covers our merge comfortably, but the reciprocal direction is the gap.

Two mitigations, in order:

1. The written exchange agreed for this friendly. If the wire leg fails in either
   direction, both sides can still see whether the hashes agreed.
2. If they need us listening, bring one peer back up before running the merge and
   leave it serving on its original port so its tunnel still resolves:
   `uv run python -m police_thief peer --role thief --wait 600 --linger 600`

Building this properly into `src/` is the right move before a **counted** series.
For an uncounted friendly the manual path plus the written backstop is enough to
prove the hashes agree.

## 5. If a sub-game ends in technical_loss

Per the agreed policy: **stop**. Do not treat the run as settled. Both sides post
their rows and SHA for diagnosis, and the series is replayed. Watch for the
containment alarm the driver prints — it accuses our own driver first, by design.

## 6. Reading a failure

- `502` from their host = their agent idle. `530` / Cloudflare `1033` = no tunnel.
- A **refusal** (terms/dialect mismatch) is reported verbatim and never retried —
  no amount of waiting fixes it. Go back to the message thread.
- `PeerUnreachableError` *after* a successful handshake means the URL was right
  and something between the two calls stopped answering — with free tunnels that
  is almost always the tunnel. Probe both sides before blaming anyone.
- Rows persist after every sub-game, so a crash costs the remainder, never the
  games already won.
