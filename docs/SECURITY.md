# SECURITY — secrets, rotation, and what the suite enforces

Rules #39/#40 forbid committing credentials. This repository never has: a sweep
of every tree in every reachable commit finds no `.env`, `credentials.json` or
`token.json`, and `tests/unit/test_secrets_hygiene.py` now re-runs that sweep on
every test run so the claim stays a fact rather than a memory.

The exposure that *does* exist is **at rest**, not in git.

---

## 1. What this project actually needs

Exactly one environment variable, and two files:

| Secret | Read by | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | `infra/llm/claude_api.py` | Optional. With `[trash_talk] provider = "template"` (the zero-token default) the whole series plays without it, and the paid chain falls back to templates when it is absent. |
| `credentials.json` | `infra/email/oauth.py` | The OAuth *client* downloaded from Google Cloud Console. For an installed/desktop app Google does not treat the client secret as confidential, but it identifies the project. |
| `token.json` | `infra/email/oauth.py` | Minted on first consent. **The most sensitive file in the checkout**: it carries a refresh token, which does not expire and grants `gmail.send` as the account owner until explicitly revoked. |

Scope is `gmail.send` only — rule #30, pinned by `test_email_oauth.py`.

Anything else in `.env` is liability with no upside. It cannot help; it can only
leak. The hygiene suite fails while an unread variable is present.

## 2. Rotating

Order matters: **revoke at the provider first, then delete locally.** Deleting
first only removes your own ability to identify which credential to revoke.

### `token.json` — do this one first
The refresh token is the only credential here that grants access to a *person's*
account rather than a metered API.

1. https://myaccount.google.com/permissions → find the app → **Remove access**.
   This invalidates the refresh token immediately, everywhere.
2. Delete `token.json` locally.
3. Re-consent on the next run; a fresh `token.json` is written automatically.

### `credentials.json`
Only if you believe the client was exposed publicly (it has never been in git):
Google Cloud Console → APIs & Services → Credentials → the OAuth 2.0 Client ID →
**Reset secret**, download, replace the file.

### `ANTHROPIC_API_KEY`
https://console.anthropic.com/settings/keys → revoke the old key → create a new
one → update `.env`. Check **Usage** for spend you do not recognise first.

### Anything else you find in `.env`
Revoke at its own provider, then delete the line. Common ones and where:

| Prefix | Provider | Revoke at |
|---|---|---|
| `sk-proj-…`, `sk-…` | OpenAI | https://platform.openai.com/api-keys |
| `rnd_…` | Render | https://dashboard.render.com/u/settings#api-keys |
| a 16-character Google app password | Google | https://myaccount.google.com/apppasswords |
| `ghp_…`, `github_pat_…` | GitHub | https://github.com/settings/tokens |

A Google **app password** deserves special mention: it bypasses two-factor
authentication and grants far more than sending mail. This project has never
needed one — Gmail access is OAuth, scoped to `gmail.send`. If one exists,
revoke it rather than keeping it "just in case".

## 3. Storage location

A checkout under a synced folder (OneDrive, Dropbox, iCloud Drive) puts every
git-ignored secret into a third party's cloud. `.gitignore` has no bearing on
this whatsoever — the sync client copies the file regardless.

Either keep the working copy outside the synced tree (`C:\dev\…` rather than
`…\OneDrive\Desktop\…`), or exclude the folder in the sync client:
OneDrive → Settings → Account → **Choose folders**, and untick it.

## 4. What the suite enforces

`tests/unit/test_secrets_hygiene.py`, seven checks:

1. `.gitignore` still names `.env`, `credentials.json`, `token.json`, `*.pem`, `*.key`.
2. Those files, where they exist, are genuinely ignored (behaviour, not rule text).
3. None of them is tracked.
4. No tracked file *contains* live-credential material — catching the paste into
   a docstring, a notebook cell or a test fixture. The scanner matches issuer
   prefixes rather than entropy, so it does not fire on this project's many
   hex digests.
5. `.env-example` documents without disclosing; its placeholders deliberately
   avoid real issuer prefixes so a template cannot be mistaken for a key.
6. No secret file appears anywhere in the reachable history.
7. `.env`, if present, declares nothing the code does not read.

Check 7 is the one that goes red first, and it is meant to: an unread secret is
a secret nobody is watching.

## 5. If a secret is ever committed

Treat it as public the moment it lands, even in a private repository, even if
the next commit removes it — it stays in the history and in every clone.

1. **Revoke it.** Immediately, before anything else. Rewriting history without
   revoking accomplishes nothing.
2. Then, optionally, purge the history (`git filter-repo`, or BFG) and
   force-push, telling every collaborator to re-clone.

Step 1 is the one that matters. Step 2 is tidying.
