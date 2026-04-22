---
name: release
description: Full release workflow for claude-notifier — preflight checks, commit pending changes, bump version, tag, push, monitor CI until Homebrew bottles land in the tap.
version: 1.0.0
---

# Release — claude-notifier Full Release Workflow

Handles everything from a dirty working tree to notarized Homebrew bottles published.

## Usage

```
/release          # patch bump (default)
/release minor    # minor bump
/release major    # major bump
/release v1.2.3   # explicit version
```

## Steps

### 1. Preflight checks

Run in parallel:

```bash
git status --porcelain
git log --oneline origin/main..HEAD
git log --oneline HEAD..origin/main
grep -n "## \[Unreleased\]" CHANGELOG.md
```

**If diverged:**
```bash
git pull --rebase origin main
```

**If no `## [Unreleased]`** → stop. Tell user to add entries first.

### 2. Commit pending changes

If there are modified tracked files:

1. `git add -u`
2. If untracked files need ignoring → add to `.gitignore` and commit.
3. Commit with a short descriptive message.

Verify `git status --porcelain` is effectively clean. Skip if already clean.

### 3. Show release plan

Read current version from `VERSION`. Calculate new version from bump type.
If no argument given, ask: `"Bump type? [patch / minor / major / vX.Y.Z]"` and wait.

Show and ask `"Proceed? [Y/n]"`:

```
Release plan for vNEW:
  • VERSION                     OLD → NEW
  • claude-notifier.py          VERSION = "OLD" → "NEW"
  • .claude-plugin/plugin.json  version: OLD → NEW
  • CHANGELOG.md  [Unreleased] → [NEW] - YYYY-MM-DD
  • git commit "chore: release vNEW"
  • git tag vNEW
  • git push origin main --tags
```

Wait for explicit `Y`.

### 4. Bump version

```bash
./scripts/bump-version.sh <bump-type>
```

Updates `VERSION`, `claude-notifier.py`, `plugin.json`, `CHANGELOG.md`, commits, tags, pushes.

### 5. Wait for Release workflow

After push, the `release.yml` workflow triggers on the tag. Wait ~30s then:

```bash
gh run list --repo rezaiyan/claude-notifier --limit 5
```

Confirm the Release run for the new tag completed. It creates the GitHub release,
updates the tap formula with tarball URL and SHA, and dispatches `bottles.yml`.

### 6. Monitor bottles workflow

```bash
gh run watch <run-id> --repo rezaiyan/claude-notifier
```

The bottles workflow signs, notarizes, staples, bottles, uploads, and updates the tap.
Required secrets: `APPLE_CERTIFICATE_P12`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_IDENTITY`,
`APPLE_ID`, `APPLE_APP_PASSWORD`, `APPLE_TEAM_ID`.

If notarize step fails with empty env vars → check secrets:
```bash
gh secret list --repo rezaiyan/claude-notifier
```

If secrets are missing, report which ones. Once fixed, re-trigger:
```bash
gh workflow run bottles.yml --repo rezaiyan/claude-notifier --field tag=vNEW
```

### 7. Confirm success

When bottles run completes:
- Verify GitHub release has `.bottle.tar.gz` assets attached
- Verify tap formula updated (check commit on `rezaiyan/homebrew-tap`)

Report:
```
Released vNEW
  tag      vNEW
  bottles  ✓ notarized
  tap      rezaiyan/homebrew-tap updated

brew upgrade claude-notifier  # installs notarized build
```

## Error Handling

| Failure | Action |
|---------|--------|
| No `[Unreleased]` in CHANGELOG | Stop — ask user to add entries first |
| User says N at plan confirmation | Stop — nothing written |
| `bump-version.sh` fails "not clean" | Re-run step 2 |
| `git push` fails | Report — commit + tag exist locally |
| Bottles fail (non-secrets reason) | Read full failure log before re-triggering |
| Missing secrets | List absent ones, wait for user to add, then re-trigger |

## Rules

- Never force-push or amend published commits.
- Never skip notarization — unnotarized builds silently fail on macOS 14+.
- Don't blindly retry bottles failure — read the log first.
