import Foundation
import SwiftUI

enum ConnectionState {
    case disconnected
    case connecting
    case connectedLocal
    case connectedCloud

    var label: String {
        switch self {
        case .disconnected:   return "Disconnected"
        case .connecting:     return "Connecting…"
        case .connectedLocal: return "Connected (Local)"
        case .connectedCloud: return "Connected (Cloud)"
        }
    }

    var color: Color {
        switch self {
        case .disconnected:   return .red
        case .connecting:     return .orange
        case .connectedLocal: return .green
        case .connectedCloud: return .yellow
        }
    }
}

/// Central coordinator for TV connectivity.
/// Tries local WebSocket first; falls back to SmartThings cloud automatically.
@MainActor
final class TVConnectionManager: ObservableObject {
    @Published var connectionState: ConnectionState = .disconnected
    @Published var currentTV: TVDevice?

    private var localService: LocalWebSocketService?
    let cloudService = SmartThingsService()
    private let wolService = WakeOnLANService()

    // MARK: - Connect

    func setTV(_ tv: TVDevice) {
        currentTV = tv
    }

    func connect() async {
        guard let tv = currentTV else { return }
        connectionState = .connecting

        do {
            let service = LocalWebSocketService(tv: tv)
            try await service.connect(timeout: 2.0)
            localService = service
            connectionState = .connectedLocal
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
