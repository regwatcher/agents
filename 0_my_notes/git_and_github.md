# Git and GitHub — this clone vs Ed Donner's repo

Snapshot from 13 Sep 2026. Local clone: `/Users/olivierdedecker/Development/agents`.

Original course repo: [ed-donner/agents](https://github.com/ed-donner/agents).

---

## Are we behind the original repo?

**No.** Local `main` matched Ed's `main` exactly.

| What | SHA / date |
|---|---|
| Local `main` | `0dba44fc` — merge of PR #1609 (playwright diagnostic middleware) |
| Cached `origin/main` | same commit |
| Live GitHub `main` | same commit, last push **10 Sep 2026** |

There were **no committed local changes**. Everything added locally was still **untracked**:

- `0_my_notes/` — personal notes / recruitment experiment
- `.agents/`, `.cursor/`, `skills-lock.json` — local tooling
- `1_foundations/5_extra_smart_cook.ipynb`
- `2_openai/community_contributions/oddc_mail_merge.ipynb` — contribution candidate
- `3_crewai/coursework/` — CrewAI exercises

`git pull` on `main` should stay safe as long as Ed does not add files with those same paths.

**Auth (updated later the same day):** `gh` is logged in as **`olivierdd`** with a valid token. That user is an **admin** of the [regwatcher](https://github.com/regwatcher) org. No extra `gh auth login` is needed to use the org.

---

## How to manage local changes (which branch)

Keep **`main` as a clean mirror of Ed’s repo**. Do not commit personal work there.

Use two kinds of branches:

| Branch | What goes there | Push to GitHub? |
|---|---|---|
| `main` | Only upstream. `git pull` here. | Never commit local work |
| `local/notes` (or similar) | `0_my_notes/`, extra notebooks, coursework, Cursor/agent files | Optional backup on **your** fork |
| `contrib/oddc-mail-merge` (topic branch) | Only the files for a PR | Yes, then open a PR |

Practical rules:

1. Leave `main` alone except for `git pull`.
2. Put day-to-day work on `local/notes`.
3. For a PR, branch from a fresh `main`, copy **only** the contribution files, commit those.
4. Do **not** include `.agents/`, `.cursor/`, `0_my_notes/`, or the full `3_crewai/coursework/` trees in a PR. Ed asks for concise work under `community_contributions/`.

Notes can stay untracked on `main` if preferred; a dedicated branch is just easier to backup.

---

## Do we have a copy on GitHub?

**Yes — under the org, not under `olivierdd`.**

- GitHub user: [olivierdd](https://github.com/olivierdd) (what `gh` logs into)
- Org: [regwatcher](https://github.com/regwatcher) (`olivierdd` is admin)
- Fork: [regwatcher/agents](https://github.com/regwatcher/agents) (fork of `ed-donner/agents`)

This local folder’s **git remote is still the original**, so pushes would still go to Ed (and fail):

```
origin  https://github.com/ed-donner/agents.git  (fetch and push)
```

The org fork last pushed **28 May 2026**, so it is **behind** both this local clone and Ed’s current `main` (10 Sep 2026).

There is no `olivierdd/agents` personal fork. That is fine — use the org fork.

---

## How to authenticate (`gh auth login`)

You log in as a **user**, not as the org. `regwatcher` cannot be an `gh` account.

Current status: already logged in as `olivierdd`, with `repo`, `read:org`, `gist`, `workflow` scopes, and admin access to `regwatcher/agents`.

Only run this if the token breaks again, or you need to add a *different personal user*:

```bash
gh auth login --hostname github.com --git-protocol https --web
```

In the browser, sign in as **olivierdd** (the user that belongs to the org). Then `gh auth status` should still show `olivierdd`, and `gh api user/orgs` should list `regwatcher`.

---

## How to sync this clone to GitHub

The fork already exists. Point this clone at it for pushes; keep Ed as **upstream**.

```bash
# 1. Remotes: origin = org fork, upstream = Ed
git remote rename origin upstream
git remote add origin https://github.com/regwatcher/agents.git

# 2. Backup a local-notes branch (optional)
git checkout -b local/notes
git add 0_my_notes 3_crewai/coursework 1_foundations/5_extra_smart_cook.ipynb
# skip .env / secrets if any appear later
git commit -m "Local notes and coursework (not for upstream PR)"
git push -u origin local/notes

# 3. Keep main tracking Ed, then update the fork
git checkout main
git pull upstream main
git push origin main
```

Ongoing sync from Ed:

```bash
git checkout main
git fetch upstream
git merge upstream/main   # or: git pull upstream main
git push origin main      # update regwatcher/agents main
```

---

## How to open a PR against the original repo

Standard **fork → topic branch → PR**. Course PRs belong under `*/community_contributions/`. The mail-merge notebook is already in the right place: `2_openai/community_contributions/oddc_mail_merge.ipynb`.

```bash
git checkout main
git pull upstream main

git checkout -b contrib/oddc-mail-merge
git add 2_openai/community_contributions/oddc_mail_merge.ipynb
git commit -m "Add oddc mail merge community contribution"
git push -u origin contrib/oddc-mail-merge

gh pr create --repo ed-donner/agents \
  --base main \
  --head regwatcher:contrib/oddc-mail-merge \
  --title "Community contribution: oddc mail merge" \
  --body "Adds a mail-merge / campaign notebook under 2_openai/community_contributions."
```

GitHub’s UI does the same: fork → push branch → “Open pull request” into `ed-donner/agents`.

Keep the PR small. Coursework crews and `0_my_notes/` should stay on `local/notes`, not in that PR.

---

## Summary

- Current with Ed’s `main` as of 13 Sep 2026.
- `gh` is logged in as `olivierdd`, admin of org `regwatcher`.
- GitHub copy already exists: [regwatcher/agents](https://github.com/regwatcher/agents) (behind Ed; local remotes still point at Ed).
- Keep `main` clean, use `local/notes` for personal work, open PRs from small `contrib/...` branches via the org fork.
