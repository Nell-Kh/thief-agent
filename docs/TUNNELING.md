# Exposing a Peer to the Public Internet

Localhost is permitted only during early development; for league play every
team **must** expose its FastMCP server through a tunnel (rulebook ch. 2.4).
Nothing in the code changes between the two - only the URLs in the private
TOML files.

## With ngrok

```bash
# 1. Start your peer (it serves on the port from [network] my_port)
uv run python -m police_thief peer --role police

# 2. In another terminal, open the tunnel to that port
ngrok http 8801
# ngrok prints something like: https://a1b2c3.ngrok-free.app
```

Give the printed URL (with the `/mcp` suffix) to the opposing team; put their
URL in your own private TOML:

```toml
[network]
my_port = 8801
opponent_url = "https://THEIR-TUNNEL.ngrok-free.app/mcp"
```

## With Localtonet

Same flow: run `localtonet http 8801`, exchange the generated URL, update
`opponent_url` on both sides.

## Starting order does not matter

Two teams cannot start their processes on the same second, so the opening
handshake is a **rendezvous**, not a single shot: whichever peer starts first
keeps re-offering its terms while the other is still booting, printing

```
[police] opponent not up yet - waiting for it to start...
```

and, once its own handshake lands, lingers a few seconds still serving so the
slower side's call also completes. Defaults are 120s of waiting and 15s of
lingering; tune with `--wait` / `--linger` on `peer`, and `--wait` on
`scripts/friendly_series.py`.

This applies **only** to the opening handshake. Mid-match the short budget
below is what governs, and that asymmetry is deliberate: a peer that has not
started yet is not the same event as a peer that has gone dark mid-game.

## What failure looks like (by design)

Once a match is under way, the peer does not hang: every request carries a
30-second deadline and three retries with 5-second backoff, after which the
peer declares a clean technical loss and reports it. Reliability rules #6/#7
in action - "a missed deadline is a failure, not patience."

A **refusal** is not a silence. If the opponent answers but rejects the terms
(a contract digest or scent-model mismatch), that is reported verbatim and
never retried - no amount of waiting fixes a mismatch. If you can hear them but
they cannot hear you, the peer names `[network].opponent_url` as the likely
cause.

## When the tunnel is the opponent

A live series produced this, and it is worth reading closely:

```
sub-game 1 did not finish (PeerUnreachableError: receive_turn: opponent
unreachable after 3 attempts (receive_turn: call to
https://XXXX.ngrok-free.dev/mcp failed (Client failed to connect: )))
```

Two things are true in that line and neither is obvious.

**The handshake had already succeeded.** `negotiate` and `receive_turn` travel
to the same URL, so an opponent that greeted us and then "vanished" one message
later did not move, misconfigure a port, or refuse anything. The URL is right.
Something between the two calls stopped answering - which, with both peers
behind free tunnels, is overwhelmingly the tunnel rather than the peer.

**The reason is empty on purpose, not by accident.** fastmcp reports a failed
connection as `f"Client failed to connect: {exception}"`, and the exceptions a
dropped tunnel actually raises - `anyio.ClosedResourceError`,
`anyio.EndOfStream`, `httpx.ReadError` - are all constructed with no arguments,
so `str()` on them is the empty string. The one fact that would have named the
fault, the exception's *type*, was the one fact the message dropped.

Three changes followed, and they are the reason that line now reads differently.

* **Every failure is rendered with its type and its whole cause chain**
  (`infra/net_errors.py`). `(Client failed to connect: )` becomes
  `(RuntimeError: Client failed to connect: <- ClosedResourceError)`.
* **The session is held open** (`infra/peer_session.py`). One MCP session per
  sub-game instead of one per message: a move used to cost a TCP handshake, a
  TLS handshake and a five-request MCP session setup, and a six-sub-game series
  opened thousands of short-lived connections through a tunnel that would
  rather serve a few long ones. A failed call discards the session, so the
  retry that follows always reconnects on a clean one.
* **A turn delivery is patient; the handshake still is not.** The contract's
  three-tries-five-seconds budget spans fifteen seconds, which is shorter than
  a free tunnel takes to re-establish itself, so a reconnect used to cost a
  whole sub-game. `--turn-patience` (default 40s) keeps re-offering the same
  move, bounded well inside the opponent's own 60s turn wait so a peer that is
  genuinely gone still becomes a technical loss quickly. The opening handshake
  deliberately keeps the short budget - that wait belongs to the rendezvous
  loop, which can tell "not started yet" from "refused".

### Probe the tunnel before you blame the opponent

`scripts/probe_peer.py` is the same dial, alone and repeatable. It only lists
tools, so it is safe to point at a live opponent mid-series.

```bash
# is the endpoint there at all?
.venv/Scripts/python.exe scripts/probe_peer.py https://THEIR-TUNNEL/mcp

# does it STAY there? twenty dials, three seconds apart
.venv/Scripts/python.exe scripts/probe_peer.py https://THEIR-TUNNEL/mcp --repeat 20 --gap 3

# does a held-open session survive, the way a match now plays?
.venv/Scripts/python.exe scripts/probe_peer.py https://THEIR-TUNNEL/mcp --repeat 10 --hold
```

Anything short of 20/20 is the failure that reads as "the opponent crashed"
mid-series. Run it against **your own** tunnel too - the side that drops is not
always the side that reports the error.

### Free-tier facts worth knowing before a counted series

* An ngrok free agent restarting keeps the same static domain, so a URL that
  looks correct can front a tunnel that is briefly - or permanently - dead.
  `ERR_NGROK_3200` means no agent; `ERR_NGROK_8012` means the agent is up but
  nothing is listening on the port it forwards to.
* `ngrok http 8801` must name the same port as `--port` / `[network].my_port`.
* Do not pass `--host-header=localhost:8801`. It rewrites the redirect a
  FastMCP server issues for `/mcp` so it points back at the *client's*
  localhost, which fails with exactly the kind of empty connection error above.
* Serve on `127.0.0.1` when the tunnel agent runs on the same machine (it dials
  localhost itself). `0.0.0.0` is for a direct remote connection.
* We send `ngrok-skip-browser-warning: true` on every call, so the free tier
  answers our peer's tool call rather than its browser-warning page.

## Proving the tunnel before you name a start time

The league kit ships a network checker; a bare "is it up?" probe cannot tell a
healthy idle tunnel from one with no ingress rules, because both answer `502`
forever. Prove your own receiving path with its loopback mode:

```bash
python tools/netcheck.py https://THEIR-TUNNEL/mcp        # probe the opponent
python tools/netcheck.py --loopback 8801 https://YOUR-TUNNEL   # prove your own
```
