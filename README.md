# claude-notifier

A Claude Code hook that fires a desktop notification whenever Claude finishes a task or is waiting for your input — so you can switch away and come back when needed.

Supports **macOS** and **Linux**.

## What it does

- **Done** — notifies when Claude completes a response
- **Waiting** — notifies when Claude needs your input ("should I proceed?", etc.)
- Always notifies by default, even when your terminal is focused
- On macOS: delivered via a native bundled app (`ClaudeNotifier.app`) — appears as a first-class notification with its own entry in System Preferences → Notifications

## Install

**Homebrew (macOS)**
```bash
brew install rezaiyan/tap/claude-notifier
```

**apt (Debian/Ubuntu)**
```bash
sudo apt install claude-notifier
```

**Manual**
```bash
git clone https://github.com/rezaiyan/claude-notifier.git
cd claude-notifier
chmod +x install.sh
./install.sh
```

All install methods:
1. Install system dependencies
2. Place `claude-notifier.py` in the appropriate location
3. Register the `Stop` hook in `~/.claude/settings.json`

## Dependencies

| Platform | Required | Optional |
|---|---|---|
| macOS | — (bundled `ClaudeNotifier.app`) | — |
| Linux | `libnotify-bin` (notify-send) | `xdotool` (focus detection, X11 only) |

On macOS, notifications are delivered by a tiny native app bundled with the formula. It is compiled at bottle-build time — end users download a pre-built bottle and never need Xcode.

## Manual install

If you prefer not to use the installer:

1. Copy `claude-notifier.py` to `~/.claude/hooks/`
2. Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/claude-notifier.py"
          }
        ]
      }
    ]
  }
}
```

## Uninstall

**Homebrew**
```bash
# Remove the settings.json entry first (Homebrew has no uninstall hook)
python3 $(brew --prefix)/opt/claude-notifier/libexec/unpatch-settings.py \
        $(brew --prefix)/opt/claude-notifier/libexec/claude-notifier.py
brew uninstall claude-notifier
```

**apt**
```bash
sudo apt remove claude-notifier   # cleans settings.json automatically via prerm
```

**Manual**
```bash
./uninstall.sh
```

> If the script is removed without running the uninstall step, the hook entry
> in `settings.json` silently no-ops — Claude Code won't break, but running
> the uninstall is the clean way to remove it fully.

## Configuration

By default, notifications always fire. Pass `--skip-if-focused` at install time to suppress them when your terminal is already in the foreground:

**Homebrew / apt** — edit the registered hook in `~/.claude/settings.json` and append the flag:
```json
{ "type": "command", "command": "python3 ~/.claude/hooks/claude-notifier.py --skip-if-focused" }
```

**Manual install**
```bash
./install.sh --skip-if-focused
```

**Re-registering after a manual install**
```bash
python3 scripts/patch-settings.py ~/.claude/hooks/claude-notifier.py --skip-if-focused
```

## Notes

- **Wayland (Linux)**: focus detection is not supported — `CLAUDE_NOTIFIER_SKIP_IF_FOCUSED=1` has no effect
- **X11 without xdotool**: same behaviour as Wayland
- **macOS**: notifications come from `ClaudeNotifier.app` (bundled); falls back to `osascript` for manual/non-Homebrew installs

## License

MIT
