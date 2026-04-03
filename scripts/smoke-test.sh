#!/usr/bin/env bash
# smoke-test.sh — upgrade via Homebrew, run setup, verify notification, tear down.
# Mirrors exactly what a user does after a release: brew upgrade + claude-notifier-setup.
#
# Usage:
#   ./scripts/smoke-test.sh          # production: brew update + upgrade + setup + test
#   ./scripts/smoke-test.sh --local  # dev: build from source, test, clean up
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="$(cat "$REPO_ROOT/VERSION")"
BUNDLE_ID="io.github.rezaiyan.claude-notifier"
MACOS_MAJOR=$(sw_vers -productVersion | cut -d. -f1)
MODE="brew"
[[ "${1:-}" == "--local" ]] && MODE="local"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

FAILURES=0
pass()   { echo -e "  ${GREEN}✓${NC}  $*"; }
fail()   { echo -e "  ${RED}✗${NC}  $*"; FAILURES=$((FAILURES + 1)); }
info()   { echo -e "  ${CYAN}→${NC}  $*"; }
warn()   { echo -e "  ${YELLOW}!${NC}  $*"; }
header() { echo -e "\n${BOLD}$*${NC}"; }
ask() {
    local ans
    echo -en "  ${YELLOW}?${NC}  $1 [y/n] "
    read -r ans; [[ "$ans" =~ ^[Yy] ]]
}

# ── Cleanup ───────────────────────────────────────────────────────────────────
WORK_DIR=$(mktemp -d)
SETTINGS="$HOME/.claude/settings.json"
SETTINGS_BAK="$HOME/.claude/settings.json.smoke-bak"

cleanup() {
    rm -rf "$WORK_DIR"
    # Restore settings.json so hook round-trip test doesn't leave stale state
    if [[ -f "$SETTINGS_BAK" ]]; then
        mv "$SETTINGS_BAK" "$SETTINGS"
        info "Restored ~/.claude/settings.json"
    fi
    if [[ "$MODE" == "local" ]]; then
        rm -rf "$WORK_DIR"
    fi
}
trap cleanup EXIT

# ── Helpers ───────────────────────────────────────────────────────────────────
check_signing() {
    local app="$1"
    local sig
    sig=$(codesign -dv "$app" 2>&1 || true)
    if echo "$sig" | grep -q "Authority=Apple Development"; then
        fail "Signed with Apple Development cert — hard-denied by macOS for notifications"
        echo "$sig" | grep "Authority" | sed 's/^/       /'
    elif echo "$sig" | grep -q "Authority=Developer ID Application"; then
        pass "Developer ID Application signed"
    else
        pass "Ad-hoc signed (correct for Homebrew distribution)"
    fi
}

fire_osascript() {
    local ts; ts=$(date +%H:%M:%S)
    osascript -e \
        "tell application \"System Events\" to display notification \"Delivery works ✓\" with title \"claude-notifier smoke test\" subtitle \"v${VERSION} · ${ts}\"" \
        2>/dev/null && return 0
    osascript -e \
        "display notification \"Delivery works ✓\" with title \"claude-notifier smoke test\" sound name \"Glass\"" \
        2>/dev/null
}

fire_app() {
    local bin="$1"; local ts; ts=$(date +%H:%M:%S)
    "$bin" -title "claude-notifier smoke test" -message "Delivery works ✓" \
           -subtitle "v${VERSION} · ${ts}" &
    local pid=$!
    local waited=0
    while kill -0 "$pid" 2>/dev/null && (( waited < 5 )); do sleep 1; (( waited++ )); done
}

# ═════════════════════════════════════════════════════════════════════════════
echo -e "${BOLD}claude-notifier smoke test  v${VERSION}  [${MODE}]  macOS ${MACOS_MAJOR}${NC}"
echo    "────────────────────────────────────────"

# ── 1. Platform ───────────────────────────────────────────────────────────────
header "1. Platform"
[[ "$OSTYPE" == "darwin"* ]] || { fail "macOS required"; exit 1; }
pass "macOS $(sw_vers -productVersion)"

