# claude-notifier

A Claude Code hook that fires a desktop notification whenever Claude finishes a task or is waiting for your input — so you can switch away and come back when needed.

Supports **macOS** and **Linux**.

## What it does

- **Done** — notifies when Claude completes a response
- **Waiting** — notifies when Claude needs your input ("should I proceed?", "confirm", etc.)
- Skips the notification if your terminal is already focused (no noise when you're watching)
- On macOS: clicking the notification brings your terminal back into focus

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
| macOS | — (osascript built-in) | `terminal-notifier` (click-to-focus) |
| Linux | `libnotify-bin` (notify-send) | `xdotool` (focus detection, X11 only) |

The installer handles these automatically. On macOS, `terminal-notifier` is installed via Homebrew if available.

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
python3 $(brew --prefix)/lib/claude-notifier/unpatch-settings.py \
        $(brew --prefix)/lib/claude-notifier/claude-notifier.py
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

## Notes

- **Wayland (Linux)**: focus detection is not supported — notifications always fire
- **X11 without xdotool**: same behaviour as Wayland
- **No terminal-notifier (macOS)**: falls back to `osascript display notification` (no click-to-focus)

## License

MIT
