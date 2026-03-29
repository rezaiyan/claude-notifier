#!/usr/bin/env python3
"""
Stop hook: fires a desktop notification when Claude finishes or is waiting.
Clicking the notification focuses the terminal window (macOS only).

macOS:  terminal-notifier (optional, falls back to osascript)
Linux:  notify-send | focus detection via xdotool (X11 only)
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path


WAITING_SIGNALS = [
    "what would you like",
    "should i proceed",
    "would you like me",
    "let me know",
    "do you want",
    "shall i",
    "ready to",
    "confirm",
]

# macOS: app name → bundle ID
KNOWN_TERMINALS_MACOS: dict[str, str] = {
    "Terminal": "com.apple.Terminal",
    "iTerm2": "com.googlecode.iterm2",
    "Warp": "dev.warp.Warp-Stable",
    "Ghostty": "com.mitchellh.ghostty",
    "Alacritty": "io.alacritty",
    "kitty": "net.kovidgoyal.kitty",
    "Hyper": "co.zeit.hyper",
}

# Linux: substrings matched against the active window title (lowercase)
KNOWN_TERMINALS_LINUX = {
    "terminal", "konsole", "xterm", "alacritty", "kitty",
    "tilix", "terminator", "xfce4-terminal", "warp", "ghostty",
    "st", "urxvt", "rxvt",
}


def extract_title(last_msg: str) -> str:
    """Pull a short action phrase from the last assistant message."""
    if not last_msg:
        return "Done"

    text = re.sub(r"[*_`#>]", "", last_msg).strip()

    for line in text.splitlines():
        line = line.strip()
        if len(line) > 8:
            if len(line) > 55:
                line = line[:55].rsplit(" ", 1)[0] + "…"
            return line

    return "Done"


# ── macOS ─────────────────────────────────────────────────────────────────────

def _detect_terminal_macos() -> tuple[str, str]:
    """Detect the running terminal from env vars. Returns (app_name, bundle_id)."""
    env = os.environ
    term_prog = env.get("TERM_PROGRAM", "")

    if "ITERM_SESSION_ID" in env or term_prog == "iTerm.app":
        return "iTerm2", "com.googlecode.iterm2"
    if "WARP_IS_LOCAL_SHELL_SESSION" in env or term_prog == "WarpTerminal":
        return "Warp", "dev.warp.Warp-Stable"
    if "GHOSTTY_RESOURCES_DIR" in env or term_prog == "ghostty":
        return "Ghostty", "com.mitchellh.ghostty"
    return "Terminal", "com.apple.Terminal"


def _macos_is_terminal_focused() -> bool:
    result = subprocess.run(
        [
            "osascript", "-e",
            "tell application \"System Events\" to "
            "name of first application process whose frontmost is true",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() in KNOWN_TERMINALS_MACOS


def _macos_notify(title: str, message: str, subtitle: str) -> None:
    app_name, bundle_id = _detect_terminal_macos()
    activate_script = f"osascript -e 'tell application \"{app_name}\" to activate'"

    try:
        result = subprocess.run(
            [
                "terminal-notifier",
                "-title", title,
                "-subtitle", subtitle,
                "-message", message,
                "-sound", "Glass",
                "-activate", bundle_id,
                "-execute", activate_script,
                "-group", "claude-code",
            ],
            capture_output=True,
        )
        if result.returncode == 0:
            return
    except FileNotFoundError:
        pass

    # Fallback: plain osascript notification
    safe = {k: v.replace('"', '\\"') for k, v in
            {"title": title, "message": message, "subtitle": subtitle}.items()}
    subprocess.run(
        [
            "osascript", "-e",
            f'display notification "{safe["message"]}" '
            f'with title "{safe["title"]}" '
            f'subtitle "{safe["subtitle"]}" '
            f'sound name "Glass"',
        ],
        capture_output=True,
    )


# ── Linux ─────────────────────────────────────────────────────────────────────

def _linux_is_terminal_focused() -> bool:
    """Return True if a terminal window is focused.

    Uses xdotool (X11 only). Returns False on Wayland or if xdotool is absent,
    so notifications are always sent rather than silently dropped.
    """
    if os.environ.get("WAYLAND_DISPLAY"):
        return False  # no reliable way without extra deps on Wayland

    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False
        title = result.stdout.strip().lower()
        return any(name in title for name in KNOWN_TERMINALS_LINUX)
    except FileNotFoundError:
        return False


def _linux_notify(title: str, message: str, subtitle: str) -> None:
    body = f"{subtitle}\n{message}" if subtitle else message
    try:
        subprocess.run(
            [
                "notify-send",
                "--app-name=Claude Code",
                "--urgency=normal",
                "--expire-time=8000",
                title,
                body,
            ],
            capture_output=True,
        )
    except FileNotFoundError:
        pass  # notify-send not installed — silent fallback


# ── Dispatch ──────────────────────────────────────────────────────────────────

def is_terminal_focused() -> bool:
    if sys.platform == "darwin":
        return _macos_is_terminal_focused()
    return _linux_is_terminal_focused()


def notify(title: str, message: str, subtitle: str) -> None:
    if sys.platform == "darwin":
        _macos_notify(title, message, subtitle)
    else:
        _linux_notify(title, message, subtitle)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    if data.get("stop_hook_active") or is_terminal_focused():
        print(json.dumps({}))
        return

    last_msg = data.get("last_assistant_message", "")
    project = Path.cwd().name

    is_waiting = any(s in last_msg.lower() for s in WAITING_SIGNALS)

    if is_waiting:
        title = "Claude Code — Waiting"
        message = extract_title(last_msg)
        subtitle = f"{project}  ·  needs your input"
    else:
        title = "Claude Code — Done"
        message = extract_title(last_msg)
        subtitle = project

    notify(title, message, subtitle)
    print(json.dumps({}))


if __name__ == "__main__":
    main()
