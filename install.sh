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
  python3 "$(dirname "$0")/scripts/patch-settings.py" "$HOOK_DIR/$SCRIPT_NAME"
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
  patch_settings
  print_success
}

main
