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

if not any(h.get("command") == guarded for h in hooks):
    hooks.append({"type": "command", "command": guarded})
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"[claude-notifier] Registered hook in {settings_path}")
else:
    print("[claude-notifier] Hook already registered.")
