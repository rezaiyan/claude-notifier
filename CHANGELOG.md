# Changelog

All notable changes to claude-notifier are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
