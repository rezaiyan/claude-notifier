#!/usr/bin/env python3
"""Register claude-notifier in ~/.claude/settings.json.

Usage: python3 patch-settings.py <absolute-path-to-claude-notifier.py>
"""
import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: patch-settings.py <path-to-claude-notifier.py> [args...]", file=sys.stderr)
    sys.exit(1)

hook_path = sys.argv[1]
extra_args = sys.argv[2:]  # e.g. ["--skip-if-focused"]
settings_path = Path.home() / ".claude" / "settings.json"

extra = (" " + " ".join(extra_args)) if extra_args else ""
hook_command = f'python3 "{hook_path}"{extra}'
guarded = f'[ -f "{hook_path}" ] && {hook_command} || true'

try:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    if not isinstance(data, dict):
        data = {}
    if data.get("allowManagedHooksOnly"):
        print(
            "[claude-notifier] WARNING: allowManagedHooksOnly is enabled in settings.json.\n"
            "  User hooks are blocked by policy — notifications will not fire even after setup.\n"
            "  Ask your admin to allow user hooks, or watch the session log instead.",
            file=sys.stderr,
        )
except json.JSONDecodeError:
    print(
        f"[claude-notifier] Warning: {settings_path} contains invalid JSON — creating backup and starting fresh.",
        file=sys.stderr,
    )
    settings_path.rename(settings_path.with_suffix(".json.bak"))
    data = {}

data.setdefault("hooks", {}).setdefault("Stop", [{}])
data["hooks"]["Stop"][0].setdefault("hooks", [])
hooks = data["hooks"]["Stop"][0]["hooks"]

stale = [h for h in hooks if "claude-notifier.py" in h.get("command", "") and h.get("command") != guarded]
already_current = any(h.get("command") == guarded for h in hooks)

if not stale and already_current:
    print("[claude-notifier] Hook already registered.")
else:
    # Remove all claude-notifier hooks (handles path changes on version upgrades).
    hooks[:] = [h for h in hooks if "claude-notifier.py" not in h.get("command", "")]
    hooks.append({"type": "command", "command": guarded})
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    if stale:
        print(f"[claude-notifier] Updated hook in {settings_path} (removed {len(stale)} stale entry)")
    else:
        print(f"[claude-notifier] Registered hook in {settings_path}")
