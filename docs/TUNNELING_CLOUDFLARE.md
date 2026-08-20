# Friendly match over a Cloudflare Tunnel — runbook

`docs/TUNNELING.md` documents ngrok and Localtonet. This is the same procedure with
`cloudflared`, written as an ordered checklist for **one uncounted friendly** (rule #52,
TODO 9.4.1–9.4.3 / 11.3.1) played as a **rule-1 role split**: two processes, two ports,
two tunnels, two artifact directories, joined once at the end by `scripts/merge_series.py`.

Nothing in the code changes for a tunnel — only the URLs on the command line. The
`ngrok-skip-browser-warning` header `infra/peer_session.py` sends on every call is inert
against Cloudflare, so no edit is needed there either.

**Why split.** Appendix ה table 7 rule 1 and §2.4.2 require the cop's code and the thief's
code in two completely separate processes; the named sanction is כישלון מוחלט. najamjad
refused to play our unsplit peer on 2026-08-18 and were right to. `scripts/_series_windows.py`
implements the split as a filter: each process plays only the three windows of its own role
and **files nothing** — three rows are not a report.

Two checkouts, one role each:

| | folder | role | port | windows (with `--start-role police`) |
|---|---|---|---|---|
| A | `police-agent` | police | 8801 | 1, 3, 5 |
| B | `thief-agent`  | thief  | 8802 | 2, 4, 6 |

The two trees are byte-identical apart from the front-page README, so this is a convention,
not a constraint — but keep it, because it makes the tunnel URL you paste unambiguous.

---

## 1. Agree in writing, before anything is launched

The handshake refuses on a mismatch, and no amount of waiting fixes a refusal
(`_series_lib.negotiate_patiently` propagates it immediately). Settle all of this by message
first:

- [ ] **The 14 signed terms** — send them your `config/game.json` and ask for theirs. The one
      that has actually bitten us is `world.map_area` (`setting`): ours ships `"Haifa"`
      (TODO 9.4.5). A kit-derived opponent on a different arena refuses at kickoff.
- [ ] **Who opens as which role.** The two sides must be complementary: if you open as police,
      they open as thief.
- [ ] **Sub-game count** — 6 (`network_and_league.num_games`).
- [ ] **Their `group_id`** exactly as they will declare it on the wire. A mismatch aborts.
- [ ] **`[interop].profile`** — we speak `kit`. Both sides must agree; a silent disagreement
      is the mutual-zero shape of rules #19/#35.
- [ ] **`[interop].tie_award`** — we use `add`. The book is ambiguous and the kit does not
      settle it, so it forks the settlement hash. Agree it explicitly.
- [ ] **A `--series-label`** distinguishing this series from any other against the same
      opponent (e.g. `friendly-1`). Without it the kit's derivation gives every series against
      them the same `game_id`.
- [ ] **Their two repo URLs** (`cop=...,thief=...`) — rulebook 9.3.3 makes both teams' links a
      mandatory report field, and a peer that declares nothing leaves ours empty.
- [ ] **Whether they are role-split too.** If yes, get **both** their URLs: their cop endpoint
      and their thief endpoint. If they run one process, they give one URL and you leave
      `--peer-thief` empty.

A friendly stays uncounted by construction: `reports.league_block` arms `counted` only for the
binding league address, and `friendly_series.py` exits non-zero if a friendly ever reports
`counted=true`. Leave `[email].mode = "draft"` and do **not** pass `--counted`.

## 2. The night before: preflight their contract

```powershell
uv run python scripts/preflight.py --their-config ~\Downloads\their_game.json --role police
```

Exit status 1 means a blocker. Read the report, fix `config/game.json`, delete their file.
This is the whole point of TODO 11.3.7 — find the refusal the night before, not at kickoff
with both teams waiting.

## 3. Install cloudflared and open two quick tunnels

```powershell
winget install --id Cloudflare.cloudflared
```

Then, in two terminals of their own that stay open for the whole series:

```powershell
# Terminal T1 — fronts the POLICE process
cloudflared tunnel --url http://127.0.0.1:8801

# Terminal T2 — fronts the THIEF process
cloudflared tunnel --url http://127.0.0.1:8802
```

Each prints a line like `https://random-words-here.trycloudflare.com`. **Append `/mcp`** before
giving either to the opponent:

```
police endpoint : https://<A>.trycloudflare.com/mcp
thief  endpoint : https://<B>.trycloudflare.com/mcp
```

