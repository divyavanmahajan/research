import Foundation

struct TVApp: Identifiable, Codable, Hashable, Transferable {
    var id = UUID()
    var name: String
    var appId: String
    var icon: String  // SF Symbol or asset name

    static var transferRepresentation: some TransferRepresentation {
        CodableRepresentation(contentType: .data)
    }

    static let knownApps: [TVApp] = [
        TVApp(name: "Netflix",     appId: "11101200001",    icon: "play.rectangle.fill"),
        TVApp(name: "YouTube",     appId: "111299001912",   icon: "play.circle.fill"),
        TVApp(name: "Disney+",     appId: "MCmYXNxgcu",    icon: "sparkles.tv.fill"),
        TVApp(name: "Prime Video", appId: "3201910019365",  icon: "shippingbox.fill"),
        TVApp(name: "Hulu",        appId: "3201601007625",  icon: "film.fill"),
        TVApp(name: "Apple TV+",   appId: "com.apple.appletv", icon: "appletv.fill"),
    ]
}
