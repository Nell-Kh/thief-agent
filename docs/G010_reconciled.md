# G010 — reconciled launch procedure

Thanks, that clears it up. Your one-driver-sequential model and our two-process
split are compatible — we just had the wrong pre-launch gate. Here's how they fit
together and how we launch.

## How our two sides differ (both fine)

- **You:** one series driver, one role live at a time, strict g01→g06. Your cop
  isn't serving until g02.
- **Us:** rule 1 (§2.4.2) requires us to run cop and thief as two *separate*
  processes, so we run both at once. Our police process owns g01/g03/g05 and our
  thief process owns g02/g04/g06. Both stay up the whole series; each simply
  waits its turn when it's the other role's sub-game.

These interlock cleanly. When you're on an odd game your thief talks to our cop;
when you advance to an even game your cop talks to our thief. Whichever of our
processes isn't in play is patiently re-offering and will connect the moment your
matching role comes back up. We're running a long wait window so a process
survives a full opposite-role sub-game before its own next window.

## The corrected gate

Requiring both our endpoints (and both of yours) to answer before g01 was the
mistake — your cop legitimately isn't up yet at kickoff. So before g01 we only
confirm the **g01 pair**:

- your THIEF `https://thief.uohay26game.com/mcp`  ← we probe this
- our COP `https://plenty-warehouse-bibliography-making.trycloudflare.com/mcp`  ← you probe this

Your cop and our thief come online for g02 and are verified by g02 negotiating,
not by a pre-probe.

## Launch

1. **T-10:** both sides bring everything up. On our side that's both tunnels and
   both processes (police + thief); the thief process will sit waiting for g02,
   which is expected. On your side, your driver ready to start from the thief repo.
2. **T-5:** we probe your thief 5/5; you probe our cop 5/5. Confirm in writing.
3. **At T:** you start your series driver (thief repo, g01). We start both our
   processes. g01 = your thief ↔ our cop. After g01 it alternates automatically
   through g06.

## Dial map (unchanged, restated)

| game | you | us | your live role dials our… | our live role dials your… |
|---|---|---|---|---|
| g01/g03/g05 | thief | police | our COP `plenty-warehouse…` | your THIEF `thief.uohay26game.com` |
| g02/g04/g06 | cop | thief | our THIEF `capabilities-dragon-awarded-baghdad…` | your COP `cop.uohay26game.com` |

Neither side restarts a tunnel from here. If one dies we abort, re-exchange URLs,
and pick a new T.

Everything else stays as agreed: `G010`, `game_uid 9d720049-…`, 14-term SHA
`ad9e1bfd…`, `thief_first`, technical-loss `0/0`/`null` with replay, and the
consensus exchange after g06. Name a T and we're go.
