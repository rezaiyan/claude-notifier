#!/usr/bin/env bash
# smoke-test.sh — build, verify, test notification, verify hooks, tear down.
# Run this locally before tagging a release.
#
# Usage:
#   ./scripts/smoke-test.sh          # build from source, test, clean up
#   ./scripts/smoke-test.sh --brew   # brew install, test, brew uninstall
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="$(cat "$REPO_ROOT/VERSION")"
BUNDLE_ID="io.github.rezaiyan.claude-notifier"
MODE="local"
[[ "${1:-}" == "--brew" ]] && MODE="brew"

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
    if [[ -f "$SETTINGS_BAK" ]]; then
        mv "$SETTINGS_BAK" "$SETTINGS"
        info "Restored ~/.claude/settings.json"
    fi
    if [[ "$MODE" == "brew" ]] && brew list rezaiyan/tap/claude-notifier &>/dev/null; then
        info "Uninstalling Homebrew formula..."
        brew uninstall rezaiyan/tap/claude-notifier 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ── Helpers ───────────────────────────────────────────────────────────────────
ncprefs_registered() {
    defaults read com.apple.ncprefs 2>/dev/null | grep -q "$BUNDLE_ID"
}

check_signing() {
    local app="$1"
    local info
    info=$(codesign -dv "$app" 2>&1 || true)
    if echo "$info" | grep -q "Authority=Apple Development"; then
        fail "Signed with Apple Development cert — Gatekeeper will reject on distribution"
        echo "$info" | grep "Authority" | sed 's/^/       /'
        return 1
    elif echo "$info" | grep -q "Authority=Developer ID Application"; then
        pass "Developer ID Application signed"
    else
        pass "Ad-hoc signed (correct for Homebrew distribution)"
    fi
}

fire_notification() {
    local binary="$1"
    "$binary" \
        -title  "claude-notifier smoke test" \
        -message "Delivery works ✓" \
        -subtitle "v${VERSION} · $(date +%H:%M:%S)" &
    # Wait up to 5 s for the process to hand off and exit
    local pid=$!
    local waited=0
    while kill -0 "$pid" 2>/dev/null && (( waited < 5 )); do
        sleep 1; (( waited++ ))
    done
}

# ═════════════════════════════════════════════════════════════════════════════
echo -e "${BOLD}claude-notifier smoke test  v${VERSION}  [${MODE}]${NC}"
echo    "────────────────────────────────────────"

# ── 1. Platform ───────────────────────────────────────────────────────────────
header "1. Platform"
if [[ "$OSTYPE" != "darwin"* ]]; then
    fail "macOS required"; exit 1
fi
pass "macOS $(sw_vers -productVersion)"

# ── 2a. LOCAL: build from source ─────────────────────────────────────────────
if [[ "$MODE" == "local" ]]; then
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

# ── 2b. BREW: install from tap ───────────────────────────────────────────────
else
    header "2. Homebrew install"
    info "brew tap rezaiyan/tap …"
    brew tap rezaiyan/tap https://github.com/rezaiyan/homebrew-tap &>/dev/null || true
    info "brew install rezaiyan/tap/claude-notifier …"
    brew install rezaiyan/tap/claude-notifier 2>&1 | tail -5 | sed 's/^/       /'
    CELLAR="$(brew --prefix rezaiyan/tap/claude-notifier)"
    APP="$CELLAR/ClaudeNotifier.app"
    NOTIFIER_BIN="$APP/Contents/MacOS/ClaudeNotifier"
    PLIST="$APP/Contents/Info.plist"
    pass "Installed to $CELLAR"
fi

# ── 3. Info.plist ─────────────────────────────────────────────────────────────
header "3. Info.plist"
if /usr/libexec/PlistBuddy -c "Print :LSUIElement" "$PLIST" 2>/dev/null | grep -qi true; then
    fail "LSUIElement=true — macOS 26 will skip the notification permission prompt"
else
    pass "LSUIElement not set"
fi
BUNDLE_ID_ACTUAL=$(/usr/libexec/PlistBuddy -c "Print :CFBundleIdentifier" "$PLIST" 2>/dev/null || echo "")
if [[ "$BUNDLE_ID_ACTUAL" == "$BUNDLE_ID" ]]; then
    pass "Bundle ID: $BUNDLE_ID"
