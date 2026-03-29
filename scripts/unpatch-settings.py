#!/usr/bin/env python3
"""Remove claude-notifier from ~/.claude/settings.json.

Usage: python3 unpatch-settings.py <absolute-path-to-claude-notifier.py>
"""
import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: unpatch-settings.py <path-to-claude-notifier.py>", file=sys.stderr)
    sys.exit(1)

hook_path = sys.argv[1]
settings_path = Path.home() / ".claude" / "settings.json"

if not settings_path.exists():
    print("[claude-notifier] settings.json not found — skipping.")
    sys.exit(0)

try:
    data = json.loads(settings_path.read_text())
    if not isinstance(data, dict):
        print("[claude-notifier] settings.json has unexpected format — skipping.")
        sys.exit(0)
except json.JSONDecodeError:
    print("[claude-notifier] settings.json contains invalid JSON — skipping.")
    sys.exit(0)

hook_command = f"python3 {hook_path}"
guarded = f"[ -f {hook_path} ] && {hook_command} || true"

for block in data.get("hooks", {}).get("Stop", []):
    block["hooks"] = [
        h for h in block.get("hooks", [])
        if h.get("command") not in (hook_command, guarded)
    ]

hooks_section = data.get("hooks", {})
hooks_section["Stop"] = [b for b in hooks_section.get("Stop", []) if b.get("hooks")]
if not hooks_section.get("Stop"):
    hooks_section.pop("Stop", None)

settings_path.write_text(json.dumps(data, indent=2) + "\n")
print(f"[claude-notifier] Removed hook from {settings_path}")
