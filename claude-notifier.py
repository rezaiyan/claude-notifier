#!/usr/bin/env python3
"""
Stop hook: fires a desktop notification when Claude finishes or is waiting.

macOS:  ClaudeNotifier.app (bundled, falls back to osascript)
Linux:  notify-send | focus detection via xdotool (X11 only)
"""
import argparse
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
]

# Linux: substrings matched against the active window title (lowercase)
KNOWN_TERMINALS_LINUX = {
    "terminal", "konsole", "xterm", "alacritty", "kitty",
    "tilix", "terminator", "xfce4-terminal", "warp", "ghostty",
    "st", "urxvt", "rxvt",
}


_SUBPROCESS_TIMEOUT = 3  # seconds — prevents hangs in focus detection


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

def _macos_is_terminal_focused() -> bool:
    try:
        result = subprocess.run(
            [
                "osascript", "-e",
                "tell application \"System Events\" to "
                "name of first application process whose frontmost is true",
            ],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False
    known = {
        "Terminal", "iTerm2", "Warp", "Ghostty", "Alacritty", "kitty", "Hyper",
    }
    return result.stdout.strip() in known


def _macos_notify(title: str, message: str, subtitle: str) -> None:
    # Prefer the bundled app (installed by Homebrew alongside this script).
    # Path: {cellar_prefix}/libexec/claude-notifier.py  →  ../ClaudeNotifier.app
    bundled = (
        Path(__file__).resolve().parent.parent
        / "ClaudeNotifier.app/Contents/MacOS/ClaudeNotifier"
    )
    if bundled.exists():
        try:
            # Fire-and-forget: the app manages its own run loop and exits when done.
            subprocess.Popen(
                [str(bundled), "-title", title, "-message", message, "-subtitle", subtitle],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except OSError:
            pass

    # Fallback: osascript (manual installs, CI, non-Homebrew environments)
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
            timeout=_SUBPROCESS_TIMEOUT,
        )
        if result.returncode != 0:
            return False
        title = result.stdout.strip().lower()
        return any(name in title for name in KNOWN_TERMINALS_LINUX)
    except (FileNotFoundError, subprocess.TimeoutExpired):
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
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--skip-if-focused", action="store_true")
    args, _ = parser.parse_known_args()

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if not isinstance(data, dict):
        sys.exit(0)

    if data.get("stop_hook_active") or (args.skip_if_focused and is_terminal_focused()):
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
