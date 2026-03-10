import Foundation

enum SmartThingsError: LocalizedError {
    case notConfigured
    case httpError(Int)
    case decodingFailed
    var errorDescription: String? {
        switch self {
        case .notConfigured:     return "SmartThings token not set — open Settings"
        case .httpError(let c):  return "SmartThings API error (HTTP \(c))"
        case .decodingFailed:    return "Could not parse SmartThings response"
        }
    }
}

final class SmartThingsService {
    private let base = URL(string: "https://api.smartthings.com/v1")!
    var token: String = ""

    var isConfigured: Bool { !token.isEmpty }

    // MARK: - Device Discovery

    func discoverTVDevices() async throws -> [TVDevice] {
        let url = base.appendingPathComponent("devices")
        var req = URLRequest(url: url)
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let (data, response) = try await URLSession.shared.data(for: req)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else {
            throw SmartThingsError.httpError((response as? HTTPURLResponse)?.statusCode ?? 0)
        }
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let items = json["items"] as? [[String: Any]] else {
            throw SmartThingsError.decodingFailed
        }
        return items.compactMap { item -> TVDevice? in
            guard let deviceId = item["deviceId"] as? String,
                  let label    = item["label"] as? String,
                  let ocfDict  = item["ocf"] as? [String: Any],
                  let name     = ocfDict["n"] as? String,
                  name.lowercased().contains("samsung") else { return nil }
            return TVDevice(name: label, ipAddress: "", macAddress: "", smartThingsDeviceId: deviceId)
        }
    }

    // MARK: - Key Command

    func sendKeyCommand(_ key: RemoteKey, deviceId: String) async throws {
        let url = base
            .appendingPathComponent("devices")
            .appendingPathComponent(deviceId)
            .appendingPathComponent("commands")

        let body: [String: Any] = [
            "commands": [[
                "component":  "main",
                "capability": "samsungvd.remoteControl",
                "command":    "sendKey",
                "arguments":  [key.rawValue]
            ]]
        ]
        try await post(url: url, body: body)
    }

    // MARK: - Power

    func powerOn(deviceId: String) async throws {
        let url = base
            .appendingPathComponent("devices")
            .appendingPathComponent(deviceId)
            .appendingPathComponent("commands")
        let body: [String: Any] = [
            "commands": [[
                "component":  "main",
                "capability": "switch",
                "command":    "on",
                "arguments":  []
            ]]
        ]
        try await post(url: url, body: body)
    }

    func powerOff(deviceId: String) async throws {
        let url = base
            .appendingPathComponent("devices")
            .appendingPathComponent(deviceId)
            .appendingPathComponent("commands")
        let body: [String: Any] = [
            "commands": [[
                "component":  "main",
                "capability": "switch",
                "command":    "off",
                "arguments":  []
            ]]
        ]
        try await post(url: url, body: body)
    }

    // MARK: - App Launch

    func launchApp(_ app: TVApp, deviceId: String) async throws {
        let url = base
            .appendingPathComponent("devices")
            .appendingPathComponent(deviceId)
            .appendingPathComponent("commands")
        let body: [String: Any] = [
            "commands": [[
                "component":  "main",
                "capability": "custom.launchApp",
                "command":    "launchApp",
                "arguments":  [app.appId]
            ]]
        ]
        try await post(url: url, body: body)
    }

    // MARK: - Private

    private func post(url: URL, body: [String: Any]) async throws {
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        req.setValue("application/json",  forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: req)
        let code = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard code == 200 || code == 202 else {
            throw SmartThingsError.httpError(code)
        }
    }
}