### Cloudflare specifics worth knowing before you name a start time

- **The port must match.** `--url http://127.0.0.1:8801` must name the same port as the
  driver's `--port` / `[network].my_port`.
- **Serve on `127.0.0.1`, not `0.0.0.0`.** `cloudflared` runs on the same machine and dials
  localhost itself; `0.0.0.0` is for a direct remote connection. `--host 127.0.0.1` is the
  driver's default, so just leave it alone.
- **Do not add `--http-host-header`.** It is Cloudflare's equivalent of the ngrok flag
  `docs/TUNNELING.md` warns about: it rewrites the redirect FastMCP issues for `/mcp` so it
  points back at the *client's* localhost, which surfaces as exactly the empty
  `Client failed to connect:` error. `fastmcp` 3.4.5 leaves host/origin protection **off** by
  default, so the forwarded `Host` header needs no accommodation.
- **A quick tunnel URL is not stable.** Restarting `cloudflared` mints a *new* random
  hostname — unlike an ngrok static domain, which survives a restart and can therefore front a
  dead agent. Cloudflare's failure is louder, but it means a restart mid-series obliges you to
  re-send the URL to the opponent.
- **Quick tunnels do not support the legacy SSE transport.** We serve
  `transport="http"` (Streamable HTTP, `mcp_server.py::serve`), which is the supported one — but
  the held-open session in `infra/peer_session.py` is precisely the shape that a tunnel reaping
  idle streams breaks, so run the `--hold` probe in step 4 rather than assuming.
- **Concurrency and uptime.** Quick Tunnels cap in-flight requests (429 above the cap) and carry
  no SLA — they are documented as testing/development only. That is acceptable for a friendly;
  for a counted series consider a named tunnel on a free Cloudflare account.

## 4. Prove both tunnels before you agree a kickoff time

`scripts/probe_peer.py` only lists tools, so it is safe against a live peer. Start each side's
server first (step 5 launches it), or point the probe at a peer you have already started.

```powershell
# is the endpoint there at all?
uv run python scripts/probe_peer.py https://<THEIRS>.trycloudflare.com/mcp

# does it STAY there? twenty dials, three seconds apart
uv run python scripts/probe_peer.py https://<THEIRS>.trycloudflare.com/mcp --repeat 20 --gap 3

# does a held-open session survive, the way a match actually plays?
uv run python scripts/probe_peer.py https://<THEIRS>.trycloudflare.com/mcp --repeat 10 --hold
```

Anything short of 20/20 is the failure that later reads as "the opponent crashed mid-series".
**Run all three against your own two tunnels as well** — the side that drops is not always the
side that reports the error.

If the `--hold` probe is the only one that fails, the tunnel is reaping idle streams. Raise
`--turn-patience` (step 5) before you consider anything else.

## 5. Kickoff — four terminals

Both processes must be given the **same `--start-role`**: it is the origin of the window
arithmetic, and `--play-windows` is only the filter applied on top of it. Getting them
different silently gives both processes the same three windows and no series.

```powershell
# Terminal 1 — POLICE half, in the police-agent checkout
cd C:\Users\yanal\OneDrive\Desktop\police-agent
uv run python scripts/friendly_series.py `
    --peer        https://<THEIR-COP>.trycloudflare.com/mcp `
    --peer-thief  https://<THEIR-THIEF>.trycloudflare.com/mcp `
    --opponent-group-id  theirteam `
    --opponent-repos     "cop=https://github.com/them/police-agent,thief=https://github.com/them/thief-agent" `
    --start-role  police `
    --play-windows police `
    --port 8801 `
    --public-url  https://<A>.trycloudflare.com/mcp `
    --series-label friendly-1 `
    --rounds 6 --wait 300 --turn-patience 60
```

```powershell
# Terminal 2 — THIEF half, in the thief-agent checkout
cd C:\Users\yanal\OneDrive\Desktop\thief-agent
uv run python scripts/friendly_series.py `
    --peer        https://<THEIR-COP>.trycloudflare.com/mcp `
    --peer-thief  https://<THEIR-THIEF>.trycloudflare.com/mcp `
    --opponent-group-id  theirteam `
    --opponent-repos     "cop=https://github.com/them/police-agent,thief=https://github.com/them/thief-agent" `
    --start-role  police `
    --play-windows thief `
    --port 8802 `
    --public-url  https://<B>.trycloudflare.com/mcp `
    --series-label friendly-1 `
    --rounds 6 --wait 300 --turn-patience 60
```

