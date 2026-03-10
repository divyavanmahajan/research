import Foundation
import CoreTransferable
import UniformTypeIdentifiers

struct TVApp: Identifiable, Codable, Hashable, Transferable {
    var id = UUID()
    var name: String
    var appId: String
    var icon: String  // SF Symbol or asset name

    static var transferRepresentation: some TransferRepresentation {
        CodableRepresentation(contentType: .data)
    }

    // Prefix "__key:" means send a remote key instead of launching via REST.
    // TVConnectionManager.launch(app:) handles this convention.
    static let knownApps: [TVApp] = [
        TVApp(name: "Live TV",     appId: "__key:KEY_TV",   icon: "antenna.radiowaves.left.and.right"),
        TVApp(name: "Netflix",     appId: "3201907018807",  icon: "play.rectangle.fill"),
        TVApp(name: "YouTube",     appId: "111299001912",   icon: "play.circle.fill"),
        TVApp(name: "Disney+",     appId: "3201901017640",  icon: "sparkles.tv.fill"),
        TVApp(name: "Prime Video", appId: "3201910019365",  icon: "shippingbox.fill"),
        TVApp(name: "Apple TV+",   appId: "3201807016597",  icon: "appletv.fill"),
        TVApp(name: "Spotify",     appId: "3201606009684",  icon: "music.note"),
    ]
}
