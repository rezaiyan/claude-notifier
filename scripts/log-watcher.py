#!/usr/bin/env python3
"""Session-log watcher daemon — fires notifications when Claude finishes a turn.

Fallback for managed Macs where allowManagedHooksOnly blocks user hooks.
Watches ~/.claude/projects/**/*.jsonl for stop_hook_summary events and fires
desktop notifications via the claude-notifier notification stack.

Usage: python3 log-watcher.py <path-to-claude-notifier.py>
"""
import importlib.util
import json
import sys
import time
from pathlib import Path


def _load_notifier(notifier_path: str) -> object:
    """Import notify and helpers from claude-notifier.py at runtime."""
    spec = importlib.util.spec_from_file_location("claude_notifier", notifier_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {notifier_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _read_new_lines(filepath: Path, positions: dict) -> list[str]:
    """Return new lines appended to filepath since the last call.

    On first sight of a file, seeds the position to EOF so we don't replay
    history from before the daemon started.
    """
    try:
        size = filepath.stat().st_size
    except OSError:
        return []

    if filepath not in positions:
        positions[filepath] = size
        return []

    prev = positions[filepath]
    if size <= prev:
        positions[filepath] = size
        return []

    try:
        with open(filepath, "rb") as fh:
            fh.seek(prev)
            raw = fh.read(size - prev)
        positions[filepath] = size
        lines = raw.splitlines()
        return [ln.decode("utf-8", errors="replace") for ln in lines if ln.strip()]
    except OSError:
        return []


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: log-watcher.py <path-to-claude-notifier.py>", file=sys.stderr)
        sys.exit(1)

    notifier_path = sys.argv[1]
    try:
        mod = _load_notifier(notifier_path)
    except Exception as exc:
        print(f"[log-watcher] Failed to load notifier: {exc}", file=sys.stderr)
        sys.exit(1)

    notify = mod.notify  # type: ignore[attr-defined]
    extract_title = mod.extract_title  # type: ignore[attr-defined]
    waiting_signals = mod.WAITING_SIGNALS  # type: ignore[attr-defined]

    logs_root = Path.home() / ".claude" / "projects"

    # filepath -> byte offset of last read position
    positions: dict[Path, int] = {}
    # filepath -> (last_assistant_text, cwd) buffered until stop_hook_summary fires
    last_assistant: dict[Path, tuple[str, str]] = {}

    while True:
        try:
            jsonl_files = list(logs_root.rglob("*.jsonl"))
        except OSError:
            time.sleep(2)
            continue

        for filepath in jsonl_files:
            for line in _read_new_lines(filepath, positions):
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")

                if event_type == "assistant":
                    msg = event.get("message", {})
                    if msg.get("stop_reason") == "end_turn":
                        text = ""
                        for block in msg.get("content", []):
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                break
                        last_assistant[filepath] = (text, event.get("cwd", ""))

                elif event_type == "system" and event.get("subtype") == "stop_hook_summary":
                    text, cwd = last_assistant.pop(filepath, ("", event.get("cwd", "")))
                    cwd = cwd or event.get("cwd", "")
                    project = Path(cwd).name if cwd else "Claude Code"

                    is_waiting = any(s in text.lower() for s in waiting_signals)
                    if is_waiting:
                        title = "Claude Code — Waiting"
                        message = extract_title(text)
                        subtitle = f"{project}  ·  needs your input"
                    else:
                        title = "Claude Code — Done"
                        message = extract_title(text) if text else "Done"
                        subtitle = project

                    try:
                        notify(title, message, subtitle)
                    except Exception:
                        pass

        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"[log-watcher] Fatal: {exc}", file=sys.stderr)
        sys.exit(1)
