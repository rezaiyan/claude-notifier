#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR="$HOME/.claude/hooks"
SETTINGS="$HOME/.claude/settings.json"
SCRIPT_NAME="claude-notifier.py"
HOOK_PATH="$HOOK_DIR/$SCRIPT_NAME"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[claude-notifier]${NC} $*"; }
warn() { echo -e "${YELLOW}[claude-notifier]${NC} $*"; }

remove_script() {
  if [[ -f "$HOOK_PATH" ]]; then
    rm "$HOOK_PATH"
    info "Removed $HOOK_PATH"
  else
    warn "Script not found at $HOOK_PATH — skipping."
  fi
}

patch_settings() {
  if [[ ! -f "$SETTINGS" ]]; then
    warn "settings.json not found — skipping."
    return
  fi

  python3 - "$SETTINGS" "$HOOK_PATH" <<'PYEOF'
import json, sys, pathlib

settings_path = pathlib.Path(sys.argv[1])
hook_command  = f"python3 {sys.argv[2]}"

data = json.loads(settings_path.read_text())

stop_blocks = data.get("hooks", {}).get("Stop", [])
changed = False

for block in stop_blocks:
    hooks = block.get("hooks", [])
    before = len(hooks)
    block["hooks"] = [h for h in hooks if h.get("command") != hook_command]
    if len(block["hooks"]) < before:
        changed = True

# Remove empty Stop blocks
data["hooks"]["Stop"] = [b for b in stop_blocks if b.get("hooks")]
if not data["hooks"]["Stop"]:
    del data["hooks"]["Stop"]

if changed:
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"[claude-notifier] Removed Stop hook from {settings_path}")
else:
    print(f"[claude-notifier] Hook entry not found in {settings_path} — skipping.")
PYEOF
}

main() {
  info "Uninstalling claude-notifier…"
  remove_script
  patch_settings
  info "Done."
}

main
