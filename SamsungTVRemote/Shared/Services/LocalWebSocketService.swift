import Foundation

enum WSError: LocalizedError {
    case noURL
    case connectionTimeout
    case notConnected
    var errorDescription: String? {
        switch self {
        case .noURL:              return "Cannot build WebSocket URL — check TV IP address"
        case .connectionTimeout:  return "TV did not respond within timeout"
        case .notConnected:       return "WebSocket is not connected"
        }
    }
}

/// Connects to a Samsung TV via its local WebSocket API (port 8001).
/// Uses Foundation's URLSessionWebSocketTask — no external dependencies.
@MainActor
final class LocalWebSocketService: NSObject {
    private let tv: TVDevice
    private var task: URLSessionWebSocketTask?
    private var session: URLSession?
    private(set) var isConnected = false

    init(tv: TVDevice) {
        self.tv = tv
    }

    func connect(timeout: TimeInterval = 2.0) async throws {
        guard let url = tv.wsURL else { throw WSError.noURL }

        session = URLSession(configuration: .default, delegate: nil, delegateQueue: nil)
        task = session?.webSocketTask(with: url)
        task?.resume()

        // Wait for first message (Samsung sends connection ack) as proxy for "connected"
        try await withThrowingTaskGroup(of: Void.self) { group in
            group.addTask {
                let msg = try await self.task!.receive()
                if case .string(let text) = msg, text.contains("ms.channel.connect") {
                    await MainActor.run { self.isConnected = true }
                    // Extract and persist pairing token if present
                    if let data = text.data(using: .utf8),
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                       let dataDict = json["data"] as? [String: Any],
                       let token = dataDict["token"] as? String {
                        // Token is stored by the caller (TVConnectionManager)
                        print("[WS] Pairing token received: \(token)")
                    }
                }
            }
            group.addTask {
                try await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000))
                throw WSError.connectionTimeout
            }
            try await group.next()
            group.cancelAll()
        }
    }

    func send(_ keyCode: String) async throws {
        guard isConnected, let task else { throw WSError.notConnected }
        let payload: [String: Any] = [
            "method": "ms.remote.control",
            "params": [
                "Cmd":          "Click",
                "DataOfCmd":    keyCode,
                "Option":       "false",
                "TypeOfRemote": "SendRemoteKey"
            ]
        ]
        let data = try JSONSerialization.data(withJSONObject: payload)
        let text = String(data: data, encoding: .utf8)!
        try await task.send(.string(text))
    }

    func launchApp(_ app: TVApp) async throws {
        guard isConnected, let task else { throw WSError.notConnected }
        let payload: [String: Any] = [
            "method": "ms.channel.emit",
            "params": [
                "event": "ed.apps.launch",
                "to":    "host",
                "data": [
                    "appId":       app.appId,
                    "action_type": "NATIVE_LAUNCH"
                ]
            ]
        ]
        let data = try JSONSerialization.data(withJSONObject: payload)
        try await task.send(.string(String(data: data, encoding: .utf8)!))
    }

    func disconnect() {
        task?.cancel(with: .goingAway, reason: nil)
        isConnected = false
    }
}
