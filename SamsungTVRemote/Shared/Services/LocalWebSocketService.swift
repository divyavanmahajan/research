import Foundation

enum WSError: LocalizedError {
    case noURL
    case connectionTimeout
    case notConnected
    case needsPairing
    var errorDescription: String? {
        switch self {
        case .noURL:              return "Cannot build WebSocket URL — check TV IP address"
        case .connectionTimeout:  return "TV did not respond within timeout"
        case .notConnected:       return "WebSocket is not connected"
        case .needsPairing:       return "TV is waiting for you to accept the pairing request on screen"
        }
    }
}

/// Connects to a Samsung TV via its local WebSocket API.
/// Tries WSS port 8002 first (required for pairing popup on newer Tizen TVs),
/// then falls back to WS port 8001 for older firmware.
@MainActor
final class LocalWebSocketService: NSObject {
    private let tv: TVDevice
    private var task: URLSessionWebSocketTask?
    private var session: URLSession?
    private(set) var isConnected = false

    /// Called when the TV sends `ms.channel.unauthorized` (pairing popup is on screen).
    var onWaitingForPairing: (() -> Void)?

    init(tv: TVDevice) {
        self.tv = tv
    }

    /// Connects to the TV and returns the pairing token if one was issued.
    /// If the TV requires pairing, waits up to `pairingWindow` seconds for the
    /// user to accept the popup on screen, then reconnects automatically.
    @discardableResult
    func connect(timeout: TimeInterval = 5.0, pairingWindow: TimeInterval = 25.0) async throws -> String? {
        // Try WSS (port 8002) first, then fall back to WS (port 8001)
        let urls: [URL] = [tv.wsURL, tv.wsURLPlain].compactMap { $0 }
        guard !urls.isEmpty else { throw WSError.noURL }

        for url in urls {
            print("[WS] Trying \(url)")
            do {
                return try await attempt(url: url, timeout: timeout)
            } catch WSError.needsPairing {
                // TV showed popup — notify UI then wait for user to accept
                print("[WS] Pairing popup shown — waiting \(Int(pairingWindow))s for user acceptance")
                await MainActor.run { onWaitingForPairing?() }
                try await Task.sleep(nanoseconds: UInt64(pairingWindow * 1_000_000_000))
                return try await attempt(url: url, timeout: timeout)
            } catch {
                // Timeout or other error — try next URL
                continue
            }
        }
        throw WSError.connectionTimeout
    }

    private func attempt(url: URL, timeout: TimeInterval) async throws -> String? {
        // URLSession delegate to accept Samsung TV's self-signed TLS certificate
        let delegate = SamsungTLSDelegate()
        let cfg = URLSessionConfiguration.default
        let sess = URLSession(configuration: cfg, delegate: delegate, delegateQueue: nil)
        session = sess
        let t = sess.webSocketTask(with: url)
        task = t
        t.resume()

        return try await withThrowingTaskGroup(of: String?.self) { group in
            group.addTask {
                let msg = try await t.receive()
                guard case .string(let text) = msg else { return nil }

                if text.contains("ms.channel.connect") {
                    await MainActor.run { self.isConnected = true }
                    if let data = text.data(using: .utf8),
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                       let dataDict = json["data"] as? [String: Any],
                       let token = dataDict["token"] as? String {
                        print("[WS] Pairing token received: \(token)")
                        return token
                    }
                    return nil
                } else if text.contains("ms.channel.unauthorized") {
                    // TV is showing a pairing popup — signal this upward
                    throw WSError.needsPairing
                }
                return nil
            }
            group.addTask {
                try await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000))
                throw WSError.connectionTimeout
            }
            do {
                let token = try await group.next() ?? nil
                group.cancelAll()
                return token
            } catch {
                group.cancelAll()
                t.cancel(with: .goingAway, reason: nil)
                throw error
            }
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
        // Use REST POST — more reliable than WebSocket for app launch on Tizen
        guard let url = URL(string: "http://\(tv.ipAddress):8001/api/v2/applications/\(app.appId)") else {
            throw WSError.noURL
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        let (_, response) = try await URLSession.shared.data(for: req)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
    }

    func disconnect() {
        task?.cancel(with: .goingAway, reason: nil)
        isConnected = false
    }
}

// MARK: - TLS delegate (accepts Samsung TV self-signed certificate)

private final class SamsungTLSDelegate: NSObject, URLSessionDelegate {
    func urlSession(_ session: URLSession,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
           let trust = challenge.protectionSpace.serverTrust {
            completionHandler(.useCredential, URLCredential(trust: trust))
        } else {
            completionHandler(.performDefaultHandling, nil)
        }
    }
}
