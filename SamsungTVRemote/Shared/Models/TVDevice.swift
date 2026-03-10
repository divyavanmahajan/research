import Foundation

struct TVDevice: Identifiable, Codable, Hashable {
    var id = UUID()
    var name: String
    var ipAddress: String
    var macAddress: String
    var pairingToken: String?
    var smartThingsDeviceId: String?

    /// WSS on port 8002 (preferred — newer Tizen TVs require TLS for pairing popup).
    var wsURL: URL? { makeWSURL(secure: true) }
    /// WS on port 8001 (fallback for older firmware).
    var wsURLPlain: URL? { makeWSURL(secure: false) }

    private func makeWSURL(secure: Bool) -> URL? {
        let appName = "SamsungTVRemote".data(using: .utf8)!.base64EncodedString()
        var components = URLComponents()
        components.scheme = secure ? "wss" : "ws"
        components.host = ipAddress
        components.port = secure ? 8002 : 8001
        components.path = "/api/v2/channels/samsung.remote.control"
        var items = [URLQueryItem(name: "name", value: appName)]
        if let token = pairingToken {
            items.append(URLQueryItem(name: "token", value: token))
        }
        components.queryItems = items
        return components.url
    }
}
