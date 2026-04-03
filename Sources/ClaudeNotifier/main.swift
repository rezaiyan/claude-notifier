import AppKit
import UserNotifications

// MARK: - Argument parsing

private struct NotifArgs {
    var title    = "Claude Code"
    var message  = ""
    var subtitle = ""
}

private func parseArgs() -> NotifArgs {
    var args = NotifArgs()
    let argv = CommandLine.arguments
    var i = 1
    while i + 1 < argv.count {
        switch argv[i] {
        case "-title":    args.title    = argv[i + 1]
        case "-message":  args.message  = argv[i + 1]
        case "-subtitle": args.subtitle = argv[i + 1]
        default: break
        }
        i += 2
    }
    return args
}

// MARK: - App delegate

private class Delegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_: Notification) {
        // Safety: always exit within 10 s even if notification center hangs
        DispatchQueue.main.asyncAfter(deadline: .now() + 10) { NSApp.terminate(nil) }

        let args = parseArgs()
        let center = UNUserNotificationCenter.current()

        // Check current authorization status before hiding from the Dock.
        // If permission is already determined, go background immediately (no
        // Dock icon). If not yet determined, stay visible as a regular app so
        // macOS shows the "Allow Notifications?" dialog — setting .prohibited
        // before requestAuthorization causes macOS 26 to treat the request as
        // coming from a background agent and silently skip the prompt.
        center.getNotificationSettings { settings in
            if settings.authorizationStatus != .notDetermined {
                DispatchQueue.main.async { NSApp.setActivationPolicy(.prohibited) }
            }

            center.requestAuthorization(options: [.alert, .sound]) { granted, _ in
                // Hide from Dock now that the dialog (if any) is dismissed.
                DispatchQueue.main.async { NSApp.setActivationPolicy(.prohibited) }

                guard granted else {
                    DispatchQueue.main.async { NSApp.terminate(nil) }
                    return
                }

                let content         = UNMutableNotificationContent()
                content.title       = args.title
                content.body        = args.message
                content.subtitle    = args.subtitle
                content.sound       = .default

                let request = UNNotificationRequest(
                    identifier: UUID().uuidString,
                    content: content,
                    trigger: nil
                )
                // Block until the request is handed off (max 3 s) so the app
                // doesn't exit before macOS records the delivery attempt.
                let sema = DispatchSemaphore(value: 0)
                center.add(request) { error in
                    if error == nil,
                       let sigPath = ProcessInfo.processInfo.environment["CLAUDE_NOTIFIER_SIGNAL_FILE"] {
                        // Create signal file so the Python caller knows delivery
                        // succeeded.  stdout is not captured (would sever the PTY
                        // and break the window-server session), so a file is used.
                        FileManager.default.createFile(atPath: sigPath, contents: Data())
                    }
                    sema.signal()
                }
                _ = sema.wait(timeout: .now() + 3)
                DispatchQueue.main.async { NSApp.terminate(nil) }
            }
        }
    }
}

// MARK: - Entry point

private let app      = NSApplication.shared
private let delegate = Delegate()
app.delegate = delegate
app.run()
