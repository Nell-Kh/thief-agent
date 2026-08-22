# yanell11 → uoh-ay26 — G010 attempt aborted, need a synchronised restart

*Paste-ready. Fill in your thief tunnel URL before sending.*

---

**Team yanell11 → uoh-ay26**

We started the G010 friendly and had to abort at sub-game 1. **No result was
settled and we are not treating this run as played** — under the
replay-on-technical-loss policy we agreed, we stop and replay rather than settle.

## What we saw

Our police peer came up, bound its port, and dialled your thief endpoint for g01:

```
dialling their thief at https://theif.uohay26game.com/mcp
negotiate: opponent unreachable after 3 attempts
  (HTTPStatusError: Server error '502 Bad Gateway'
   for url 'https://theif.uohay26game.com/mcp')
```

By your own endpoint-readiness table, `502` means *"tunnel route is connected;
local origin is idle"* — your thief tunnel was routing correctly, but no thief
process was serving behind it yet. Your cop endpoint was never reached, since
g01 dials your thief.

So we read this as a **timing miss, not a fault in anyone's implementation**: we
started before your peers were up.

## One thing on our side, disclosed

Our rendezvous loop is supposed to keep re-offering terms for the full `--wait`
window (we ran with 600 s) while an opponent is still booting. It did not: it
retries a *silence*, and a `502` is an HTTP answer rather than a silence, so the
call failed through the normal three-attempt budget and scored a technical loss
in seconds instead of waiting ten minutes.

That is our bug and we are fixing it. We mention it because it may bite you in
the mirror image, and because it explains why we gave up so quickly rather than
waiting for you.

## What we need for the restart

1. **Both your peers serving, not just both tunnels up.** g01 needs your thief
   and g02 needs your cop, and with the role split both processes need to be
   live for the whole series rather than started per window.
2. **An agreed wall-clock kickoff time.** Propose one and we will be up and
   probing five minutes beforehand.
3. **A mutual probe before we start.** We will confirm both your endpoints answer
   a tool listing 5/5 before we launch, and we ask you to do the same against
   ours. Anything less than 5/5 is the failure that later reads as "the opponent
   crashed mid-series."

## Our endpoints for this attempt

These are Cloudflare quick tunnels and the hostnames change on every restart.
Current:

- Cop: `https://years-repairs-cdna-demonstration.trycloudflare.com/mcp`
- Thief: `<FILL IN YOUR 8802 TUNNEL>`

If you probe either and get `530` / Cloudflare `1033`, that is a restarted tunnel
and a stale URL — message us and we will send the new one rather than read it as
you being down. We will re-send both immediately before the agreed kickoff so you
are never working from a stale hostname.

Everything else agreed remains unchanged and verified on our side: `G010`,
`game_uid 9d720049-dd3d-6ee2-a7db-67f17fb78f2d`, the 14 signed terms at
`ad9e1bfd…`, `thief_first`, the role schedule, the uid consensus preimage, and
the 600 s consensus window.

Ready when you are — name a time.
