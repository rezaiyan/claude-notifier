# claude-notifier

A Claude Code hook that fires a desktop notification whenever Claude finishes a task or is waiting for your input — so you can switch away and come back when needed.

Supports **macOS** and **Linux**.

## What it does

- **Done** — notifies when Claude completes a response
- **Waiting** — notifies when Claude needs your input ("should I proceed?", etc.)
- Always notifies by default, even when your terminal is focused
- On macOS: delivered via a native bundled app (`ClaudeNotifier.app`) — appears as a first-class notification with its own entry in System Preferences → Notifications

## Install

### Claude Code plugin (macOS + Linux, quickest)

```bash
# Add the marketplace (once)
claude plugin marketplace add rezaiyan/claude-plugins

# Install
claude plugin install claude-notifier@rezaiyan
```

Uses `osascript` on macOS — no native app required, works everywhere. For a first-class entry in System Settings → Notifications, use Homebrew instead.

### Homebrew (macOS, best notification experience)

```bash
brew install rezaiyan/tap/claude-notifier
claude-notifier-setup
```

Bundles the notarized `ClaudeNotifier.app` — notifications appear under "Claude Notifier" in System Settings.

### apt (Debian/Ubuntu)

```bash
sudo apt install claude-notifier
```

### Manual

```bash
git clone https://github.com/rezaiyan/claude-notifier.git
cd claude-notifier
./install.sh
```

## Managed Macs (allowManagedHooksOnly)

Some enterprise environments set `allowManagedHooksOnly: true` in Claude Code's managed settings, which silently blocks all user-defined hooks. `claude-notifier-setup` detects this automatically and installs a **launchd session-log watcher** daemon instead — no hook required. Notifications work identically either way.

## Dependencies

| Platform | Required                        | Optional                              |
| -------- | ------------------------------- | ------------------------------------- |
| macOS    | — (bundled `ClaudeNotifier.app`) | —                                    |
| Linux    | `libnotify-bin` (notify-send)   | `xdotool` (focus detection, X11 only) |

On macOS, notifications are delivered by a tiny native app bundled with the formula. It is compiled at bottle-build time — end users download a pre-built bottle and never need Xcode.

## Status

Run `claude-notifier` (no arguments) to check whether the hook or daemon is active:

```
claude-notifier v1.2.6  [macOS]

  ✓  Hook registered
     /opt/homebrew/opt/claude-notifier/libexec/claude-notifier.py

  Test delivery:  claude-notifier --test
  To remove:      claude-notifier uninstall
```

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
claude-notifier uninstall
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

---

## More Claude tools by rezaiyan

| Plugin | Description | Install |
|--------|-------------|---------|
| [claude-token-guard](https://github.com/rezaiyan/claude-token-guard) | Cut token burn — blocks expensive agents, rewrites verbose Bash commands | `claude plugin install claude-token-guard@rezaiyan` |
| [skillfetch](https://github.com/rezaiyan/skillfetch) | Sync AI skill instructions from GitHub repos — security-scanned, diff-previewed | `claude plugin install skillfetch@rezaiyan` |
| [claude-session-manager](https://github.com/rezaiyan/claude-session-manager) | Desktop app for running multiple Claude Code sessions side by side | — |
