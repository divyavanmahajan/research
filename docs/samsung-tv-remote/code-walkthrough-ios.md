# Samsung TV Remote — iOS Code Walkthrough (Linear)

**Version:** 1.0
**Purpose:** Step-by-step trace of every code path from app launch to a key press being sent to the TV.

---

## 1. App Entry Point: `iOS/SamsungRemoteApp.swift`

The app starts here. SwiftUI's `@main` attribute designates this as the entry point.

```swift
@main
struct SamsungRemoteApp: App {
    @StateObject private var connectionManager = TVConnectionManager()
    @StateObject private var settingsVM = SettingsViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(connectionManager)
                .environmentObject(settingsVM)
        }
    }
}
```

**What happens:**
1. `TVConnectionManager` is instantiated (a single shared actor for the whole app lifetime)
2. `SettingsViewModel` loads saved TV devices from UserDefaults
3. `ContentView` is presented, with both objects injected into SwiftUI's environment

---

## 2. Root View: `Shared/Views/RemoteControlView.swift`

`ContentView` on iOS resolves to `RemoteControlView`.

```swift
struct RemoteControlView: View {
    @EnvironmentObject var connectionManager: TVConnectionManager
    @StateObject private var viewModel = RemoteViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                ConnectionStatusBanner()      // Step 3
                PowerButtonView()             // Step 4
                DPadView()                    // Step 5
                QuickNavRow()                 // Step 6
                MediaControlsView()           // Step 7
                AppLauncherView()             // Step 8
            }
            .navigationTitle(connectionManager.currentTV?.name ?? "No TV")
            .toolbar { SettingsButton() }
        }
        .onAppear { Task { await connectionManager.connect() } }  // Step 9
    }
}
```

**What happens:**
- On `.onAppear`, the connection sequence begins (Step 9)
- Each sub-view is a self-contained SwiftUI component sharing `connectionManager` via environment

---

## 3. Connection Status Banner: `Shared/Views/ConnectionStatusBanner.swift`

```swift
struct ConnectionStatusBanner: View {
    @EnvironmentObject var manager: TVConnectionManager

    var body: some View {
        HStack {
            Circle()
                .fill(manager.connectionState.color)  // green / yellow / red
                .frame(width: 10, height: 10)
            Text(manager.connectionState.label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}
```

`connectionState` is a `@Published` property on `TVConnectionManager`. SwiftUI re-renders the banner whenever it changes.

---

## 4. Power Button: `Shared/Views/PowerButtonView.swift`

```swift
struct PowerButtonView: View {
    @EnvironmentObject var viewModel: RemoteViewModel

    var body: some View {
        Button {
            Task { await viewModel.sendKey(.power) }   // → Step 10
        } label: {
            Image(systemName: "power")
                .font(.title)
                .foregroundStyle(.red)
        }
        .buttonStyle(.bordered)
    }
}
```

**What happens:**
- Tapping creates a Swift Task (non-blocking)
- Calls `viewModel.sendKey(.power)` — goes to Step 10

---

## 5. D-Pad: `Shared/Views/DPadView.swift`

```swift
struct DPadView: View {
    @EnvironmentObject var viewModel: RemoteViewModel

    var body: some View {
        ZStack {
            Circle().fill(Color(.systemGray5))
                .frame(width: 200, height: 200)

            VStack(spacing: 0) {
                DPadButton(key: .up,    icon: "chevron.up")
                HStack(spacing: 0) {
                    DPadButton(key: .left,  icon: "chevron.left")
                    OKButton()             // Sends KEY_ENTER
                    DPadButton(key: .right, icon: "chevron.right")
                }
                DPadButton(key: .down,  icon: "chevron.down")
            }
        }
    }
}

struct DPadButton: View {
    let key: RemoteKey
    let icon: String
    @EnvironmentObject var viewModel: RemoteViewModel

    var body: some View {
        Button { Task { await viewModel.sendKey(key) } } label: {  // → Step 10
            Image(systemName: icon)
                .frame(width: 60, height: 60)
        }
        .buttonStyle(.plain)
    }
}
```

---

## 6. Quick Nav Row: `Shared/Views/QuickNavRow.swift`

