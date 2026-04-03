"""Tests for claude-notifier.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

from conftest import load_module

cn = load_module("claude_notifier", "claude-notifier.py")


# ── extract_title ─────────────────────────────────────────────────────────────

def test_extract_title_empty() -> None:
    assert cn.extract_title("") == "Done"


def test_extract_title_short_line_ignored() -> None:
    # Lines under 8 chars are skipped
    assert cn.extract_title("ok") == "Done"


def test_extract_title_first_long_line() -> None:
    assert cn.extract_title("Here is a summary of the work done") == "Here is a summary of the work done"


def test_extract_title_strips_markdown() -> None:
    result = cn.extract_title("**Bold heading** with `code`")
    assert "*" not in result
    assert "`" not in result


def test_extract_title_truncates_long_lines() -> None:
    long = "A" * 60
    result = cn.extract_title(long)
    assert len(result) <= 56  # 55 chars + ellipsis


def test_extract_title_uses_first_meaningful_line() -> None:
    msg = "\n\nok\n\nHere is the real title line that matters\nSecond line"
    assert cn.extract_title(msg) == "Here is the real title line that matters"


# ── _check_setup ─────────────────────────────────────────────────────────────

def test_check_setup_not_registered(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": []}]}}))
    with patch.object(Path, "home", return_value=tmp_path):
        is_reg, path = cn._check_setup()
    assert not is_reg
    assert path == ""


def test_check_setup_registered(tmp_path: Path) -> None:
    notifier = "/hooks/claude-notifier.py"
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({
        "hooks": {"Stop": [{"hooks": [
            {"type": "command",
             "command": f'[ -f "{notifier}" ] && python3 "{notifier}" || true'}
        ]}]}
    }))
    with patch.object(Path, "home", return_value=tmp_path):
        is_reg, path = cn._check_setup()
    assert is_reg
    assert path == notifier


def test_check_setup_missing_file(tmp_path: Path) -> None:
    with patch.object(Path, "home", return_value=tmp_path):
        is_reg, path = cn._check_setup()
    assert not is_reg


# ── _check_managed_hooks_only ─────────────────────────────────────────────────

def test_check_managed_hooks_only_false(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({}))
    with patch.object(Path, "home", return_value=tmp_path):
        assert cn._check_managed_hooks_only() is False


def test_check_managed_hooks_only_true(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"allowManagedHooksOnly": True}))
    with patch.object(Path, "home", return_value=tmp_path):
        assert cn._check_managed_hooks_only() is True


# ── bundled app path resolution ───────────────────────────────────────────────

def test_bundled_app_path_homebrew_layout(tmp_path: Path) -> None:
    """
    In the Homebrew layout, claude-notifier.py lives at prefix/libexec/claude-notifier.py
    and ClaudeNotifier.app lives at prefix/ClaudeNotifier.app.
    parent.parent of the script must resolve to prefix/.
    """
    libexec = tmp_path / "libexec"
    libexec.mkdir()
    script = libexec / "claude-notifier.py"
    script.write_text("# fake")

    app_bin = tmp_path / "ClaudeNotifier.app" / "Contents" / "MacOS" / "ClaudeNotifier"
    app_bin.parent.mkdir(parents=True)
    app_bin.write_text("#!/bin/bash")

    # Simulate path resolution as done in _macos_notify()
    bundled = script.resolve().parent.parent / "ClaudeNotifier.app/Contents/MacOS/ClaudeNotifier"
    assert bundled == app_bin.resolve(), (
        f"Expected bundled app at {app_bin}, resolved to {bundled}. "
        "Homebrew layout: script must be in libexec/ subdir alongside ClaudeNotifier.app."
    )


def test_bundled_app_path_repo_root_layout_fails(tmp_path: Path) -> None:
    """
    When claude-notifier.py sits directly at repo root (not in libexec/),
    parent.parent resolves ABOVE the repo — ClaudeNotifier.app won't be found there.
    This test documents the known limitation that drives the smoke-test layout fix.
    """
    script = tmp_path / "claude-notifier.py"
    script.write_text("# fake")

    app_bin = tmp_path / "ClaudeNotifier.app" / "Contents" / "MacOS" / "ClaudeNotifier"
    app_bin.parent.mkdir(parents=True)
    app_bin.write_text("#!/bin/bash")

    bundled = script.resolve().parent.parent / "ClaudeNotifier.app/Contents/MacOS/ClaudeNotifier"
    # bundled is now in tmp_path's PARENT, not in tmp_path — wrong location
    assert not bundled.exists(), (
        "When script is at repo root (not libexec/), the app lookup escapes the project dir. "
        "smoke-test.sh --local must copy script into a libexec/ subdir."
    )


# ── hook lock ─────────────────────────────────────────────────────────────────

def test_acquire_release_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "test.lock"
    with patch.object(cn, "_LOCK_PATH", lock_path):
        lf = cn._acquire_lock()
        assert lf is not None
        # Second acquire should fail (lock is held)
        lf2 = cn._acquire_lock()
        assert lf2 is None
        cn._release_lock(lf)
        # After release, acquire should succeed again
        lf3 = cn._acquire_lock()
        assert lf3 is not None
        cn._release_lock(lf3)


# ── stop_hook_active short-circuit ────────────────────────────────────────────

def test_stop_hook_active_outputs_empty_json(tmp_path: Path, capsys) -> None:
    """When stop_hook_active is true the hook must output {} and exit cleanly."""
    input_data = json.dumps({"last_assistant_message": "done", "stop_hook_active": True})
    with patch.object(sys, "argv", ["claude-notifier.py"]), \
         patch("sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = input_data
        # Make json.load work with our mock
        import io
        real_stdin = io.StringIO(input_data)
        with patch("sys.stdin", real_stdin):
            cn.main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "{}"