Notes on the flags that are not obvious:

- `--peer` is **their cop** endpoint and `--peer-thief` **their thief** endpoint;
  `_series_subgame.peer_url_for` dials their thief exactly when we are police. If the opponent
  is not split, give one URL as `--peer` and omit `--peer-thief`.
- `--public-url` is recorded in the declaration artifact. It is documentation, not routing —
  but it is what lets both sides reconstruct afterwards which tunnel was in play.
- `--wait` (default 120s) is the rendezvous window: whichever peer starts first keeps
  re-offering terms and prints `opponent not up yet - waiting for it to start...`. 300 gives a
  human-sized margin for two teams coordinating over chat.
- `--turn-patience` (default 40s) is how long a *turn delivery* keeps retrying a dropped
  tunnel; it is bounded well inside the opponent's own turn wait. Raise it toward 60 if the
  step-4 `--hold` probe was shaky. The opening handshake deliberately keeps the short budget.
- Do **not** pass `--counted` and do not pass `--friendly-report-to` unless the opponent asked
  for automatic friendly delivery. Note that `[email].mode = "draft"` cannot work under the
  `gmail.send`-only scope at all (TODO 9.1.6 — Google requires `gmail.compose` for drafts), so
  a friendly that tries to mail itself will 403 unless you also flip the mode.

Verify on the first three lines each process prints:

```
game_id  = ...
commit   = <sha>   <- verify this is the code you meant to play
setting  = 'Haifa' (a signed term - must match the opponent)
```

Both halves must print the **same `game_id`** and the **same `commit`**. On 2026-08-17 we told
sharNamr in writing that a fix was running when it was only committed; that line exists so it
cannot happen again.

## 6. Merge the two halves

Each locked process exits with `windows [1, 3, 5] settled...` and prints the
`games_played` the opponent declared **on the wire**. Use that number — do not invent one.

```powershell
cd C:\Users\yanal\OneDrive\Desktop\police-agent
uv run python scripts/merge_series.py `
    ..\police-agent\results\friendly_<game_id>_police `
    ..\thief-agent\results\friendly_<game_id>_thief `
    --opponent-group-id theirteam `
    --opponent-games-played <what they declared> `
    --series-label friendly-1 `
    --opponent-repos "cop=...,thief=..."
```

The merge refuses an incomplete or double-claimed window set, which is the check that stops a
half-series being presented as a whole one.

## 7. Cross-check artifacts with the opponent

Point the kit's checker at the two **series folders**, never at `results/` — its two-directory
join recurses, so a tree holding several archived series takes on the rule-35 contradictory
shape (kit finding P5, TODO 9.4.14):

```powershell
python tools/check_artifacts.py results\friendly_<game_id> <their-folder>
```

You are looking for an identical `game_uid` and a byte-identical `mutual_agreement.sha256` on
both sides.

## 8. Reading a failure correctly

- **A refusal is not a silence.** If they answer but reject the terms (contract digest or
  scent-model mismatch), it is reported verbatim and never retried. Go back to step 1.
- **`PeerUnreachableError` after a successful handshake** means the URL was right — `negotiate`
  and `receive_turn` travel to the same address. With both peers behind free tunnels it is
  overwhelmingly the tunnel, not the peer. Probe both sides (step 4) before blaming anyone.
- **`(RuntimeError: Client failed to connect: <- ClosedResourceError)`** — `infra/net_errors.py`
  renders the whole cause chain now; the type after the arrow is the fact worth reading.
- **A sub-game that dies is contained, not fatal.** It scores a technical loss and the series
  continues; rows are persisted after every sub-game, so a crash costs the remainder, never the
  games already won. Watch for the containment alarm at the end — it accuses our own driver
  first, by design.

## 9. Afterwards

- Stop both `cloudflared` terminals. The URLs are dead the moment you do, and a new run mints
  new ones.
- Leave `[email].mode` at `draft` and `[email].recipient` at the binding league address. The
  repository's resting state is the rehearsal state.
- Tick TODO 9.4.1 / 9.4.2 / 9.4.3 and 11.3.1, and record the opponent, the date and the
  `game_id` — rule 37 counts declared games, and the ledger is only as good as what you wrote
  down.
