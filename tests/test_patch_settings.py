"""Tests for scripts/patch-settings.py."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import load_module

REPO = Path(__file__).parent.parent
PATCH_SETTINGS = REPO / "scripts" / "patch-settings.py"
SYSTEM_PYTHON = "/usr/bin/python3"

ps = load_module("patch_settings", "scripts/patch-settings.py")


# ── Python 3.9 compatibility (system python3) ─────────────────────────────────

@pytest.mark.skipif(
    not Path(SYSTEM_PYTHON).exists(),
    reason=f"{SYSTEM_PYTHON} not present",
)
def test_patch_settings_importable_on_system_python() -> None:
    """patch-settings.py must import cleanly on the macOS system Python (3.9).

    'str | None' union syntax requires Python 3.10+ unless
    'from __future__ import annotations' is present.
    """
    result = subprocess.run(
        [SYSTEM_PYTHON, "-c", f"import importlib.util; "
         f"spec = importlib.util.spec_from_file_location('ps', '{PATCH_SETTINGS}'); "
         f"mod = importlib.util.module_from_spec(spec); "
         f"spec.loader.exec_module(mod)"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"patch-settings.py fails to import on {SYSTEM_PYTHON}:\n{result.stderr}"
    )


# ── _register_hook ────────────────────────────────────────────────────────────

def test_register_hook_fresh(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    ps._register_hook(settings, "/hooks/claude-notifier.py", [])
    data = json.loads(settings.read_text())
    hooks = data["hooks"]["Stop"][0]["hooks"]
    assert len(hooks) == 1
    assert "claude-notifier.py" in hooks[0]["command"]
    assert hooks[0]["type"] == "command"


def test_register_hook_idempotent(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    ps._register_hook(settings, "/hooks/claude-notifier.py", [])
    ps._register_hook(settings, "/hooks/claude-notifier.py", [])
    data = json.loads(settings.read_text())
    hooks = data["hooks"]["Stop"][0]["hooks"]
    notifier_hooks = [h for h in hooks if "claude-notifier.py" in h.get("command", "")]
    assert len(notifier_hooks) == 1, "idempotent: should not duplicate the hook"


def test_register_hook_replaces_stale(tmp_path: Path) -> None:
    """A hook pointing to an old versioned path must be replaced, not duplicated."""
    settings = tmp_path / "settings.json"
    # Simulate an older versioned Cellar hook
    old_path = "/opt/homebrew/Cellar/claude-notifier/1.2.1/libexec/claude-notifier.py"
    old_guarded = f'[ -f "{old_path}" ] && python3 "{old_path}" || true'
    settings.write_text(json.dumps({
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": old_guarded}]}]}
    }))

    new_path = "/opt/homebrew/opt/claude-notifier/libexec/claude-notifier.py"
    ps._register_hook(settings, new_path, [])

    data = json.loads(settings.read_text())
    hooks = data["hooks"]["Stop"][0]["hooks"]
    notifier_hooks = [h for h in hooks if "claude-notifier.py" in h.get("command", "")]
    assert len(notifier_hooks) == 1, "stale hook must be replaced, not left alongside new one"
    assert new_path in notifier_hooks[0]["command"]
    assert "1.2.1" not in notifier_hooks[0]["command"]


def test_register_hook_preserves_other_hooks(tmp_path: Path) -> None:
    """Other hooks in the same Stop group must not be touched."""
    settings = tmp_path / "settings.json"
    other = {"type": "command", "command": 'echo "other hook"'}
    settings.write_text(json.dumps({
        "hooks": {"Stop": [{"hooks": [other]}]}
    }))
    ps._register_hook(settings, "/hooks/claude-notifier.py", [])
    data = json.loads(settings.read_text())
    hooks = data["hooks"]["Stop"][0]["hooks"]
    commands = [h["command"] for h in hooks]
    assert 'echo "other hook"' in commands


def test_register_hook_guard_syntax(tmp_path: Path) -> None:
    """Written command must be the guard-wrapped form."""
    settings = tmp_path / "settings.json"
    hook_path = "/hooks/claude-notifier.py"
    ps._register_hook(settings, hook_path, [])
    data = json.loads(settings.read_text())
    cmd = data["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert cmd == f'[ -f "{hook_path}" ] && python3 "{hook_path}" || true'


def test_register_hook_with_extra_args(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    hook_path = "/hooks/claude-notifier.py"
    ps._register_hook(settings, hook_path, ["--skip-if-focused"])
    data = json.loads(settings.read_text())
    cmd = data["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert "--skip-if-focused" in cmd


def test_register_hook_invalid_json_backup(tmp_path: Path) -> None:
    """Invalid JSON in settings.json is backed up and overwritten cleanly."""
    settings = tmp_path / "settings.json"
    settings.write_text("{not valid json}")
    ps._register_hook(settings, "/hooks/claude-notifier.py", [])
    assert (tmp_path / "settings.json.bak").exists()
    data = json.loads(settings.read_text())
    assert "hooks" in data


# ── _parse_args ───────────────────────────────────────────────────────────────

def test_parse_args_basic() -> None:
    with patch.object(sys, "argv", ["patch-settings.py", "/path/notifier.py"]):
        notifier, watcher, extra = ps._parse_args()
    assert notifier == "/path/notifier.py"
    assert watcher is None
    assert extra == []


def test_parse_args_with_watcher() -> None:
    with patch.object(sys, "argv", [
        "patch-settings.py", "/path/notifier.py",
        "--watcher", "/path/watcher.py",
    ]):
        notifier, watcher, extra = ps._parse_args()
    assert notifier == "/path/notifier.py"
    assert watcher == "/path/watcher.py"
    assert extra == []


def test_parse_args_extra_args() -> None:
    with patch.object(sys, "argv", [
        "patch-settings.py", "/path/notifier.py", "--skip-if-focused",
    ]):
        notifier, watcher, extra = ps._parse_args()
    assert extra == ["--skip-if-focused"]


def test_parse_args_no_args_exits() -> None:
    with patch.object(sys, "argv", ["patch-settings.py"]):
        with pytest.raises(SystemExit):
            ps._parse_args()


# ── upgrade-safe hook path ────────────────────────────────────────────────────

def test_hook_cellar_path_becomes_stale_on_version_bump(tmp_path: Path) -> None:
    """
    Simulates a brew upgrade: hook was written with v1.2.1 Cellar path,
    then setup runs with v1.2.2 Cellar path. The old entry is stale and
    must be replaced — confirming that versioned Cellar paths are NOT
    upgrade-safe and require re-running setup after every upgrade.
    """
    settings = tmp_path / "settings.json"

    old_path = "/opt/homebrew/Cellar/claude-notifier/1.2.1/libexec/claude-notifier.py"
    ps._register_hook(settings, old_path, [])

    # Simulate upgrade: setup now runs with 1.2.2 versioned path
    new_cellar_path = "/opt/homebrew/Cellar/claude-notifier/1.2.2/libexec/claude-notifier.py"
    ps._register_hook(settings, new_cellar_path, [])

    data = json.loads(settings.read_text())
    hooks = data["hooks"]["Stop"][0]["hooks"]
    notifier_hooks = [h for h in hooks if "claude-notifier.py" in h.get("command", "")]
    # There should be exactly one hook, with the NEW version
    assert len(notifier_hooks) == 1
    assert "1.2.2" in notifier_hooks[0]["command"]
    # Confirms versioned paths require re-running setup after each upgrade


def test_hook_opt_path_survives_version_bump(tmp_path: Path) -> None:
    """
    When setup registers the hook with the stable opt symlink path,
    running setup again (after a brew upgrade) detects no staleness and
    returns immediately — no re-registration needed.
    This is the correct behavior when using #{opt_prefix}/libexec in the Formula.
    """
    settings = tmp_path / "settings.json"
    opt_path = "/opt/homebrew/opt/claude-notifier/libexec/claude-notifier.py"

    ps._register_hook(settings, opt_path, [])

    # Simulate: even after upgrade, the opt path is still the same
    ps._register_hook(settings, opt_path, [])

    data = json.loads(settings.read_text())
    hooks = data["hooks"]["Stop"][0]["hooks"]
    notifier_hooks = [h for h in hooks if "claude-notifier.py" in h.get("command", "")]
    assert len(notifier_hooks) == 1
    assert "opt/claude-notifier" in notifier_hooks[0]["command"]
    assert "/Cellar/" not in notifier_hooks[0]["command"]
