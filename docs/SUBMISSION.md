# Submission runbook — the steps only a human can perform

Everything mechanical is already done and verified by the suite: both
submission trees build from the git index (`scripts/split_repos.py`), each
passes the full gates independently, the four-link block reads two distinct
real URLs from `[game].repos`, and the reports are addressed to the binding
league inbox in `draft` mode. What remains needs a GitHub account, a Gmail
account or a Moodle login — this file is that list, in order, so nothing is
rediscovered at the deadline.

## 1. Publish the two submission repos (rule #49, task 8.19)

```
uv run python scripts/split_repos.py
```

Then, once per repo (`police-agent`, then `thief-agent`):

1. On GitHub, create the empty repo with **exactly** the name the config
   declares — `Nell-Kh/police-agent` / `Nell-Kh/thief-agent`. If either name
   must change, change `[game].repos` in BOTH per-peer TOMLs first and re-run
   the split; the tool refuses to build from a lying table.
2. `cd build/<name>` and:

   ```
   git init -b main && git add -A
   git commit -m "initial submission tree"
   git remote add origin https://github.com/Nell-Kh/<name>.git
   git push -u origin main
   git tag v1.0-submission && git push origin v1.0-submission
   ```

3. Prove the published tree stands alone: fresh terminal, `cd build/<name>`,
   `uv sync && uv run pytest -q` — expect the same count as the dev repo.
4. Grant the lecturer access / set visibility (rule #49). Verify from a
   logged-out browser window that the repo is reachable as intended.

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
