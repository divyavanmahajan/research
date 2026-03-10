# Samsung TV Remote — macOS Code Walkthrough (Linear)

**Version:** 1.0
**Purpose:** Step-by-step trace from app launch to key press on macOS, highlighting all Mac-specific divergences from the iOS path.

---

## 1. App Entry Point: `macOS/SamsungRemoteApp.swift`

```swift
@main
struct SamsungRemoteApp: App {
    @StateObject private var connectionManager = TVConnectionManager()
    @StateObject private var settingsVM = SettingsViewModel()

    var body: some Scene {
        // Primary remote window — fixed-size, always-on-top
        WindowGroup {
            RemoteControlView()
                .environmentObject(connectionManager)
                .environmentObject(settingsVM)
                .frame(width: 400, height: 700)
        }
        .windowResizability(.contentSize)   // macOS-only: prevents resizing
        .windowStyle(.hiddenTitleBar)       // macOS-only: removes title bar chrome

        // macOS-only: Preferences window opened with ⌘,
        Settings {
            SettingsView()
                .environmentObject(settingsVM)
        }
    }
}
```

**macOS vs iOS differences here:**
- Uses `Settings { }` scene for ⌘, Preferences — this scene type is macOS only
- `windowResizability` and `windowStyle` are macOS-only modifiers
- `.frame(width:height:)` fixes the window to a compact remote-panel size

---

## 2. App Delegate for Menu Bar: `macOS/AppDelegate.swift`

The macOS target adds a `NSApplicationDelegateAdaptor` for menu bar support:

```swift
class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem?
    var popover = NSPopover()

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Create menu bar icon
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        statusItem?.button?.image = NSImage(systemSymbolName: "tv", accessibilityDescription: "TV Remote")
        statusItem?.button?.action = #selector(togglePopover)

        // Mini remote in popover
        let miniRemote = MiniRemoteView()
        popover.contentViewController = NSHostingController(rootView: miniRemote)
        popover.contentSize = NSSize(width: 200, height: 300)
        popover.behavior = .transient
    }

    @objc func togglePopover() {
        if popover.isShown {
            popover.performClose(nil)
        } else if let button = statusItem?.button {
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        }
    }
}
```

This is **macOS-only** — iOS has no menu bar concept.

---

## 3. Root View: `Shared/Views/RemoteControlView.swift`

The same `RemoteControlView` is used on both platforms. macOS platform-specific layout is achieved via `#if os(macOS)` guards:

```swift
struct RemoteControlView: View {
    @EnvironmentObject var connectionManager: TVConnectionManager
    @StateObject private var viewModel = RemoteViewModel()

    var body: some View {
        VStack(spacing: 12) {
            ConnectionStatusBanner()
            PowerButtonView()
            DPadView()
            QuickNavRow()
            MediaControlsView()
            AppLauncherView()
        }
        #if os(macOS)
        .padding(16)                              // Tighter padding on Mac
        .background(.background.opacity(0.95))    // Window background
        #endif
        .onAppear { Task { await connectionManager.connect() } }
    }
}
```

---

## 4. Keyboard Shortcuts: macOS-only overlay in `RemoteControlView`

On macOS, arrow keys and other keyboard shortcuts are mapped to TV commands:

```swift
#if os(macOS)
extension RemoteControlView {
    var keyboardHandlerView: some View {
        Color.clear
            .onKeyPress(.upArrow)    { Task { await viewModel.sendKey(.up) };    return .handled }
            .onKeyPress(.downArrow)  { Task { await viewModel.sendKey(.down) };  return .handled }
            .onKeyPress(.leftArrow)  { Task { await viewModel.sendKey(.left) };  return .handled }
            .onKeyPress(.rightArrow) { Task { await viewModel.sendKey(.right) }; return .handled }
            .onKeyPress(.return)     { Task { await viewModel.sendKey(.ok) };    return .handled }
            .onKeyPress(.escape)     { Task { await viewModel.sendKey(.back) };  return .handled }
            .onKeyPress(characters: CharacterSet(charactersIn: "+")) { _ in
                Task { await viewModel.sendKey(.volumeUp) }; return .handled }
            .onKeyPress(characters: CharacterSet(charactersIn: "-")) { _ in
                Task { await viewModel.sendKey(.volumeDown) }; return .handled }
            .onKeyPress(characters: CharacterSet(charactersIn: "m")) { _ in
                Task { await viewModel.sendKey(.mute) }; return .handled }
    }
}
#endif
```

