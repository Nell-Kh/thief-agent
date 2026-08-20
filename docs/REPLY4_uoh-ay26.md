# yanell11 → uoh-ay26 — reply 4 (agreed; two notes on the contract)

*Refresh the two commit SHAs before sending.*

---

**Team yanell11 → uoh-ay26**

**The settlement is now proven, not assumed.** Your corrected six-row preimage
hashes to `d3eff951328452b0ee523c8af0ae8859796e5d3ae8fe19589232d2b6a5ce2cbd`,
which is byte-for-byte the value our implementation produced independently for
those same six outcomes before you sent it. All six rows agree, including both
`technical_loss` rows at `0/0` with `winner_group: null`. Thank you for
re-checking that against your scoring code rather than against the example.

Agreed and locked on our side:

- `technical_loss` → `score` `0/0`, `winner_group: null`
- If any sub-game in G010 ends `technical_loss`: we stop, both post rows and SHA
  for diagnosis, and replay rather than settle
- Consensus: we merge after g06 and dial you within 5 minutes; both sides keep a
  peer serving; SHA also posted in writing as a debugging backup, wire
  authoritative

We checked your two commits resolve publicly and that
`SERIES_CONSENSUS_TIMEOUT_SECONDS = 600.0` is genuinely in them.

## Your `config/game.json` — all 14 signed terms match

We ran it through our pre-match checker. The 14 signed terms derived from your
file hash to `ad9e1bfd724e9debcde523833381cb7982a5d619d693d3738b59e0da61f4d81a`,
identical to ours and to the value we both published. The handshake will pass.

Four keys outside the signed set differ. Two are cosmetic, two are not:

**1. We have adopted your timeouts.** Yours read `response_timeout_sec: 120` and
`watchdog_timeout_sec: 180`; ours read `30` and `60`. Neither is in the signed
terms, so nothing would have refused — which is exactly why it was worth
catching.

The asymmetry ran against you: your peer would have waited 120s for us, while we
would have abandoned you at 30s. A peer is entitled to the deadline it published,
and cutting it short manufactures a technical loss against a compliant opponent.
Under the fallback we just agreed, that would not merely cost a sub-game — it
would void and replay the whole series. We have changed our shared contract to
`120` / `180` to match yours.

**2. Your file has no top-level `version` key.** Ours carries `"version": "1.00"`,
and our loader treats it as mandatory — guidelines ch. 8.1 requires both code and
configuration to carry an explicit version starting at 1.00, and we refuse to load
a contract without one rather than guess at compatibility. This does not affect
our match: we each load our own copy, and every signed term agrees. We mention it
only because a grader reading ch. 8.1 may look for it in your file.

**3–4. Cosmetic.** We have set `agreed_between` to `["uoh-ay26", "yanell11"]` to
match yours; it is descriptive and read by no code on our side.

**Our refreshed commit SHAs** (turn-order correction, then the contract change
above — the second push is the binding one):

- Cop: `<REFRESH>`
- Thief: `<REFRESH>`

## Ready when you are

From our side everything is now agreed and verified: identity, label, `game_uid`
and its derivation, the 14 signed terms, turn order, role schedule, the full
consensus preimage including technical-loss rows, the consensus window and flow,
and the replay-on-technical-loss policy for this friendly.

Propose a kickoff time and we will bring both tunnels up 15 minutes beforehand and
probe them from your side and ours before we start.

One practical note: our two endpoints are Cloudflare quick tunnels, so the
hostnames change if either agent restarts. If you probe us and get `530` /
Cloudflare `1033`, that means a restarted tunnel and a stale URL — message us and
we will send the new one rather than have you read it as us being down.
