import Foundation

@MainActor
final class RemoteViewModel: ObservableObject {
    // Convenience wrapper so Views don't need to hold the manager directly
    func sendKey(_ key: RemoteKey, via manager: TVConnectionManager) async {
        await manager.send(key: key)
    }

    func launchApp(_ app: TVApp, via manager: TVConnectionManager) async {
        await manager.launch(app: app)
    }
}