---

## 5. Settings View: `Shared/Views/SettingsView.swift`

On iOS, Settings is a sheet. On macOS, it is a Preferences window (opened with ⌘,):

```swift
struct SettingsView: View {
    @EnvironmentObject var settingsVM: SettingsViewModel

    var body: some View {
        #if os(macOS)
        TabView {
            TVListSettingsTab().tabItem { Label("TVs", systemImage: "tv") }
            ConnectionSettingsTab().tabItem { Label("Connection", systemImage: "wifi") }
            SmartThingsSettingsTab().tabItem { Label("SmartThings", systemImage: "cloud") }
            AppearanceSettingsTab().tabItem { Label("Appearance", systemImage: "paintbrush") }
        }
        .frame(width: 500, height: 400)
        #else
        NavigationStack {
            Form {
                TVListSection()
                ConnectionSection()
                SmartThingsSection()
            }
            .navigationTitle("Settings")
        }
        #endif
    }
}
```

---

## 6. SettingsViewModel: `Shared/ViewModels/SettingsViewModel.swift`

Shared between platforms, but Keychain access uses different APIs per OS:

```swift
@MainActor
class SettingsViewModel: ObservableObject {
    @Published var tvDevices: [TVDevice] = []
    @Published var smartThingsToken: String = ""

    init() {
        loadDevices()
        smartThingsToken = KeychainHelper.read(key: "smartthings_token") ?? ""
    }

    func saveToken(_ token: String) {
        smartThingsToken = token
        KeychainHelper.save(key: "smartthings_token", value: token)
        // KeychainHelper uses SecItem APIs — works on both iOS and macOS
    }

    private func loadDevices() {
        // UserDefaults — same on both platforms
        if let data = UserDefaults.standard.data(forKey: "tvDevices"),
           let devices = try? JSONDecoder().decode([TVDevice].self, from: data) {
            tvDevices = devices
        }
    }
}
```

---

## 7. Connection Manager (shared): `Shared/Services/TVConnectionManager.swift`

Identical to the iOS path. See iOS walkthrough §9 for full detail.

The **only macOS difference** is in Wake-on-LAN: on macOS, the app can also send the WoL packet via a raw socket with elevated privileges (using the Hardened Runtime entitlement `com.apple.security.network.client`).

```swift
// macOS only — retries WoL 3 times (TV may be in deep sleep)
#if os(macOS)
func powerOnWithRetry(tv: TVDevice) async {
    for attempt in 1...3 {
        try? WakeOnLANService().send(macAddress: tv.macAddress)
        try? await Task.sleep(for: .seconds(2))
    }
}
#endif
```

---

## 8. Local WebSocket Service (shared): `Shared/Services/LocalWebSocketService.swift`

100% identical to the iOS path (see iOS walkthrough §11). Starscream works identically on macOS.

---

## 9. SmartThings Service (shared): `Shared/Services/SmartThingsService.swift`

100% identical to the iOS path (see iOS walkthrough §12). URLSession is the same on macOS.

---

## 10. Preferences Window Lifecycle (macOS only)

When the user presses ⌘,:

```
User presses ⌘,
  └─ macOS activates the Settings { } scene
       └─ SettingsView() is presented in a new NSWindow
            ├─ TVListSettingsTab: reads/writes settingsVM.tvDevices
            ├─ SmartThingsSettingsTab: reads/writes settingsVM.smartThingsToken
            │    └─ On "Discover Devices" tap:
            │         └─ SmartThingsService.discoverDevices()
            │              └─ GET https://api.smartthings.com/v1/devices
            │                   └─ Filtered by capability "remoteControlStatus"
            │                   └─ Populates settingsVM.tvDevices
            └─ ConnectionSettingsTab: reads/writes UserDefaults preferences
```

