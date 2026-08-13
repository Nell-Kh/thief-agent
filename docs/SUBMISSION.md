# Submission runbook — the steps only a human can perform

Everything mechanical is already done and verified by the suite: both
submission trees build from the git index (`scripts/split_repos.py`), each
passes the full gates independently, the four-link block reads two distinct
real URLs from `[game].repos`, and the reports are addressed to the binding
league inbox in `draft` mode. What remains needs a GitHub account, a Gmail
account or a Moodle login — this file is that list, in order, so nothing is
rediscovered at the deadline.

## 1. Republish the two submission repos with their real history

**This is the repeatable procedure, not a one-off.** Because both role repos are
"the dev tree plus one README banner", *any* change to the dev tree — a doc fix,
a new counted-series artifact, anything — has to reach them, and the honest way
to do that is to re-graft rather than to hand-edit a published repo. Hand-edits
also silently vanish the next time this runbook is run.

It started as a repair: the repos were first published as a single squashed
commit built from an older dev commit, a tree that still carried a broken
front-page command and stale report numbers. Since both repos deliberately ship
the full engine, the entire dev history (both authors, all commits, untouched
hashes) can be **grafted** underneath the banner commit, which fixes the stale
tree and gives the grader the real development story Appendix ג values. An
external audit verified the graft reproduces the published tree byte-for-byte.

Run it whenever `main` moves on the dev repo. Each run leaves exactly one banner
commit on top of the real history — the shape never drifts, however many times
you re-graft.

First, on the dev repo (once): commit and `git push origin main`, then `uv run
python scripts/split_repos.py` so `build/<name>/README.md` carries the current
banner over the current report.

Then, once per repo (`police-agent`, then `thief-agent`; substitute the name
everywhere):

```
git clone https://github.com/Nell-Kh/police-agent.git pa-rewrite
cd pa-rewrite
git remote add dev https://github.com/Nell-Kh/police-thief-p2p.git
git fetch dev

# safety net: keep the currently published commit reachable, by name.
# On a re-graft the branch already exists, so move it to today's tip:
git branch -f pre-graft-backup main
git push -f origin pre-graft-backup

# the real history, with the corrected banner replayed as one honest commit
git checkout -b main-new dev/main
cp /path/to/police-thief-p2p/build/police-agent/README.md README.md
git add README.md
git commit -m "role banner: police-agent - submission tree for the POLICE peer"

# gates inside the grafted tree, then publish
uv sync && uv run pytest -q && uv run ruff check src scripts tests
git branch -M main-new main
git push --force-with-lease origin main

# the annotated tag must move to the new tip (Appendix Gimel: -a and -m).
# A tag left on the old tip is worse than no tag: it points the grader at a
# tree that is not the one you are submitting.
git tag -d v1.0-submission
git push origin :refs/tags/v1.0-submission
git tag -a v1.0-submission -m "Final submission: Police-Thief P2P, team yanell11"
git push origin v1.0-submission
git show v1.0-submission | head -3   # must say 'tag', not a bare commit
```

Keep `pre-graft-backup` until the grade is settled. Do both repos or neither —
two submission repos with different-shaped histories invites questions. Never
force-push the dev repo itself; it is the provenance anchor.

Finally: verify from a logged-out browser window that both repos and both tags
are visible, and that each README's first command is `peer`, not `serve`.

## 2. Counted series (task 9.5) — the guard will hold the door

The config is already armed correctly: recipient is the league inbox,
`mode = "draft"` parks each report in Gmail Drafts for a human look. Play with
`--counted`; the driver refuses upfront if anything would stop the series
counting. After eyeballing the drafted report, either send it from Drafts or
flip `mode = "send"` for the second series. The Gmail OAuth files live on the
machine that ran the Appendix-A setup — play from anywhere, but mail the
report from that machine.

## 3. Moodle (rules #43/#44, App. ג)

- Fill the Moodle form, save as PDF with fields untouched.
- Submit **individually** — each team member uploads.
- Paste **two** repo links: `police-agent` and `thief-agent` (not the dev repo).

## 4. Last look before the deadline

- `git log --oneline -5` in both published repos shows the tag on the tip.
- The result JSON of every counted series carries four links, two per team.
- No `credentials.json`, `token.json` or `.env` in ANY pushed tree
  (`git ls-files | grep -E "credentials|token|\.env"` prints nothing).
