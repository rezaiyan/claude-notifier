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
        NSApp.setActivationPolicy(.prohibited)

        // Safety: always exit within 10 s even if notification center hangs
        DispatchQueue.main.asyncAfter(deadline: .now() + 10) { NSApp.terminate(nil) }

        let args = parseArgs()
        let center = UNUserNotificationCenter.current()

        center.requestAuthorization(options: [.alert, .sound]) { granted, _ in
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
            center.add(request) { _ in
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
