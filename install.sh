#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR="$HOME/.claude/hooks"
SCRIPT_NAME="claude-notifier.py"
SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/$SCRIPT_NAME"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
BOLD='\033[1m'; DIM='\033[2m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[claude-notifier]${NC} $*"; }
warn()    { echo -e "${YELLOW}[claude-notifier]${NC} $*"; }
error()   { echo -e "${RED}[claude-notifier]${NC} $*" >&2; exit 1; }

# ── Dependencies ──────────────────────────────────────────────────────────────
install_deps() {
  if [[ "$OSTYPE" == "darwin"* ]]; then
    : # macOS ships osascript; the bundled ClaudeNotifier.app is provided by Homebrew

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
  python3 "$(dirname "$0")/scripts/patch-settings.py" "$HOOK_DIR/$SCRIPT_NAME" "$@"
}

# ── Request notification permission (macOS only) ───────────────────────────────
request_permission() {
  if [[ "$OSTYPE" != "darwin"* ]]; then return; fi

  # Look for the ClaudeNotifier.app relative to this script (manual install layout).
  local app_bin
  app_bin="$(cd "$(dirname "$0")" && pwd)/ClaudeNotifier.app/Contents/MacOS/ClaudeNotifier"
  if [[ ! -x "$app_bin" ]]; then return; fi

  info "Requesting notification permission (a dialog may appear)…"
  # Launch once — the app calls requestAuthorization and exits on its own (≤10 s).
  "$app_bin" -title "Claude Notifier" -message "Notifications are enabled." \
             -subtitle "Setup complete" &>/dev/null &
  # Give macOS time to show the permission dialog before we print the success banner.
  sleep 2
}

# ── Main ──────────────────────────────────────────────────────────────────────
check_python3() {
  if ! command -v python3 &>/dev/null; then
    error "python3 is required but not found. Install it and re-run."
  fi
}

print_success() {
  echo
  echo -e "${BOLD}${GREEN}  ╭──────────────────────────────────────────────────────╮${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}                                                      ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}   ${BOLD}claude-notifier${NC} is ready                           ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}                                                      ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}   From now on, every Claude Code session will        ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}   notify you the moment Claude finishes a task       ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}   or is waiting for your input.                      ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}                                                      ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}   ${CYAN}◆  Claude Code — Done${NC}     task completed           ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}   ${YELLOW}◆  Claude Code — Waiting${NC}  needs your input         ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}                                                      ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}   ${DIM}Switch away freely — Claude will tap you.${NC}          ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  │${NC}                                                      ${BOLD}${GREEN}│${NC}"
  echo -e "${BOLD}${GREEN}  ╰──────────────────────────────────────────────────────╯${NC}"
  echo
}

main() {
  info "Starting installation…"
  check_python3
  install_deps
  install_script
  patch_settings "$@"
  request_permission
  print_success
}

main "$@"
