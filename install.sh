#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR="$HOME/.claude/hooks"
SETTINGS="$HOME/.claude/settings.json"
SCRIPT_NAME="claude-notifier.py"
SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/$SCRIPT_NAME"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[claude-notifier]${NC} $*"; }
warn()    { echo -e "${YELLOW}[claude-notifier]${NC} $*"; }
error()   { echo -e "${RED}[claude-notifier]${NC} $*" >&2; exit 1; }

# ── Dependencies ──────────────────────────────────────────────────────────────
install_deps() {
  if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v terminal-notifier &>/dev/null; then
      if command -v brew &>/dev/null; then
        info "Installing terminal-notifier via Homebrew…"
        brew install terminal-notifier
      else
        warn "terminal-notifier not found and Homebrew is not installed."
        warn "Notifications will fall back to osascript (no click-to-focus)."
        warn "To install manually: brew install terminal-notifier"
      fi
    else
      info "terminal-notifier already installed."
    fi

  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! command -v notify-send &>/dev/null; then
      info "Installing libnotify-bin…"
      if command -v apt-get &>/dev/null; then
        sudo apt-get install -y libnotify-bin
      elif command -v dnf &>/dev/null; then
        sudo dnf install -y libnotify
      elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm libnotify
      else
        warn "Could not install notify-send automatically. Install libnotify for your distro."
      fi
    else
      info "notify-send already installed."
    fi

    if ! command -v xdotool &>/dev/null; then
      info "Installing xdotool (optional, for focus detection on X11)…"
      if command -v apt-get &>/dev/null; then
        sudo apt-get install -y xdotool
      elif command -v dnf &>/dev/null; then
        sudo dnf install -y xdotool
      elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm xdotool
      else
        warn "Could not install xdotool automatically. Focus detection will be disabled on X11."
      fi
    else
      info "xdotool already installed."
    fi

  else
    error "Unsupported OS: $OSTYPE. Only macOS and Linux are supported."
  fi
}

# ── Copy script ───────────────────────────────────────────────────────────────
install_script() {
  mkdir -p "$HOOK_DIR"
  cp "$SCRIPT_SRC" "$HOOK_DIR/$SCRIPT_NAME"
  chmod +x "$HOOK_DIR/$SCRIPT_NAME"
  info "Installed $SCRIPT_NAME → $HOOK_DIR/$SCRIPT_NAME"
}

# ── Patch settings.json ───────────────────────────────────────────────────────
patch_settings() {
  python3 - "$SETTINGS" "$HOOK_DIR/$SCRIPT_NAME" <<'PYEOF'
import json, sys, pathlib

settings_path = pathlib.Path(sys.argv[1])
hook_command  = f"python3 {sys.argv[2]}"

# Load or start fresh
if settings_path.exists():
    data = json.loads(settings_path.read_text())
else:
    data = {}

# Ensure structure exists
data.setdefault("hooks", {})
data["hooks"].setdefault("Stop", [{}])
data["hooks"]["Stop"][0].setdefault("hooks", [])

existing = data["hooks"]["Stop"][0]["hooks"]
# Wrap with existence check so an orphaned entry (e.g. after `brew uninstall`)
# fails silently instead of producing a Python error on every Claude stop.
guarded_command = f"[ -f {sys.argv[2]} ] && {hook_command} || true"
entry = {"type": "command", "command": guarded_command}

# Idempotent: only add if not already present
if not any(h.get("command") == guarded_command for h in existing):
    existing.append(entry)
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"[claude-notifier] Registered Stop hook in {settings_path}")
else:
    print(f"[claude-notifier] Stop hook already registered in {settings_path}")
PYEOF
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  info "Starting installation…"
  install_deps
  install_script
  patch_settings
  info "Done. Claude Code will notify you when it finishes or needs input."
}

main
