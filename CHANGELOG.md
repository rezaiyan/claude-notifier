# Changelog

All notable changes to claude-notifier are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2026-04-03

## [1.2.7] - 2026-04-03

## [1.2.6] - 2026-04-03

## [1.2.5] - 2026-04-03

## [1.2.4] - 2026-04-03

## [1.2.3] - 2026-04-03

## [1.2.2] - 2026-04-03

### Fixed
- `ClaudeNotifier.app` bottles are now notarized via `xcrun notarytool` and stapled before packaging — macOS 14+ (including macOS 26 / Tahoe) silently returns `granted = false` from `UNUserNotificationCenter.requestAuthorization` for apps that are signed but not notarized, so no permission prompt was ever shown and no notification was ever delivered
- Removed the macOS 26–specific osascript bypass in `claude-notifier.py` (introduced in v1.2.1 as a workaround for the unnotarized state). Now that bottles are notarized, `ClaudeNotifier.app` is used on all macOS versions; osascript is retained as a fallback only for non-Homebrew installs where the binary is absent
- `Formula/claude-notifier.rb`: restore the `claude-notifier` bin wrapper that was dropped during restructuring
- `scripts/bump-version.sh`: update `VERSION` constant in `claude-notifier.py` as part of each release

## [1.2.1] - 2026-04-03

### Fixed
- Restored osascript-as-primary path on macOS 26+ (Tahoe): `tell application "System Events" to display notification` delivers banner notifications without any extra setup. `ClaudeNotifier.app` (v1.2.0) was silently swallowing notifications on macOS 26 because `UNUserNotificationCenter` hard-denies non-notarized apps regardless of signing identity, and the fire-and-forget `Popen` call had no fallback

## [1.2.0] - 2026-04-02

### Fixed
- `claude-notifier.py` now uses `ClaudeNotifier.app` on all macOS versions (including macOS 26 / Tahoe). The macOS 26 osascript-only bypass was introduced for ad-hoc signed apps that were hard-denied by the OS; now that Homebrew bottles are signed with a Developer ID Application certificate (`TeamIdentifier=VFCFJC7Y5J`), `UNUserNotificationCenter` can prompt for permission and deliver notifications as proper banners. osascript is retained as a fallback for non-Homebrew / local-build installs where no Developer ID cert is present

## [1.1.9] - 2026-04-03

### Fixed
- Re-added Developer ID Application signing step to bottles workflow (removed in v1.1.7 because the `APPLE_IDENTITY` secret held the wrong cert type). Now validates that the imported cert is `Developer ID Application` — not `Apple Development` — and fails the build early if the wrong type is used. Signing uses `--options runtime` for notarization compatibility

## [1.1.8] - 2026-04-02

### Fixed
- macOS 26 (Tahoe) hard-denies `UNUserNotificationCenter` for ad-hoc signed apps with no user-visible prompt (`UNErrorDomain Code=1`). `claude-notifier.py` now detects macOS 26+ via `platform.mac_ver()` and uses `osascript` via System Events as the primary notification path — zero setup required. ClaudeNotifier.app is still used on macOS 25 and earlier where `UNUserNotificationCenter` works with proper signing
- `setActivationPolicy(.prohibited)` was called before `requestAuthorization` in `main.swift`, which had the same effect as `LSUIElement=true`. Now checks `getNotificationSettings` first: hides from Dock immediately if permission already determined, stays visible if `notDetermined` so the OS can show the prompt (for future use with a Developer ID cert)
- Smoke test now detects macOS version and tests the correct notification path per OS

## [1.1.7] - 2026-04-02

### Fixed
- Removed Developer ID re-signing step from bottles workflow — the `APPLE_IDENTITY` secret held an Apple Development cert (device-only, Gatekeeper-rejected) instead of a Developer ID Application cert, preventing `UNUserNotificationCenter` from registering the app. Homebrew bottles now ship with the formula's existing ad-hoc signature (`codesign --sign "-"`), which is sufficient since Homebrew strips the quarantine bit on install
- Formula caveats now say "after install **or upgrade**" to prompt users to re-run `claude-notifier-setup` so stale hooks are cleaned up

## [1.1.6] - 2026-04-02

### Fixed
- Remove `LSUIElement = true` from `Info.plist` — macOS 26 (Tahoe) silently skips the notification permission dialog for Info.plist-declared background agents; removing it lets macOS treat the app as a regular app and show the prompt automatically on first run. Runtime invisibility is preserved by `NSApp.setActivationPolicy(.prohibited)` in code (same behaviour as before, different classification at OS level)

## [1.1.5] - 2026-04-02

### Fixed
- `ClaudeNotifier.app` no longer exits before handing off the notification: removed early termination on `!granted` (macOS 26 silently denies LSUIElement agents on first run without showing a prompt, then registers them in `com.apple.ncprefs` on the next attempt) and added a `DispatchSemaphore` to block exit until `center.add(request)` callback fires
- `claude-notifier-setup` (`patch-settings.py`) now removes hooks from previous version paths before inserting the current one — prevents duplicate hooks after a Homebrew upgrade
- `unpatch-settings.py` now matches hooks by `claude-notifier.py` substring rather than exact path, so it correctly removes hooks installed by any prior version

## [1.1.4] - 2026-04-02

### Fixed
- osascript fallback now delegates to `System Events` first (`tell application "System Events" to display notification`) — fixes macOS 26 (Tahoe) error `-2740` where top-level `display notification` is blocked; bare form retained as a fallback for older macOS
- `~/.claude/hooks/claude-notifier.py` synced to v1.1.3 source (removed stale terminal-notifier path)

