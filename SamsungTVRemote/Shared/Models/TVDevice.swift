import Foundation

struct TVDevice: Identifiable, Codable, Hashable {
    var id = UUID()
    var name: String
    var ipAddress: String
    var macAddress: String
    var pairingToken: String?
    var smartThingsDeviceId: String?

    var wsURL: URL? {
        let appName = "SamsungTVRemote".data(using: .utf8)!.base64EncodedString()
        var components = URLComponents()
        components.scheme = "ws"
        components.host = ipAddress
        components.port = 8001
        components.path = "/api/v2/channels/samsung.remote.control"
        var items = [URLQueryItem(name: "name", value: appName)]
        if let token = pairingToken {
            items.append(URLQueryItem(name: "token", value: token))
        }
        components.queryItems = items
        return components.url
    }
}
