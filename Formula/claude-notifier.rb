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
      exec python3 "#{libexec}/patch-settings.py" "#{libexec}/claude-notifier.py"
    SH

    (bin/"claude-notifier-teardown").write <<~SH
      #!/bin/bash
      exec python3 "#{libexec}/unpatch-settings.py" "#{libexec}/claude-notifier.py"
    SH
  end

  def caveats
    <<~EOS
      To register the Claude Code hook, run:
        claude-notifier-setup

      To uninstall cleanly:
        claude-notifier-teardown
        brew uninstall claude-notifier

      For click-to-focus notifications, also install terminal-notifier:
        brew install terminal-notifier
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