### Changed
- Bottles workflow now signs `ClaudeNotifier.app` with a Developer ID Application certificate (from GitHub Actions secrets `APPLE_CERTIFICATE_P12`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_IDENTITY`) before bottling — embeds TeamIdentifier so macOS can persist notification permissions for the bundle ID

## [1.1.3] - 2026-04-02

### Fixed
- Release workflow: use `gh workflow run` dispatch instead of `workflow_call` to trigger bottles — avoids `contents: write` permission propagation issue with reusable workflows

## [1.1.2] - 2026-04-02

### Fixed
- Bottle filename: rename `name--version.tag.bottle.N.tar.gz` → `name-version.tag.bottle.tar.gz` at upload time to match what Homebrew expects when fetching
- Bottles now build and publish automatically on every release via `workflow_call` chain in `release.yml` — no manual trigger needed

## [1.1.1] - 2026-04-02

### Fixed
- Homebrew bottles workflow: inject `root_url` into bottle stanza so Homebrew fetches from GitHub Releases instead of defaulting to `ghcr.io`
- Homebrew bottles workflow: correct tap repo URL, artifact download path, and bottle filename glob (`*.bottle.N.tar.gz`)
- Removed unsupported `macos-13` runner from bottles matrix

## [1.1.0] - 2026-04-02

### Added
- `Sources/ClaudeNotifier/main.swift` + `Info.plist`: self-owned native macOS app bundle (`ClaudeNotifier.app`) delivering notifications via `UNUserNotificationCenter` with bundle ID `io.github.rezaiyan.claude-notifier`; appears as a first-class entry in System Preferences → Notifications
- `.github/workflows/bottles.yml`: automated Homebrew bottle builds for `arm64_sequoia`, `arm64_sonoma`, and `ventura`; bottles uploaded to the GitHub release and SHA256 stanzas injected into the tap formula automatically

### Changed
- Homebrew formula compiles the Swift helper and assembles the `.app` bundle at install time (ad-hoc signed; no Team ID or personal credentials in source); removed `depends_on "terminal-notifier"`
- `claude-notifier.py`: macOS notification path uses the bundled `ClaudeNotifier.app` (fire-and-forget), falls back to `osascript` for non-Homebrew installs
- `install.sh`: removed terminal-notifier install step on macOS

## [1.0.9] - 2026-04-02

### Changed
- Removed LaunchAgent-based sandbox-escape attempts from `post_install` (both `launchctl bootstrap` and `launchctl load` are blocked or silently inert under Homebrew's sandbox); reverted to clean, minimal caveats with a single `claude-notifier-setup` command

## [1.0.8] - 2026-04-02

### Fixed
- Switch `launchctl bootstrap` to `launchctl load -w` in `post_install`; the legacy Mach IPC path used by `load` is reachable from within Homebrew's sandbox, whereas XPC (used by `bootstrap`) is blocked

## [1.0.7] - 2026-04-02

### Changed
- Homebrew `post_install` now bootstraps a one-shot LaunchAgent to run `claude-notifier-setup` outside the sandbox, so `brew install` registers the hook automatically without any manual step
- `claude-notifier-setup` cleans up the LaunchAgent plist after it runs and suppresses the success box when not running in an interactive terminal
- Caveats now show three states: registered (success), plist pending (background registration in progress), or manual fallback

## [1.0.6] - 2026-04-02

### Changed
- Homebrew formula now attempts to register the hook automatically in `post_install`; `claude-notifier-setup` is only needed as a fallback if Homebrew's sandbox blocks the write
- Caveats are dynamic: show a success message when the hook is already registered, or the setup instruction when it is not

## [1.0.5] - 2026-04-02

### Added
- `--skip-if-focused` flag: pass at install time (`./install.sh --skip-if-focused`) or append to the hook command in `settings.json` to suppress notifications when the terminal is already focused (default: always notify)

### Fixed
- Hook command and guard string now quote the script path, preventing breakage when `$HOME` contains spaces
- `subprocess.run` calls for focus detection now have a 3-second timeout, preventing the hook from hanging if `osascript` or `xdotool` stalls
- `extract-changelog.py` now resolves `CHANGELOG.md` relative to the script, not the working directory
- `unpatch-settings.py` skips writing `settings.json` when no matching hook entry is found
- Removed `"confirm"` from waiting-signal list to eliminate false "Waiting" notifications
- `debian/postinst`: `su` now uses `-s /bin/sh` for portability on restricted-shell systems

## [1.0.4] - 2026-03-29

### Changed
- Homebrew caveats redesigned with a prominent box and clear setup instruction
- `claude-notifier-setup` now prints the same colorful success box as `install.sh`

## [1.0.3] - 2026-03-29

### Fixed
- Homebrew deploy workflow now copies the full formula from source before
  substituting url/sha256/version, so structural changes are always reflected

## [1.0.2] - 2026-03-29

### Fixed
- Homebrew `post_install` sandbox blocks writes to `~/.claude/settings.json`;
  replaced with `claude-notifier-setup` / `claude-notifier-teardown` bin commands
  that run in the user's shell context

## [1.0.1] - 2026-03-29

## [1.0.0] - 2026-03-29

### Added
- macOS notifications via `terminal-notifier` with `osascript` fallback
- Linux notifications via `notify-send`
- Focus detection: skips notification when terminal is already in the foreground
- Detects iTerm2, Warp, Ghostty, Alacritty, kitty via environment variables (macOS)
- X11 focus detection via `xdotool`; graceful no-op on Wayland
- `install.sh` — installs deps, copies script, patches `~/.claude/settings.json`
- `uninstall.sh` — removes script and cleans `settings.json`
- Homebrew formula (`Formula/claude-notifier.rb`)
- Debian package structure (`debian/`) with `postinst`/`prerm` maintainer scripts
- Hook command guarded against orphaned entries after package manager removal