else
    fail "Bundle ID mismatch: expected '$BUNDLE_ID', got '$BUNDLE_ID_ACTUAL'"
fi

# ── 4. Code signature ─────────────────────────────────────────────────────────
header "4. Code signature"
check_signing "$APP"

# ── 5. Notification permission (pre-flight) ───────────────────────────────────
header "5. Notification permission (before launch)"
if ncprefs_registered; then
    pass "Already registered in com.apple.ncprefs"
else
    warn "Not yet registered — expected on a fresh install"
fi

# ── 6. Fire notification ──────────────────────────────────────────────────────
header "6. Notification delivery"
if [[ ! -x "$NOTIFIER_BIN" ]]; then
    fail "Binary not executable: $NOTIFIER_BIN"; exit 1
fi
info "Launching ClaudeNotifier — watch for a permission dialog or notification…"
fire_notification "$NOTIFIER_BIN"

if ncprefs_registered; then
    pass "Registered in com.apple.ncprefs after launch"
else
    warn "Still not in com.apple.ncprefs — may need a second launch after granting permission"
fi

if ask "Did you see a notification or a 'Allow Notifications?' dialog?"; then
    pass "Visual delivery confirmed"
else
    fail "No notification or dialog seen"
    warn "Check: System Settings → Notifications → Claude Notifier"
fi

# ── 7. Hook round-trip ────────────────────────────────────────────────────────
header "7. Hook script (patch / unpatch)"
[[ -f "$SETTINGS" ]] && cp "$SETTINGS" "$SETTINGS_BAK"

HOOK_SCRIPT="$REPO_ROOT/claude-notifier.py"
if [[ "$MODE" == "brew" ]]; then
    HOOK_SCRIPT="$(brew --prefix rezaiyan/tap/claude-notifier)/libexec/claude-notifier.py"
fi

info "patch-settings.py …"
python3 "$REPO_ROOT/scripts/patch-settings.py" "$HOOK_SCRIPT"
if grep -q "claude-notifier.py" "$SETTINGS" 2>/dev/null; then
    pass "Hook registered"
else
    fail "Hook not found in settings.json after patch"
fi

# Run twice — second run must not add a duplicate
info "patch-settings.py (idempotency check) …"
COUNT_BEFORE=$(grep -c "claude-notifier.py" "$SETTINGS" 2>/dev/null || echo 0)
python3 "$REPO_ROOT/scripts/patch-settings.py" "$HOOK_SCRIPT"
COUNT_AFTER=$(grep -c "claude-notifier.py" "$SETTINGS" 2>/dev/null || echo 0)
if [[ "$COUNT_BEFORE" -eq "$COUNT_AFTER" ]]; then
    pass "Idempotent (no duplicate hook added)"
else
    fail "Duplicate hook added on second run ($COUNT_BEFORE → $COUNT_AFTER)"
fi

info "unpatch-settings.py …"
python3 "$REPO_ROOT/scripts/unpatch-settings.py" "$HOOK_SCRIPT"
if grep -q "claude-notifier.py" "$SETTINGS" 2>/dev/null; then
    fail "Hook still present after unpatch"
else
    pass "Hook removed"
fi

# ── 8. End-to-end hook pipe ───────────────────────────────────────────────────
header "8. Hook pipe (JSON → notify)"
info "Piping stop-hook JSON to claude-notifier.py …"
OUTPUT=$(echo '{"last_assistant_message": "smoke test complete", "stop_hook_active": false}' \
    | python3 "$HOOK_SCRIPT" 2>&1 || true)
if echo "$OUTPUT" | python3 -c "import sys,json; json.load(sys.stdin)" &>/dev/null; then
    pass "Hook returned valid JSON"
else
    fail "Hook output is not valid JSON: $OUTPUT"
fi

# ── Result ────────────────────────────────────────────────────────────────────
echo
echo "────────────────────────────────────────"
if [[ $FAILURES -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}  All checks passed — safe to release v${VERSION}${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}  ${FAILURES} check(s) failed — do not release${NC}"
    exit 1
fi
