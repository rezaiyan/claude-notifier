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

    plist_label = "com.rezaiyan.claude-notifier-setup"

    # claude-notifier-setup: registers the hook, then cleans up the one-shot
    # LaunchAgent plist that post_install bootstraps to escape the sandbox.
    (bin/"claude-notifier-setup").write <<~SH
      #!/bin/bash
      python3 "#{libexec}/patch-settings.py" "#{libexec}/claude-notifier.py" || exit 1

      # Remove the one-shot LaunchAgent that post_install uses to escape the sandbox.
      plist="#{etc}/#{plist_label}.plist"
      if [[ -f "$plist" ]]; then
        launchctl bootout "gui/$(id -u)" "#{plist_label}" 2>/dev/null || true
        rm -f "$plist"
      fi

      # Only print the success box when running interactively.
      [[ -t 1 ]] || exit 0
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

  def post_install
    # Homebrew's sandbox blocks writes to ~/.claude/settings.json from post_install.
    # Workaround: bootstrap a one-shot LaunchAgent so launchd spawns claude-notifier-setup
    # outside the sandbox. The setup script cleans up the plist after it runs.
    home       = `echo $HOME`.chomp
    plist_label = "com.rezaiyan.claude-notifier-setup"
    plist_path  = etc/"#{plist_label}.plist"

    plist_path.write <<~XML
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>#{plist_label}</string>
        <key>ProgramArguments</key>
        <array>
          <string>#{bin}/claude-notifier-setup</string>
        </array>
        <key>EnvironmentVariables</key>
        <dict>
          <key>HOME</key>
          <string>#{home}</string>
          <key>PATH</key>
          <string>#{HOMEBREW_PREFIX}/bin:/usr/local/bin:/usr/bin:/bin</string>
        </dict>
        <key>RunAtLoad</key>
        <true/>
      </dict>
      </plist>
    XML

    # launchctl load uses the legacy Mach IPC path, which is reachable from
    # within Homebrew's sandbox (unlike bootstrap, which requires XPC to gui/UID).
    system "launchctl", "load", "-w", plist_path.to_s
  rescue StandardError
    nil
  end

  def caveats
    plist_pending = (etc/"com.rezaiyan.claude-notifier-setup.plist").exist?
    registered = begin
      require "json"
      settings = File.expand_path("~/.claude/settings.json")
      File.exist?(settings) &&
        JSON.parse(File.read(settings))
            .dig("hooks", "Stop")
            &.any? { |b| b["hooks"]&.any? { |h| h["command"]&.include?("claude-notifier") } }
    rescue StandardError
      false
    end

    if registered
      <<~EOS
        claude-notifier is active — you will be notified when Claude finishes or waits.

        To uninstall cleanly:
          claude-notifier-teardown && brew uninstall claude-notifier

        Optional – click notification to jump back to terminal:
          brew install terminal-notifier
      EOS
    elsif plist_pending
      <<~EOS
        claude-notifier is registering its hook in the background.
        If it does not complete, run once manually:
          claude-notifier-setup

        To uninstall cleanly:
          claude-notifier-teardown && brew uninstall claude-notifier
      EOS
    else
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
  end

  test do
    output = pipe_output(
      "python3 #{libexec}/claude-notifier.py",
      '{"last_assistant_message": "done", "stop_hook_active": true}'
    )
    assert_equal "{}", output.strip
  end
end
