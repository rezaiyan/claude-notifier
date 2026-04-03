#!/usr/bin/env python3
"""
Stop hook: fires a desktop notification when Claude finishes or is waiting.

macOS:  ClaudeNotifier.app via UNUserNotificationCenter (notarized Developer ID)
        — appears as "Claude Notifier" in System Settings → Notifications.
        osascript is kept as a fallback for non-Homebrew installs.
Linux:  notify-send | focus detection via xdotool (X11 only)

Run without arguments (interactive) to check setup status.
"""
import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = "1.3.3"


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
_LOCK_PATH = Path(tempfile.gettempdir()) / "claude-notifier.lock"
# Resolved at import time so tests can patch it.
_BUNDLED_APP_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / "ClaudeNotifier.app/Contents/MacOS/ClaudeNotifier"
)


def _acquire_lock() -> "object | None":
    """Grab an exclusive non-blocking file lock. Returns the open file or None if busy."""
    try:
        lf = open(_LOCK_PATH, "w")  # noqa: SIM115, WPS515
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lf
    except (BlockingIOError, PermissionError, OSError):
        return None


def _release_lock(lf: "object") -> None:
    try:
        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
        lf.close()  # type: ignore[attr-defined]
    except OSError:
        pass


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


def _macos_osascript_notify(title: str, message: str, subtitle: str) -> None:
    """Deliver via osascript — works on all macOS versions, no permission needed."""
    safe = {k: v.replace('"', '\\"') for k, v in
            {"title": title, "message": message, "subtitle": subtitle}.items()}
    # System Events delegation form works on macOS 26 (Tahoe); bare form is the
    # fallback for older macOS where System Events doesn't support that syntax.
    result = subprocess.run(
        [
            "osascript", "-e",
            f'tell application "System Events" to '
            f'display notification "{safe["message"]}" '
            f'with title "{safe["title"]}" '
            f'subtitle "{safe["subtitle"]}"',
        ],
        capture_output=True,
    )
    if result.returncode != 0:
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


def _macos_notify(title: str, message: str, subtitle: str) -> None:
    # Prefer the notarized ClaudeNotifier.app (UNUserNotificationCenter) on all
    # macOS versions — notarization is required for authorization to be granted.
    # Signal mechanism: the app creates a temp file (path passed via env var
    # CLAUDE_NOTIFIER_SIGNAL_FILE) after successfully handing the request to the
    # system daemon.  We must NOT redirect stdout/stderr — doing so replaces the
    # inherited PTY with a pipe or /dev/null, which severs the window-server
    # session and causes silent delivery failure even though the app exits 0.
    # The Swift app writes nothing to stdout, so inheriting is safe.
    if _BUNDLED_APP_PATH.exists():
        sig = Path(tempfile.mktemp(prefix="cn-ok-"))  # noqa: S306
        try:
            proc = subprocess.Popen(
                [str(_BUNDLED_APP_PATH), "-title", title, "-message", message, "-subtitle", subtitle],
                env={**os.environ, "CLAUDE_NOTIFIER_SIGNAL_FILE": str(sig)},
            )
            try:
                proc.wait(timeout=10)
                if sig.exists():
                    return  # notification delivered
                # No signal file — silent failure, fall through to osascript.
            except subprocess.TimeoutExpired:
                proc.kill()
        except OSError:
            pass
        finally:
            sig.unlink(missing_ok=True)

    _macos_osascript_notify(title, message, subtitle)


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


# ── Interactive status ────────────────────────────────────────────────────────

def _check_setup() -> tuple[bool, str]:
    """Return (is_registered, hook_path_or_empty)."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return False, ""
    try:
        data = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return False, ""
    for group in data.get("hooks", {}).get("Stop", []):
        for h in group.get("hooks", []):
            cmd = h.get("command", "")
            if "claude-notifier.py" in cmd:
                m = re.search(r'"([^"]*claude-notifier\.py)"', cmd)
                return True, m.group(1) if m else cmd
    return False, ""


def _check_managed_hooks_only() -> bool:
    """Return True if allowManagedHooksOnly is set, which silently blocks user hooks."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return False
    try:
        data = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    return bool(data.get("allowManagedHooksOnly", False))


