#!/usr/bin/env python3
"""Register claude-notifier in ~/.claude/settings.json.

Usage: python3 patch-settings.py <absolute-path-to-claude-notifier.py>
       [--watcher <absolute-path-to-log-watcher.py>] [extra hook args...]
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── Argument parsing ──────────────────────────────────────────────────────────

def _parse_args() -> tuple[str, str | None, list[str]]:
    """Return (notifier_path, watcher_path_or_None, extra_hook_args)."""
    args = sys.argv[1:]
    if not args:
        print("Usage: patch-settings.py <path-to-claude-notifier.py> [--watcher <path>] [args...]",
              file=sys.stderr)
        sys.exit(1)

    notifier_path = args[0]
    watcher_path: str | None = None
    extra: list[str] = []

    i = 1
    while i < len(args):
        if args[i] == "--watcher" and i + 1 < len(args):
            watcher_path = args[i + 1]
            i += 2
        else:
            extra.append(args[i])
            i += 1

    return notifier_path, watcher_path, extra


# ── Daemon management (macOS only) ────────────────────────────────────────────

DAEMON_LABEL = "com.claude-notifier.log-watcher"
DAEMON_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{DAEMON_LABEL}.plist"


def _daemon_is_loaded() -> bool:
    result = subprocess.run(
        ["launchctl", "list", DAEMON_LABEL],
        capture_output=True,
    )
    return result.returncode == 0


def _unload_daemon() -> None:
    if _daemon_is_loaded():
        uid = os.getuid()
        subprocess.run(
            ["launchctl", "bootout", f"gui/{uid}/{DAEMON_LABEL}"],
            capture_output=True,
        )


def _install_daemon(notifier_path: str, watcher_path: str) -> None:
    """Write the launchd plist and bootstrap the daemon."""
    python3 = shutil.which("python3") or "/usr/bin/python3"
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{DAEMON_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python3}</string>
        <string>{watcher_path}</string>
        <string>{notifier_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/claude-notifier-watcher.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-notifier-watcher.log</string>
</dict>
</plist>
"""
    DAEMON_PLIST.parent.mkdir(parents=True, exist_ok=True)

    # Reload if already running (picks up path changes on upgrade)
    _unload_daemon()

    DAEMON_PLIST.write_text(plist)
    uid = os.getuid()
    result = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(DAEMON_PLIST)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"[claude-notifier] Warning: could not start daemon: {result.stderr.strip()}",
            file=sys.stderr,
        )
    else:
        print("[claude-notifier] Log-watcher daemon installed and started.")


def _remove_daemon_if_present() -> None:
    """Unload and delete the daemon plist if it exists."""
    loaded = _daemon_is_loaded()
    exists = DAEMON_PLIST.exists()
    if not loaded and not exists:
        return
    _unload_daemon()
    if exists:
        DAEMON_PLIST.unlink()
        print(f"[claude-notifier] Removed daemon plist {DAEMON_PLIST}")


# ── Hook management ───────────────────────────────────────────────────────────

def _register_hook(settings_path: Path, hook_path: str, extra_args: list[str]) -> None:
    extra = (" " + " ".join(extra_args)) if extra_args else ""
    hook_command = f'python3 "{hook_path}"{extra}'
    guarded = f'[ -f "{hook_path}" ] && {hook_command} || true'

    try:
        data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        if not isinstance(data, dict):
            data = {}
    except json.JSONDecodeError:
        print(
            f"[claude-notifier] Warning: {settings_path} contains invalid JSON"
            " — creating backup and starting fresh.",
            file=sys.stderr,
        )
        settings_path.rename(settings_path.with_suffix(".json.bak"))
        data = {}

    data.setdefault("hooks", {}).setdefault("Stop", [{}])
    data["hooks"]["Stop"][0].setdefault("hooks", [])
    hooks = data["hooks"]["Stop"][0]["hooks"]

    stale = [
        h for h in hooks
        if "claude-notifier.py" in h.get("command", "") and h.get("command") != guarded
    ]
    already_current = any(h.get("command") == guarded for h in hooks)

    if not stale and already_current:
        print("[claude-notifier] Hook already registered.")
        return

    hooks[:] = [h for h in hooks if "claude-notifier.py" not in h.get("command", "")]
    hooks.append({"type": "command", "command": guarded})
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    if stale:
        print(f"[claude-notifier] Updated hook in {settings_path} (removed {len(stale)} stale entry)")
    else:
        print(f"[claude-notifier] Registered hook in {settings_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    notifier_path, watcher_path, extra_args = _parse_args()
    settings_path = Path.home() / ".claude" / "settings.json"

    # Read current settings (best-effort; errors handled in _register_hook)
    managed_only = False
    try:
        if settings_path.exists():
            data = json.loads(settings_path.read_text())
            if isinstance(data, dict):
                managed_only = bool(data.get("allowManagedHooksOnly", False))
    except (json.JSONDecodeError, OSError):
        pass

    if managed_only:
        if watcher_path:
            # Hooks are blocked by policy — install the session-log watcher daemon instead.
            print(
                "[claude-notifier] allowManagedHooksOnly detected — installing log-watcher daemon.",
            )
            _install_daemon(notifier_path, watcher_path)
        else:
            # No watcher available (e.g. manual install without the script).
            print(
                "[claude-notifier] WARNING: allowManagedHooksOnly is enabled in settings.json.\n"
                "  User hooks are blocked by policy — notifications will not fire even after setup.\n"
                "  Ask your admin to allow user hooks, or watch the session log instead.",
                file=sys.stderr,
            )
        return

    # Normal path: hooks are allowed — remove any leftover daemon and register the hook.
    _remove_daemon_if_present()
    _register_hook(settings_path, notifier_path, extra_args)


if __name__ == "__main__":
    main()