```swift
struct QuickNavRow: View {
    @EnvironmentObject var viewModel: RemoteViewModel
    var body: some View {
        HStack(spacing: 24) {
            NavButton(key: .home,  icon: "house",       label: "Home")
            NavButton(key: .back,  icon: "arrow.left",  label: "Back")
            NavButton(key: .menu,  icon: "line.3.horizontal", label: "Menu")
        }
    }
}
```

---

## 7. Media Controls: `Shared/Views/MediaControlsView.swift`

```swift
struct MediaControlsView: View {
    @EnvironmentObject var viewModel: RemoteViewModel
    var body: some View {
        VStack(spacing: 8) {
            HStack {
                MediaButton(key: .volumeDown, icon: "speaker.minus")
                MediaButton(key: .mute,       icon: "speaker.slash")
                MediaButton(key: .volumeUp,   icon: "speaker.plus")
            }
            HStack {
                MediaButton(key: .channelDown, icon: "chevron.down.circle")
                Spacer()
                MediaButton(key: .channelUp,   icon: "chevron.up.circle")
            }
        }
    }
}
```

---

## 8. App Launcher: `Shared/Views/AppLauncherView.swift`

```swift
struct AppLauncherView: View {
    @EnvironmentObject var viewModel: RemoteViewModel
    let columns = [GridItem(.adaptive(minimum: 80))]

    var body: some View {
        LazyVGrid(columns: columns, spacing: 12) {
            ForEach(TVApp.knownApps) { app in
                Button {
                    Task { await viewModel.launchApp(app) }   // → Step 11
                } label: {
                    VStack {
                        Image(app.icon).resizable().frame(width: 48, height: 48)
                        Text(app.name).font(.caption2)
                    }
                }
            }
        }
    }
}
```

---

## 9. Connection Sequence: `Shared/Services/TVConnectionManager.swift`

`connect()` is called on `.onAppear` of the main view.

```swift
@MainActor
class TVConnectionManager: ObservableObject {
    @Published var connectionState: ConnectionState = .disconnected
    private var localService: LocalWebSocketService?
    private let cloudService = SmartThingsService()

    func connect() async {
        guard let tv = currentTV else { return }
        connectionState = .connecting

        // 1. Try local WebSocket first
        do {
            localService = LocalWebSocketService(tv: tv)
            try await localService!.connect(timeout: 2.0)  // 2-second timeout
            connectionState = .connectedLocal
        } catch {
            // 2. Local failed → fall back to cloud
            connectionState = await cloudService.isConfigured()
                ? .connectedCloud
                : .disconnected
        }
    }
}
```

---

## 10. Sending a Key: `Shared/ViewModels/RemoteViewModel.swift`

Every button tap calls `sendKey(_:)`:

```swift
@MainActor
class RemoteViewModel: ObservableObject {
    @EnvironmentObject var connectionManager: TVConnectionManager  // injected

    func sendKey(_ key: RemoteKey) async {
        await connectionManager.send(key: key)
    }
}
```

This delegates to `TVConnectionManager.send(key:)`:

```swift
// TVConnectionManager.swift
func send(key: RemoteKey) async {
    // Try local first
    if connectionState == .connectedLocal {
        do {
            try await localService?.send(key.rawValue)
            return
        } catch {
            // Local dropped — switch to cloud
            connectionState = .connectedCloud
        }
    }
    // Cloud path
    if let tv = currentTV {
        try? await cloudService.sendKeyCommand(key, deviceId: tv.smartThingsDeviceId)
    }
}
```

---

## 11. Local WebSocket Send: `Shared/Services/LocalWebSocketService.swift`

```swift
final class LocalWebSocketService {
    private var socket: WebSocket?   // Starscream WebSocket

    func connect(timeout: TimeInterval) async throws {
        // Build connection URL:
        // ws://192.168.1.100:8001/api/v2/channels/samsung.remote.control?name=<base64>
        let appName = "Samsung TV Remote".data(using: .utf8)!.base64EncodedString()
        var components = URLComponents()
        components.scheme = "ws"
        components.host   = tv.ipAddress
        components.port   = 8001
        components.path   = "/api/v2/channels/samsung.remote.control"
        components.queryItems = [
            URLQueryItem(name: "name",  value: appName),
            URLQueryItem(name: "token", value: tv.pairingToken)
        ]
        let request = URLRequest(url: components.url!)
        socket = WebSocket(request: request)
        // ... async connect with timeout ...
    }

    func send(_ keyCode: String) async throws {
        // Build JSON payload
        let payload: [String: Any] = [
            "method": "ms.remote.control",
            "params": [
                "Cmd":           "Click",
                "DataOfCmd":     keyCode,          // e.g. "KEY_VOLUMEUP"
                "Option":        "false",
                "TypeOfRemote":  "SendRemoteKey"
            ]
        ]
        let data = try JSONSerialization.data(withJSONObject: payload)
        let text = String(data: data, encoding: .utf8)!
        socket?.write(string: text)
    }
}
```