def _check_daemon() -> bool:
    """Return True if the log-watcher launchd daemon is loaded (macOS only)."""
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["launchctl", "list", "com.claude-notifier.log-watcher"],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _offer_interactive_setup(managed_only: bool, BOLD: str, DIM: str, NC: str) -> None:
    """Prompt the user to run setup now, then exec the right installer."""
    setup_cmd = shutil.which("claude-notifier-setup")
    install_sh = Path(__file__).resolve().parent.parent / "install.sh"
    if not install_sh.exists():
        # git-clone layout: install.sh sits next to the script itself
        install_sh = Path(__file__).resolve().parent / "install.sh"

    # Decide which command we'll run if the user says yes
    if setup_cmd:
        run_label = f"{BOLD}claude-notifier-setup{NC}"
        run_args: list[str] = [setup_cmd]
    elif install_sh.exists():
        run_label = f"{BOLD}bash {install_sh}{NC}"
        run_args = ["bash", str(install_sh)]
    else:
        # Nothing available — fall back to informational text
        print("  Run to activate:")
        print(f"    {BOLD}claude-notifier-setup{NC}          (Homebrew install)")
        print(f"    {BOLD}bash install.sh{NC}                (manual / git clone)")
        print(f"\n  {DIM}After setup, Claude Code will notify you automatically.{NC}")
        return

    try:
        answer = input(f"  Set up now with {run_label}? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if answer in ("", "y", "yes"):
        print()
        result = subprocess.run(run_args, check=False)
        if result.returncode != 0:
            print(f"[claude-notifier] Setup failed (exit {result.returncode})", file=sys.stderr)
    else:
        print(f"\n  {DIM}Run manually when ready:{NC}")
        if setup_cmd:
            print(f"    {BOLD}claude-notifier-setup{NC}          (Homebrew install)")
        if install_sh.exists():
            print(f"    {BOLD}bash {install_sh}{NC}  (manual / git clone)")
        print(f"\n  {DIM}After setup, Claude Code will notify you automatically.{NC}")


def show_status() -> None:
    GREEN  = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED    = "\033[0;31m"
    BOLD   = "\033[1m"
    CYAN   = "\033[0;36m"
    DIM    = "\033[2m"
    NC     = "\033[0m"

    is_setup, hook_path = _check_setup()
    managed_only = _check_managed_hooks_only()
    daemon_running = _check_daemon()
    platform_tag = "macOS" if sys.platform == "darwin" else "Linux"

    print(f"\n{BOLD}claude-notifier{NC}  v{VERSION}  [{platform_tag}]")
    print(f"{DIM}Desktop notifications for Claude Code — done and waiting alerts{NC}\n")

    active = False

    if daemon_running:
        print(f"  {GREEN}✓{NC}  Log-watcher daemon active")
        if managed_only:
            print(f"     {DIM}Bypassing hook policy via session-log monitoring{NC}")
        print("\n  Notifications fire when Claude finishes or needs your input:\n")
        print(f"    {CYAN}◆  Claude Code — Done{NC}     task completed")
        print(f"    {YELLOW}◆  Claude Code — Waiting{NC}  needs your input")
        print(f"\n  {DIM}Test delivery:  claude-notifier --test{NC}")
        print(f"  {DIM}To remove:      claude-notifier uninstall{NC}")
        active = True

    elif is_setup:
        if managed_only:
            print(f"  {YELLOW}⚠{NC}  {BOLD}allowManagedHooksOnly{NC} is enabled — hook will not fire")
            print(f"     {DIM}Re-run claude-notifier-setup to install the log-watcher daemon.{NC}\n")
        else:
            print(f"  {GREEN}✓{NC}  Hook registered")
            if hook_path:
                print(f"     {DIM}{hook_path}{NC}")
            print("\n  Notifications fire when Claude finishes or needs your input:\n")
            print(f"    {CYAN}◆  Claude Code — Done{NC}     task completed")
            print(f"    {YELLOW}◆  Claude Code — Waiting{NC}  needs your input")
            print(f"\n  {DIM}Test delivery:  claude-notifier --test{NC}")
            print(f"  {DIM}To remove:      claude-notifier uninstall{NC}")
            active = True

    if not active and not is_setup:
        if managed_only:
            print(f"  {YELLOW}⚠{NC}  {BOLD}allowManagedHooksOnly{NC} is enabled in settings.json")
            print("     User hooks are blocked by policy.\n")
        else:
            print(f"  {RED}✗{NC}  Not configured\n")

        _offer_interactive_setup(managed_only, BOLD, DIM, NC)

    print()


# ── Uninstall ─────────────────────────────────────────────────────────────────

def _do_uninstall() -> None:
    """Remove hook + daemon, then uninstall the package."""
    notifier_py = Path(__file__).resolve()

    # ── 1. Remove hook from settings.json ────────────────────────────────────
    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text())
            if isinstance(data, dict):
                removed = False
                for block in data.get("hooks", {}).get("Stop", []):
                    before = len(block.get("hooks", []))
                    block["hooks"] = [
                        h for h in block.get("hooks", [])
                        if "claude-notifier.py" not in h.get("command", "")
                    ]
                    if len(block["hooks"]) < before:
                        removed = True
                if removed:
                    hs = data.get("hooks", {})
                    hs["Stop"] = [b for b in hs.get("Stop", []) if b.get("hooks")]
                    if not hs.get("Stop"):
                        hs.pop("Stop", None)
                    settings_path.write_text(json.dumps(data, indent=2) + "\n")
                    print(f"[claude-notifier] Removed hook from {settings_path}")
                else:
                    print("[claude-notifier] No hook entry found in settings.json.")
        except (json.JSONDecodeError, OSError):
            print("[claude-notifier] Could not read settings.json — skipping hook cleanup.", file=sys.stderr)

    # ── 2. Unload and remove the launchd daemon (macOS only) ─────────────────
    if sys.platform == "darwin":
        daemon_label = "com.claude-notifier.log-watcher"
        daemon_plist = Path.home() / "Library" / "LaunchAgents" / f"{daemon_label}.plist"
        loaded = subprocess.run(
            ["launchctl", "list", daemon_label], capture_output=True
        ).returncode == 0
        if loaded:
            subprocess.run(
                ["launchctl", "bootout", f"gui/{os.getuid()}/{daemon_label}"],
                capture_output=True,
            )
            print("[claude-notifier] Stopped log-watcher daemon.")
        if daemon_plist.exists():
            daemon_plist.unlink()
            print(f"[claude-notifier] Removed {daemon_plist}")

    # ── 3. Remove files and package ──────────────────────────────────────────
    path_str = str(notifier_py).lower()
    is_homebrew = "cellar" in path_str or "homebrew" in path_str

    if is_homebrew:
        brew = shutil.which("brew")
        if brew:
            print("[claude-notifier] Running: brew uninstall claude-notifier")
            subprocess.run([brew, "uninstall", "claude-notifier"], check=False)
        else:
            print("[claude-notifier] brew not found — remove the formula manually.", file=sys.stderr)
    else:
        hooks_dir = Path.home() / ".claude" / "hooks"
        for name in ("claude-notifier.py", "log-watcher.py"):
            script = hooks_dir / name
            if script.exists():
                script.unlink()
                print(f"[claude-notifier] Removed {script}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    # Handle `claude-notifier uninstall` before argparse so it works naturally.
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        _do_uninstall()
        return

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--skip-if-focused", action="store_true")
    parser.add_argument("--test", action="store_true")
    args, _ = parser.parse_known_args()

    if args.test:
        notify("Claude Code — Test", "Notification delivery works ✓", "claude-notifier")
        return

    if sys.stdin.isatty():
        show_status()
        return

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if not isinstance(data, dict):
        sys.exit(0)

    if data.get("stop_hook_active") or (args.skip_if_focused and is_terminal_focused()):
        print(json.dumps({}))
        return

    lock = _acquire_lock()
    if lock is None:
        # Another instance is already delivering a notification — skip duplicate.
        print(json.dumps({}))
        return

    try:
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

        try:
            notify(title, message, subtitle)
        except Exception:  # noqa: BLE001
            pass  # delivery failure is non-fatal; hook must still exit cleanly
    finally:
        _release_lock(lock)

    print(json.dumps({}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        # Never let an unhandled exception crash the Claude Code hook runner.
        sys.exit(0)
