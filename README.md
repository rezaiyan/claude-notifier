# claude-notifier

A Claude Code hook that fires a desktop notification whenever Claude finishes a task or is waiting for your input — so you can switch away and come back when needed.

Supports **macOS** and **Linux**.

## What it does

- **Done** — notifies when Claude completes a response
- **Waiting** — notifies when Claude needs your input ("should I proceed?", "confirm", etc.)
- Skips the notification if your terminal is already focused (no noise when you're watching)
- On macOS: clicking the notification brings your terminal back into focus

## Install

```bash
git clone https://github.com/alirezaiyan/claude-notifier.git
cd claude-notifier
chmod +x install.sh
./install.sh
```

The installer:
1. Installs system dependencies
2. Copies `claude-notifier.py` to `~/.claude/hooks/`
3. Registers the `Stop` hook in `~/.claude/settings.json`

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

```bash
./uninstall.sh
```

Removes the script from `~/.claude/hooks/` and cleans up `settings.json`.

> **Package managers (brew, apt, etc.)** do not touch `~/.claude/settings.json`.
> Always run `uninstall.sh` before or after removing via a package manager,
> otherwise the hook entry will remain. If the script is already gone the
> registered command fails silently, so Claude Code won't break — but running
> `uninstall.sh` is the clean way to remove it fully.

## Notes

- **Wayland (Linux)**: focus detection is not supported — notifications always fire
- **X11 without xdotool**: same behaviour as Wayland
- **No terminal-notifier (macOS)**: falls back to `osascript display notification` (no click-to-focus)

## License

MIT
