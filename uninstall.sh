#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR="$HOME/.claude/hooks"
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
  python3 "$(dirname "$0")/scripts/unpatch-settings.py" "$HOOK_PATH"
}

main() {
  info "Uninstalling claude-notifier…"
  remove_script
  if command -v python3 &>/dev/null; then
    patch_settings
  else
    warn "python3 not found — skipping settings.json cleanup."
    warn "Remove the hook entry manually from ~/.claude/settings.json."
  fi
  info "Done."
}

main