---

## 11. Drag-to-Reorder Apps (macOS only)

The app launcher on macOS supports drag-and-drop reordering — not present on iOS:

```swift
#if os(macOS)
struct AppLauncherView: View {
    @State private var apps = TVApp.knownApps

    var body: some View {
        LazyVGrid(columns: columns) {
            ForEach(apps) { app in
                AppTile(app: app)
                    .draggable(app)   // NSItemProvider drag source
            }
            .onMove { source, dest in
                apps.move(fromOffsets: source, toOffset: dest)
            }
        }
        .dropDestination(for: TVApp.self) { dropped, location in
            // Handle drops from other sources (e.g., dragging from TV's app list)
            true
        }
    }
}
#endif
```

---

## 12. Sandbox & Entitlements Check (macOS)

Before any network call, the macOS target verifies its entitlements are active:

```swift
// In TVConnectionManager.connect() — macOS only
#if os(macOS)
private func checkNetworkEntitlement() {
    // If the network client entitlement is missing, the WebSocket will fail silently.
    // Log a clear error in debug builds.
    assert(
        Bundle.main.object(forInfoDictionaryKey: "com.apple.security.network.client") != nil,
        "Missing network.client entitlement — add to SamsungRemote.entitlements"
    )
}
#endif
```

---

## Full macOS Call Stack Summary

```
User clicks "Volume Up" button (or presses "+")
  └─ DPadButton.body { Task { await viewModel.sendKey(.volumeUp) } }
  └─ [macOS] onKeyPress("+") { Task { await viewModel.sendKey(.volumeUp) } }
       └─ RemoteViewModel.sendKey(.volumeUp)
            └─ TVConnectionManager.send(key: .volumeUp)
                 ├─ [local connected — Starscream WebSocket]
                 │    └─ LocalWebSocketService.send("KEY_VOLUMEUP")
                 │         └─ socket.write(JSON)  ──► Samsung TV (port 8001)
                 └─ [local failed]
                      └─ SmartThingsService.sendKeyCommand(.volumeUp, deviceId:)
                           └─ URLSession POST api.smartthings.com ──► TV

User presses Space (power toggle, TV currently off)
  └─ onKeyPress(.space) → viewModel.sendKey(.power)
       └─ TVConnectionManager.powerOn(tv:)
            ├─ WakeOnLANService.send(macAddress: tv.macAddress)
            │    └─ UDP broadcast 255.255.255.255:9 (magic packet)
            └─ [macOS] powerOnWithRetry — sends WoL 3× with 2s delay
                 └─ After 8s: connect() attempt → local WebSocket established

User presses ⌘, (opens Preferences)
  └─ macOS Settings scene activates
       └─ SettingsView (TabView) displayed
            └─ SmartThingsSettingsTab → discoverDevices()
                 └─ GET api.smartthings.com/v1/devices
                      └─ TVDevice list saved to UserDefaults
```

---

## Key macOS vs iOS Code Differences at a Glance

| Concern | iOS File / API | macOS File / API |
|---|---|---|
| Entry point scene | `WindowGroup` only | `WindowGroup` + `Settings {}` |
| Menu bar | N/A | `AppDelegate` + `NSStatusItem` |
| Keyboard input | Touch gestures | `onKeyPress` modifiers |
| Preferences | Sheet (Form) | Preferences window (TabView) |
| Window size | Full screen / navigation stack | Fixed 400×700 panel |
| App list reorder | Not supported | Drag-and-drop (`.draggable`) |
| WoL retry | 1 attempt | 3 attempts with 2s gap |
| Entitlements check | Not needed | `com.apple.security.network.client` assert |
