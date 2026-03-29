# Changelog

All notable changes to claude-notifier are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
