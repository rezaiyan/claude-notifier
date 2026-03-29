#!/usr/bin/env python3
"""Register claude-notifier in ~/.claude/settings.json.

Usage: python3 patch-settings.py <absolute-path-to-claude-notifier.py>
"""
import json
import sys
from pathlib import Path

hook_path = sys.argv[1]
settings_path = Path.home() / ".claude" / "settings.json"

hook_command = f"python3 {hook_path}"
guarded = f"[ -f {hook_path} ] && {hook_command} || true"

data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
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
