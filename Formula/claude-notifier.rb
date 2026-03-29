class ClaudeNotifier < Formula
  desc "Desktop notifications for Claude Code — done and waiting alerts"
  homepage "https://github.com/rezaiyan/claude-notifier"
  url "https://github.com/rezaiyan/claude-notifier/archive/refs/tags/v0.0.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  version "0.0.0"
  license "MIT"
  head "https://github.com/rezaiyan/claude-notifier.git", branch: "main"

  depends_on :macos

  def install
    libexec.install "claude-notifier.py"
    libexec.install "scripts/patch-settings.py"
    libexec.install "scripts/unpatch-settings.py"

    # Bin wrappers run in the user's shell context (no sandbox), so they can
    # write to ~/.claude/settings.json — unlike post_install which is sandboxed.
    (bin/"claude-notifier-setup").write <<~SH
      #!/bin/bash
      python3 "#{libexec}/patch-settings.py" "#{libexec}/claude-notifier.py" || exit 1
      BOLD="\\033[1m" GREEN="\\033[0;32m" CYAN="\\033[0;36m" YELLOW="\\033[1;33m" DIM="\\033[2m" NC="\\033[0m"
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
    SH

    (bin/"claude-notifier-teardown").write <<~SH
      #!/bin/bash
      exec python3 "#{libexec}/unpatch-settings.py" "#{libexec}/claude-notifier.py"
    SH
  end

  def caveats
    <<~EOS
      ┌─────────────────────────────────────────────────────┐
      │  ⚡ One more step to activate claude-notifier       │
      └─────────────────────────────────────────────────────┘

        claude-notifier-setup

      Registers the hook in ~/.claude/settings.json.
      Every Claude Code session will then notify you when
      Claude finishes a task or needs your input.

      ─────────────────────────────────────────────────────
      To uninstall cleanly:
        claude-notifier-teardown && brew uninstall claude-notifier

      Optional – click notification to jump back to terminal:
        brew install terminal-notifier
      ─────────────────────────────────────────────────────
    EOS
  end

  test do
    output = pipe_output(
      "python3 #{libexec}/claude-notifier.py",
      '{"last_assistant_message": "done", "stop_hook_active": true}'
    )
    assert_equal "{}", output.strip
  end
end