# ── 2. Install / upgrade ──────────────────────────────────────────────────────
if [[ "$MODE" == "brew" ]]; then
    header "2. brew update + upgrade + setup"
    info "brew update …"
    brew update --quiet 2>&1 | grep -E "Updated|Already" || true

    if brew list rezaiyan/tap/claude-notifier &>/dev/null; then
        INSTALLED_VER=$(brew info rezaiyan/tap/claude-notifier 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        if [[ "$INSTALLED_VER" == "$VERSION" ]]; then
            info "Already at v${VERSION} — reinstalling to exercise upgrade path …"
            brew reinstall rezaiyan/tap/claude-notifier 2>&1 | tail -3 | sed 's/^/       /'
        else
            info "Upgrading $INSTALLED_VER → $VERSION …"
            brew upgrade rezaiyan/tap/claude-notifier 2>&1 | tail -3 | sed 's/^/       /'
        fi
    else
        info "Installing v${VERSION} …"
        brew tap rezaiyan/tap https://github.com/rezaiyan/homebrew-tap &>/dev/null || true
        brew install rezaiyan/tap/claude-notifier 2>&1 | tail -3 | sed 's/^/       /'
    fi

    CELLAR="$(brew --prefix rezaiyan/tap/claude-notifier)"
    INSTALLED_VER=$(brew info rezaiyan/tap/claude-notifier 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [[ "$INSTALLED_VER" == "$VERSION" ]]; then
        pass "Installed v${VERSION} at $CELLAR"
    else
        fail "Expected v${VERSION}, got v${INSTALLED_VER}"
    fi

    info "claude-notifier-setup …"
    claude-notifier-setup 2>&1 | grep -v "^$" | sed 's/^/       /'
    pass "Setup complete"

    APP="$CELLAR/ClaudeNotifier.app"
    NOTIFIER_BIN="$APP/Contents/MacOS/ClaudeNotifier"
    PLIST="$APP/Contents/Info.plist"
    HOOK_SCRIPT="$CELLAR/libexec/claude-notifier.py"
    PATCH_SCRIPT="$CELLAR/libexec/patch-settings.py"
    UNPATCH_SCRIPT="$CELLAR/libexec/unpatch-settings.py"

else
    header "2. Build (local source)"
    APP="$WORK_DIR/ClaudeNotifier.app"
    mkdir -p "$APP/Contents/MacOS"
    cp "$REPO_ROOT/Sources/ClaudeNotifier/Info.plist" "$APP/Contents/"
    info "swiftc …"
    swiftc \
        -framework AppKit \
        -framework UserNotifications \
        "$REPO_ROOT/Sources/ClaudeNotifier/main.swift" \
        -o "$APP/Contents/MacOS/ClaudeNotifier" 2>&1 | sed 's/^/       /' || {
        fail "Compilation failed"; exit 1
    }
    codesign --force --deep --sign - "$APP" &>/dev/null
    pass "Compiled and ad-hoc signed"
    NOTIFIER_BIN="$APP/Contents/MacOS/ClaudeNotifier"
    PLIST="$APP/Contents/Info.plist"
    # Mirror the Homebrew layout: script at prefix/libexec/, app at prefix/ClaudeNotifier.app.
    # _macos_notify() resolves the app as Path(__file__).parent.parent / "ClaudeNotifier.app",
    # so the script must be one directory below the app's parent — i.e. in libexec/.
    mkdir -p "$WORK_DIR/libexec"
    cp "$REPO_ROOT/claude-notifier.py" "$WORK_DIR/libexec/claude-notifier.py"
    HOOK_SCRIPT="$WORK_DIR/libexec/claude-notifier.py"
    PATCH_SCRIPT="$REPO_ROOT/scripts/patch-settings.py"
    UNPATCH_SCRIPT="$REPO_ROOT/scripts/unpatch-settings.py"
fi

# ── 3. Info.plist ─────────────────────────────────────────────────────────────
header "3. Info.plist"
if /usr/libexec/PlistBuddy -c "Print :LSUIElement" "$PLIST" 2>/dev/null | grep -qi true; then
    fail "LSUIElement=true — permission prompt will be skipped on macOS 26"
else
    pass "LSUIElement not set"
fi
BUNDLE_ID_ACTUAL=$(/usr/libexec/PlistBuddy -c "Print :CFBundleIdentifier" "$PLIST" 2>/dev/null || echo "")
[[ "$BUNDLE_ID_ACTUAL" == "$BUNDLE_ID" ]] \
    && pass "Bundle ID: $BUNDLE_ID" \
    || fail "Bundle ID mismatch: expected '$BUNDLE_ID', got '$BUNDLE_ID_ACTUAL'"

# ── 4. Code signature ─────────────────────────────────────────────────────────
header "4. Code signature"
check_signing "$APP"

# ── 5. Notification delivery (end-to-end via installed hook) ──────────────────
header "5. Notification delivery"
info "Firing test notification via --test flag …"
python3 "$HOOK_SCRIPT" --test
sleep 2

if ask "Did you see a notification?"; then
    pass "End-to-end delivery confirmed (--test)"
else
    fail "No notification seen"
    if (( MACOS_MAJOR >= 26 )); then
        warn "macOS 26: check that Terminal has Automation permission for System Events"
        warn "System Settings → Privacy & Security → Automation → Terminal → System Events"
    else
        warn "Check: System Settings → Notifications → Claude Notifier"
    fi
fi

info "Piping stop-hook JSON through the installed claude-notifier.py …"
echo '{"last_assistant_message": "smoke test complete", "stop_hook_active": false}' \
    | python3 "$HOOK_SCRIPT"
sleep 1

# ── 6. Hook settings.json round-trip ─────────────────────────────────────────
header "6. Hook settings.json (patch / unpatch)"
[[ -f "$SETTINGS" ]] && cp "$SETTINGS" "$SETTINGS_BAK"

info "patch-settings.py …"
python3 "$PATCH_SCRIPT" "$HOOK_SCRIPT"
if grep -q "claude-notifier.py" "$SETTINGS" 2>/dev/null; then
    pass "Hook registered"
else
    fail "Hook not found after patch"
fi

info "Idempotency check (second patch run) …"
COUNT_BEFORE=$(grep -c "claude-notifier.py" "$SETTINGS" 2>/dev/null || echo 0)
python3 "$PATCH_SCRIPT" "$HOOK_SCRIPT"
COUNT_AFTER=$(grep -c "claude-notifier.py" "$SETTINGS" 2>/dev/null || echo 0)
[[ "$COUNT_BEFORE" -eq "$COUNT_AFTER" ]] \
    && pass "Idempotent (no duplicate)" \
    || fail "Duplicate hook added ($COUNT_BEFORE → $COUNT_AFTER)"

if [[ "$MODE" == "brew" ]]; then
    info "Verifying hook uses stable opt path (not versioned Cellar) …"
    HOOK_CMD=$(python3 -c "
import json, sys
data = json.load(open('$SETTINGS'))
for g in data.get('hooks', {}).get('Stop', []):
    for h in g.get('hooks', []):
        if 'claude-notifier.py' in h.get('command', ''):
            print(h['command']); sys.exit(0)
" 2>/dev/null)
    if echo "$HOOK_CMD" | grep -q "/Cellar/"; then
        fail "Hook uses versioned Cellar path — will break after brew upgrade: $HOOK_CMD"
    else
        pass "Hook uses stable opt path (upgrade-safe)"
    fi
fi

info "unpatch-settings.py …"
python3 "$UNPATCH_SCRIPT" "$HOOK_SCRIPT"
grep -q "claude-notifier.py" "$SETTINGS" 2>/dev/null \
    && fail "Hook still present after unpatch" \
    || pass "Hook removed"

# ── Result ────────────────────────────────────────────────────────────────────
echo
echo "────────────────────────────────────────"
if [[ $FAILURES -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}  All checks passed — v${VERSION} ships${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}  ${FAILURES} check(s) failed — do not release${NC}"
    exit 1
fi
