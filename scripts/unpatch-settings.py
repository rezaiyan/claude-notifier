#!/usr/bin/env python3
"""Remove claude-notifier from ~/.claude/settings.json and unload the daemon if present.

Usage: python3 unpatch-settings.py <absolute-path-to-claude-notifier.py>
"""
import json
import os
import subprocess
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: unpatch-settings.py <path-to-claude-notifier.py>", file=sys.stderr)
    sys.exit(1)

hook_path = sys.argv[1]
settings_path = Path.home() / ".claude" / "settings.json"

# ── Remove hook from settings.json ───────────────────────────────────────────

if not settings_path.exists():
    print("[claude-notifier] settings.json not found — skipping hook removal.")
else:
    try:
        data = json.loads(settings_path.read_text())
        if not isinstance(data, dict):
            print("[claude-notifier] settings.json has unexpected format — skipping hook removal.")
        else:
            removed = False
            for block in data.get("hooks", {}).get("Stop", []):
                before = len(block.get("hooks", []))
                block["hooks"] = [
                    h for h in block.get("hooks", [])
                    if "claude-notifier.py" not in h.get("command", "")
                ]
                if len(block["hooks"]) < before:
                    removed = True

            if not removed:
                print("[claude-notifier] Hook not found — nothing to remove.")
            else:
                hooks_section = data.get("hooks", {})
                hooks_section["Stop"] = [b for b in hooks_section.get("Stop", []) if b.get("hooks")]
                if not hooks_section.get("Stop"):
                    hooks_section.pop("Stop", None)
                settings_path.write_text(json.dumps(data, indent=2) + "\n")
                print(f"[claude-notifier] Removed hook from {settings_path}")

    except json.JSONDecodeError:
        print("[claude-notifier] settings.json contains invalid JSON — skipping hook removal.")

# ── Unload and remove the log-watcher daemon (macOS only) ────────────────────

DAEMON_LABEL = "com.claude-notifier.log-watcher"
DAEMON_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{DAEMON_LABEL}.plist"

if sys.platform == "darwin":
    daemon_loaded = subprocess.run(
        ["launchctl", "list", DAEMON_LABEL],
        capture_output=True,
    ).returncode == 0

    if daemon_loaded:
        uid = os.getuid()
        subprocess.run(
            ["launchctl", "bootout", f"gui/{uid}/{DAEMON_LABEL}"],
            capture_output=True,
        )
        print("[claude-notifier] Stopped log-watcher daemon.")

    if DAEMON_PLIST.exists():
        DAEMON_PLIST.unlink()
        print(f"[claude-notifier] Removed daemon plist {DAEMON_PLIST}")
