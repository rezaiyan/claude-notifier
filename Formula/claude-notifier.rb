class ClaudeNotifier < Formula
  desc "Desktop notifications for Claude Code — done and waiting alerts"
  homepage "https://github.com/rezaiyan/claude-notifier"
  # Update url and sha256 on each release:
  #   url "https://github.com/rezaiyan/claude-notifier/archive/refs/tags/v1.0.0.tar.gz"
  #   sha256 "<run `brew fetch --build-from-source` to get this>"
  head "https://github.com/rezaiyan/claude-notifier.git", branch: "main"

  license "MIT"
  depends_on :macos

  # terminal-notifier is optional: the hook falls back to osascript without it
  # but click-to-focus requires it.
  # depends_on "terminal-notifier" => :optional

  def install
    libexec.install "claude-notifier.py"
    libexec.install "scripts/patch-settings.py"
    libexec.install "scripts/unpatch-settings.py"
  end

  # Runs as the installing user (not root), so Path.home() is correct.
  def post_install
    system "python3", "#{libexec}/patch-settings.py", "#{libexec}/claude-notifier.py"
  end

  def caveats
    <<~EOS
      claude-notifier has been registered as a Claude Code Stop hook.

      To uninstall cleanly, remove the hook entry from settings.json first:
        python3 #{opt_libexec}/unpatch-settings.py #{opt_libexec}/claude-notifier.py

      Then uninstall: brew uninstall claude-notifier

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