**Wire format sent to TV:**
```json
{
  "method": "ms.remote.control",
  "params": {
    "Cmd": "Click",
    "DataOfCmd": "KEY_VOLUMEUP",
    "Option": "false",
    "TypeOfRemote": "SendRemoteKey"
  }
}
```

---

## 12. SmartThings Cloud Send: `Shared/Services/SmartThingsService.swift`

When local is unavailable, commands go via HTTPS:

```swift
final class SmartThingsService {
    private let baseURL = URL(string: "https://api.smartthings.com/v1")!

    func sendKeyCommand(_ key: RemoteKey, deviceId: String) async throws {
        let url = baseURL
            .appendingPathComponent("devices")
            .appendingPathComponent(deviceId)
            .appendingPathComponent("commands")

        let body: [String: Any] = [
            "commands": [[
                "component":  "main",
                "capability": "remoteControlStatus",
                "command":    key.smartThingsCommand,
                "arguments":  key.smartThingsArguments
            ]]
        ]

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json",  forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else {
            throw TVConnectionError.cloudCommandFailed
        }
    }
}
```

---

## 13. App Launch Path: `Shared/Services/LocalWebSocketService.swift`

Launching a streaming app uses a different Samsung API endpoint:

```swift
func launchApp(_ app: TVApp) async throws {
    let payload: [String: Any] = [
        "method": "ms.channel.emit",
        "params": [
            "event": "ed.apps.launch",
            "to":    "host",
            "data": [
                "appId":    app.appId,
                "action_type": "NATIVE_LAUNCH"
            ]
        ]
    ]
    let data = try JSONSerialization.data(withJSONObject: payload)
    socket?.write(string: String(data: data, encoding: .utf8)!)
}
```

---

## 14. Wake-on-LAN: `Shared/Services/WakeOnLANService.swift`

Power-on sends a UDP magic packet:

```swift
final class WakeOnLANService {
    func send(macAddress: String) throws {
        // Parse MAC bytes
        let macBytes = macAddress
            .split(separator: ":")
            .compactMap { UInt8($0, radix: 16) }
        guard macBytes.count == 6 else { throw WoLError.invalidMAC }

        // Build magic packet: 6×0xFF + 16×MAC
        var packet = [UInt8](repeating: 0xFF, count: 6)
        for _ in 0..<16 { packet.append(contentsOf: macBytes) }

        // Send UDP broadcast to 255.255.255.255:9
        let sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        var broadcast: Int32 = 1
        setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &broadcast, 4)
        var addr = sockaddr_in()
        addr.sin_family      = sa_family_t(AF_INET)
        addr.sin_port        = UInt16(9).bigEndian
        addr.sin_addr.s_addr = UInt32.max  // 255.255.255.255
        withUnsafeBytes(of: &addr) { addrPtr in
            packet.withUnsafeBytes { pktPtr in
                sendto(sock, pktPtr.baseAddress, packet.count,
                       0, addrPtr.bindMemory(to: sockaddr.self).baseAddress, 16)
            }
        }
        close(sock)
    }
}
```

---

## Full iOS Call Stack Summary

```
User taps "Volume Up"
  └─ DPadButton.body { Task { await viewModel.sendKey(.volumeUp) } }
       └─ RemoteViewModel.sendKey(.volumeUp)
            └─ TVConnectionManager.send(key: .volumeUp)
                 ├─ [local connected]
                 │    └─ LocalWebSocketService.send("KEY_VOLUMEUP")
                 │         └─ socket.write(JSON payload)  ──► TV adjusts volume
                 └─ [local failed]
                      └─ SmartThingsService.sendKeyCommand(.volumeUp, deviceId:)
                           └─ URLSession POST /v1/devices/{id}/commands ──► cloud ──► TV
```
