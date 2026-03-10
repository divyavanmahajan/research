import Foundation
import SwiftUI

enum ConnectionState {
    case disconnected
    case connecting
    case waitingForPairing
    case connectedLocal
    case connectedCloud

    var label: String {
        switch self {
        case .disconnected:      return "Disconnected"
        case .connecting:        return "Connecting…"
        case .waitingForPairing: return "Accept pairing on TV screen…"
        case .connectedLocal:    return "Connected (Local)"
        case .connectedCloud:    return "Connected (Cloud)"
        }
    }

    var color: Color {
        switch self {
        case .disconnected:      return .red
        case .connecting:        return .orange
        case .waitingForPairing: return .blue
        case .connectedLocal:    return .green
        case .connectedCloud:    return .yellow
        }
    }
}

/// Central coordinator for TV connectivity.
/// Tries local WebSocket first; falls back to SmartThings cloud automatically.
@MainActor
package final class TVConnectionManager: ObservableObject {
    package init() {}

    @Published var connectionState: ConnectionState = .disconnected
    @Published var currentTV: TVDevice?

    private var localService: LocalWebSocketService?
    let cloudService = SmartThingsService()
    private let wolService = WakeOnLANService()

    /// Called whenever a TVDevice is mutated (e.g. pairing token saved). Use this to
    /// persist the update back to SettingsViewModel without creating a direct dependency.
    var onDeviceUpdated: ((TVDevice) -> Void)?

    // MARK: - Connect

    func setTV(_ tv: TVDevice) {
        currentTV = tv
    }

    func disconnect() {
        localService?.disconnect()
        localService = nil
        connectionState = .disconnected
    }

    /// Selects a TV and immediately tries to connect to it.
    func selectAndConnect(_ tv: TVDevice) async {
        localService?.disconnect()
        localService = nil
        connectionState = .disconnected
        setTV(tv)
        await connect()
    }

    func connect() async {
        guard let tv = currentTV else { return }
        connectionState = .connecting

        do {
            let service = LocalWebSocketService(tv: tv)
            service.onWaitingForPairing = { [weak self] in
                self?.connectionState = .waitingForPairing
            }
            let token = try await service.connect(timeout: 5.0)
            localService = service
            connectionState = .connectedLocal

            // Persist the pairing token if the TV issued one (or a new one)
            if let token, token != currentTV?.pairingToken {
                currentTV?.pairingToken = token
                if let updated = currentTV {
                    onDeviceUpdated?(updated)
                }
            }
        } catch {
            print("[TVConnectionManager] Local WS failed: \(error.localizedDescription)")
            localService = nil
            connectionState = cloudService.isConfigured ? .connectedCloud : .disconnected
        }
    }

    // MARK: - Send Key

    func send(key: RemoteKey) async {
        if connectionState == .connectedLocal {
            do {
                try await localService?.send(key.rawValue)
                return
            } catch {
                print("[TVConnectionManager] Local send failed, switching to cloud: \(error)")
                connectionState = cloudService.isConfigured ? .connectedCloud : .disconnected
            }
        }

        if let deviceId = currentTV?.smartThingsDeviceId, connectionState == .connectedCloud {
            try? await cloudService.sendKeyCommand(key, deviceId: deviceId)
        }
    }

    // MARK: - Launch App

    func launch(app: TVApp) async {
        // Apps prefixed with "__key:" send a key press instead of a REST app launch
        if app.appId.hasPrefix("__key:") {
            let keyCode = String(app.appId.dropFirst("__key:".count))
            if let key = RemoteKey(rawValue: keyCode) {
                await send(key: key)
            }
            return
        }

        if connectionState == .connectedLocal {
            do {
                try await localService?.launchApp(app)
                return
            } catch {
                connectionState = cloudService.isConfigured ? .connectedCloud : .disconnected
            }
        }
        if let deviceId = currentTV?.smartThingsDeviceId {
            try? await cloudService.launchApp(app, deviceId: deviceId)
        }
    }

    // MARK: - Power

    func togglePower() async {
        guard let tv = currentTV else { return }

        if connectionState == .disconnected || connectionState == .connectedCloud {
            // TV likely off — send Wake-on-LAN
            try? wolService.send(macAddress: tv.macAddress)
            #if os(macOS)
            // Retry WoL 3 times for macOS (TV may be in deeper sleep)
            for _ in 0..<2 {
                try? await Task.sleep(for: .seconds(2))
                try? wolService.send(macAddress: tv.macAddress)
            }
            #endif
            // Wait for TV to boot then reconnect
            try? await Task.sleep(for: .seconds(8))
            await connect()
        } else {
            // TV is on — send power off
            await send(key: .power)
            connectionState = .disconnected
            localService = nil
        }
    }
}
