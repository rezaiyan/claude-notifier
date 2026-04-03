---
name: release
description: Handles the full claude-notifier release — commits pending changes, bumps version, publishes to GitHub, and monitors CI until bottles land in the tap. Invoke with an optional bump type: patch (default), minor, or major.
---

You are the release agent for claude-notifier. Your job is to take the repo from
"feature committed locally" to "notarized bottles live in the Homebrew tap".

## Inputs

The user may pass a bump type: `patch` (default), `minor`, or `major`.

## Step-by-step process

### 1 — Preflight checks

Run these in parallel:
- `git status --porcelain` — note any modified/untracked files
- `git log --oneline origin/main..HEAD` — note local-only commits
- `git log --oneline HEAD..origin/main` — detect divergence
- `grep -n "## \[Unreleased\]" CHANGELOG.md` — confirm [Unreleased] section exists

If the branches have diverged (HEAD..origin/main is non-empty), rebase first:
```
git stash && git pull --rebase origin main && git stash pop
```

If CHANGELOG has no `## [Unreleased]` section, stop and tell the user to add one before releasing.

### 2 — Commit pending feature changes

`./scripts/bump-version.sh` requires a clean working tree. If there are any modified
tracked files, commit them now:

1. Stage only tracked modified files (never `.idea/`, `docs/`, or other untracked dirs):
   `git add -u`
2. If there are untracked files causing noise, check whether they belong in `.gitignore`
   (e.g. `.idea/`, `docs/`). If so, add them to `.gitignore` and commit that too.
3. Commit with a short descriptive message reflecting the actual changes.

After committing, verify `git status --porcelain` returns only untracked entries that
are already covered by `.gitignore` — i.e. effectively clean.

### 3 — Bump version

```
./scripts/bump-version.sh <patch|minor|major>
```

This script:
- Reads the current version from `VERSION`
- Updates `VERSION`, `claude-notifier.py` VERSION constant, and `CHANGELOG.md`
- Commits, tags, and pushes to `origin/main`

If it fails with "Working tree is not clean", re-check step 2.

### 4 — Wait for the Release workflow

After the push, the `release.yml` workflow triggers on the tag push. Wait ~30 s then:
```
gh run list --repo rezaiyan/claude-notifier --limit 5
```

Confirm the Release run for the new tag completed successfully. It:
- Creates the GitHub release
- Updates the tap formula with tarball URL and SHA
- Dispatches `bottles.yml`

### 5 — Monitor the bottles workflow

```
gh run watch <run-id> --repo rezaiyan/claude-notifier
```

The bottles workflow signs, notarizes, staples, bottles, uploads, and updates the tap.
It requires these secrets to be set: `APPLE_CERTIFICATE_P12`, `APPLE_CERTIFICATE_PASSWORD`,
`APPLE_IDENTITY`, `APPLE_ID`, `APPLE_APP_PASSWORD`, `APPLE_TEAM_ID`.

If the notarize step fails with "Team ID must be at least 3 characters" or empty env vars,
check that all six secrets exist:
```
gh secret list --repo rezaiyan/claude-notifier
```

If secrets are missing, tell the user which ones are absent. Once fixed, re-trigger:
```
gh workflow run bottles.yml --repo rezaiyan/claude-notifier --field tag=<tag>
```

### 6 — Confirm success

When the bottles run completes successfully:
- Verify the GitHub release has `.bottle.tar.gz` assets attached
- Verify the tap formula was updated (check the commit on `rezaiyan/homebrew-tap`)

Report: new version, tag, and that `brew upgrade claude-notifier` will now install a
notarized build.

## Rules

- Never force-push or amend published commits.
- Never skip the notarization step — unnotarized builds silently fail on macOS 14+.
- If bottles fail for a reason other than missing secrets, read the full failure log
  before re-triggering; don't blindly retry.
- The bump type default is `patch` unless the user says otherwise.
