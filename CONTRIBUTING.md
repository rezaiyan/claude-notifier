# Contributing

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include your OS, terminal emulator, and the output of running the hook manually:

```bash
echo '{"last_assistant_message": "done", "stop_hook_active": false}' \
  | python3 ~/.claude/hooks/claude-notifier.py
```

## Pull requests

1. Fork the repo and create a branch from `main`
2. Keep changes focused — one fix or feature per PR
3. Run `ruff check .` before submitting (zero errors required)
4. Test on the OS(es) your change affects

## Adding terminal emulator support

`KNOWN_TERMINALS_MACOS` and `KNOWN_TERMINALS_LINUX` in `claude-notifier.py` are the two places to add new terminals. For macOS, you need the app name and bundle ID (find it with `osascript -e 'id of app "YourTerminal"'`). For Linux, add a lowercase substring of the window title.

## Scope

This is intentionally a small, dependency-light tool. PRs that add pip dependencies or significantly expand scope are unlikely to be merged.
