// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SamsungTVRemote",
    platforms: [
        .iOS(.v16),
        .macOS(.v13)
    ],
    products: [
        .library(name: "SamsungTVRemoteShared", targets: ["SamsungTVRemoteShared"])
    ],
    dependencies: [
        // WebSocket client — used by LocalWebSocketService as a fallback if
        // URLSessionWebSocketTask is unavailable on older OS versions.
        // Remove if targeting iOS 17+ / macOS 14+ exclusively.
        // .package(url: "https://github.com/daltoniam/Starscream.git", from: "4.0.6")
    ],
    targets: [
        .target(
            name: "SamsungTVRemoteShared",
            path: "Shared"
        ),
        .testTarget(
            name: "SamsungTVRemoteTests",
            dependencies: ["SamsungTVRemoteShared"],
            path: "Tests"
        )
    ]
)
