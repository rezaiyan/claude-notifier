#!/usr/bin/env python3
"""Remove claude-notifier from ~/.claude/settings.json.

Usage: python3 unpatch-settings.py <absolute-path-to-claude-notifier.py>
"""
import json
import sys
from pathlib import Path

hook_path = sys.argv[1]
settings_path = Path.home() / ".claude" / "settings.json"

if not settings_path.exists():
    print("[claude-notifier] settings.json not found — skipping.")
    sys.exit(0)

hook_command = f"python3 {hook_path}"
guarded = f"[ -f {hook_path} ] && {hook_command} || true"

data = json.loads(settings_path.read_text())

for block in data.get("hooks", {}).get("Stop", []):
    block["hooks"] = [
        h for h in block.get("hooks", [])
        if h.get("command") not in (hook_command, guarded)
    ]

data["hooks"]["Stop"] = [b for b in data["hooks"].get("Stop", []) if b.get("hooks")]
if not data["hooks"].get("Stop"):
    data["hooks"].pop("Stop", None)

settings_path.write_text(json.dumps(data, indent=2) + "\n")
print(f"[claude-notifier] Removed hook from {settings_path}")
