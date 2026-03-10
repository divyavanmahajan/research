// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SamsungTVRemote",
    platforms: [
        .iOS(.v16),
        .macOS(.v14)
    ],
    products: [
        .executable(name: "SamsungRemote-macOS", targets: ["SamsungRemote-macOS"]),
        .executable(name: "SamsungRemote-iOS",   targets: ["SamsungRemote-iOS"]),
    ],
    dependencies: [
        // WebSocket client — used by LocalWebSocketService as a fallback if
        // URLSessionWebSocketTask is unavailable on older OS versions.
        // Remove if targeting iOS 17+ / macOS 14+ exclusively.
        // .package(url: "https://github.com/daltoniam/Starscream.git", from: "4.0.6")
    ],
    targets: [
        // Shared library — compiled once per platform, referenced by both executables.
        // Avoids the "overlapping sources" error when xcodebuild resolves the full
        // package graph for both targets simultaneously.
        .target(
            name: "SamsungTVRemoteShared",
            path: "Shared"
        ),

        .executableTarget(
            name: "SamsungRemote-macOS",
            dependencies: ["SamsungTVRemoteShared"],
            path: ".",
            exclude: [
                "iOS", "Shared", "simulator", "Package.swift",
                "build.sh", "tv_test.swift", "samsung-tv.swift",
                "SAMSUNG_TV_CLI.md", "instructions.md",
            ],
            sources: ["macOS"],
            swiftSettings: [.define("os_macOS")]
        ),
        .executableTarget(
            name: "SamsungRemote-iOS",
            dependencies: ["SamsungTVRemoteShared"],
            path: ".",
            exclude: [
                "macOS", "Shared", "simulator", "Package.swift",
                "build.sh", "tv_test.swift", "samsung-tv.swift",
                "SAMSUNG_TV_CLI.md", "instructions.md",
            ],
            sources: ["iOS"],
            swiftSettings: [.define("os_iOS")]
        ),
        // .testTarget(
        //     name: "SamsungTVRemoteTests",
        //     dependencies: ["SamsungTVRemoteShared"],
        //     path: "Tests"
        // )
    ]
)
