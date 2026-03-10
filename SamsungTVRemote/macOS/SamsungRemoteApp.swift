import SwiftUI
import AppKit

@main
struct SamsungRemoteApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var connectionManager = TVConnectionManager()
    @StateObject private var settingsVM = SettingsViewModel()

    var body: some Scene {
        WindowGroup {
            RemoteControlView()
                .environmentObject(connectionManager)
                .environmentObject(settingsVM)
                .frame(width: 380, height: 680)
        }
        .windowResizability(.contentSize)
        .windowStyle(.hiddenTitleBar)

        // ⌘, opens Preferences
        Settings {
            SettingsView()
                .environmentObject(settingsVM)
                .environmentObject(connectionManager)
        }
    }
}

// MARK: - Menu Bar Support

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem?
    private var popover: NSPopover?
    private var connectionManager: TVConnectionManager?

    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMenuBar()
    }

    private func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        if let button = statusItem?.button {
            button.image = NSImage(systemSymbolName: "tv", accessibilityDescription: "Samsung TV Remote")
            button.action = #selector(togglePopover(_:))
            button.target = self
        }
    }

    @objc func togglePopover(_ sender: NSButton) {
        if let pop = popover, pop.isShown {
            pop.performClose(sender)
        } else {
            let pop = NSPopover()
            pop.contentSize = NSSize(width: 380, height: 680)
            pop.behavior = .transient
            // Mini remote reuses the same view
            let cm = TVConnectionManager()
            let sm = SettingsViewModel()
            pop.contentViewController = NSHostingController(
                rootView: RemoteControlView()
                    .environmentObject(cm)
                    .environmentObject(sm)
            )
            pop.show(relativeTo: sender.bounds, of: sender, preferredEdge: .minY)
            self.popover = pop
        }
    }
}
