import SwiftUI

@main
struct SamsungRemoteApp: App {
    @StateObject private var connectionManager = TVConnectionManager()
    @StateObject private var settingsVM = SettingsViewModel()

    var body: some Scene {
        WindowGroup {
            RemoteControlView()
                .environmentObject(connectionManager)
                .environmentObject(settingsVM)
        }
    }
}
