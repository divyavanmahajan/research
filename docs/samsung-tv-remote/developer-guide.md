# Samsung TV Remote — Developer Guide

**Version:** 1.0
**Date:** 2026-03-08

---

## 1. Prerequisites

| Tool | Minimum Version | Install |
|---|---|---|
| Xcode | 15.0 | Mac App Store |
| macOS | 13 Ventura | System update |
| Swift | 5.9 | Bundled with Xcode |
| iOS Simulator | iOS 16+ | Xcode → Platforms |
| uvx / uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Git | 2.x | Xcode Command Line Tools |

Optional tools used for interactive demos and browser testing:

```bash
# showboat — executable demo documents (proof-of-work markdown)
uvx showboat --help

# rodney — Chrome automation for testing SmartThings API flows
uvx rodney --help
```

---

## 2. Repository Setup

```bash
git clone https://github.com/divyavanmahajan/research.git
cd research

# Switch to the feature branch
git checkout claude/samsung-tv-remote-apps-eNy1f

# Open the Xcode project
open SamsungTVRemote/SamsungTVRemote.xcodeproj
```

---

## 3. Swift Package Dependencies

Dependencies are declared in `Package.swift` and resolved automatically by Xcode.

| Package | Version | Purpose |
|---|---|---|
| [Starscream](https://github.com/daltoniam/Starscream) | 4.0.6+ | WebSocket client |

To resolve manually:
```bash
cd SamsungTVRemote
swift package resolve
```

---

## 4. Xcode Project Configuration

### Targets

| Target | Identifier | Deployment |
|---|---|---|
| `SamsungRemote-iOS` | `com.yourcompany.samsungremote.ios` | iOS 16.0+ |
| `SamsungRemote-macOS` | `com.yourcompany.samsungremote.mac` | macOS 13.0+ |

### Signing

1. Open Xcode → Project navigator → select `SamsungTVRemote`
2. Select each target → **Signing & Capabilities**
3. Set **Team** to your Apple Developer account
4. Xcode auto-manages provisioning profiles when "Automatically manage signing" is checked

### Entitlements (macOS)

The macOS target requires these entitlements in `macOS/SamsungRemote.entitlements`:

```xml
<key>com.apple.security.network.client</key>
<true/>
<key>com.apple.security.network.server</key>
<false/>
```

### Info.plist Keys (iOS)

```xml
<!-- Required for local network (WebSocket discovery) -->
<key>NSLocalNetworkUsageDescription</key>
<string>Samsung TV Remote needs local network access to control your TV directly.</string>

<!-- Bonjour services (optional mDNS discovery) -->
<key>NSBonjourServices</key>
<array>
  <string>_samsungsmarthome._tcp</string>
</array>
```

---

## 5. Environment Variables & Secrets

Never hardcode secrets. Use Xcode environment variables for local development.

### Setting Up a Local Dev Config

Create `SamsungTVRemote/.env.local` (git-ignored):

```bash
SMARTTHINGS_TOKEN=your_personal_access_token_here
TEST_TV_IP=192.168.1.100
TEST_TV_MAC=AA:BB:CC:DD:EE:FF
TEST_TV_DEVICE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Load in scheme: **Edit Scheme → Run → Arguments → Environment Variables**.

In code, secrets are read at runtime from Keychain (production) or environment (debug):

```swift
#if DEBUG
let token = ProcessInfo.processInfo.environment["SMARTTHINGS_TOKEN"] ?? ""
#else
let token = KeychainHelper.read(key: "smartthings_token") ?? ""
#endif
```

---

## 6. Building and Running

### iOS Simulator

```bash
# Build for simulator
xcodebuild -scheme SamsungRemote-iOS \
           -destination 'platform=iOS Simulator,name=iPhone 15 Pro' \
           build

# Or simply press ⌘R in Xcode with an iPhone simulator selected
```

> **Note:** WebSocket connections to a real TV work from simulator only if your Mac and TV are on the same network. Wake-on-LAN (UDP broadcast) does not work from simulator — use a physical device or macOS build for WoL testing.

### macOS

```bash
xcodebuild -scheme SamsungRemote-macOS \
           -destination 'platform=macOS' \
           build
# Or press ⌘R in Xcode with "My Mac" selected
```

---

## 7. Testing

### Unit Tests

```bash
xcodebuild test \
  -scheme SamsungTVRemote \
  -destination 'platform=iOS Simulator,name=iPhone 15 Pro'
```

Key test files:

| File | What it tests |
|---|---|
| `TVConnectionManagerTests.swift` | Fallback logic: local → cloud |
| `LocalWebSocketServiceTests.swift` | Key code serialization |
| `SmartThingsServiceTests.swift` | REST request construction |
| `WakeOnLANTests.swift` | Magic packet byte sequence |
| `RemoteViewModelTests.swift` | State transitions |

### Integration Tests (against real TV)

Set environment variables (see §5), then run the `IntegrationTests` scheme:

```bash
xcodebuild test \
  -scheme IntegrationTests \
  -destination 'platform=macOS'
```

These tests send real commands to the TV — **ensure someone is present** to dismiss the pairing dialog on the first run.

---

## 8. Creating a Demo Document with `showboat`

`showboat` creates executable markdown documents that mix commentary, shell commands, and captured output. Use it to document and prove that the TV remote works end-to-end.

```bash
# Initialize a new demo document
uvx showboat init docs/samsung-tv-remote/demo-session.md "Samsung TV Remote — Live Demo"

# Add commentary
uvx showboat note docs/samsung-tv-remote/demo-session.md \
  "Connect to the TV WebSocket and send a volume-up command."

# Run a command and capture its output into the doc
uvx showboat exec docs/samsung-tv-remote/demo-session.md bash \
  "curl -s ws://192.168.1.100:8001/api/v2 | python3 -m json.tool"

# Add a screenshot of the app
uvx showboat image docs/samsung-tv-remote/demo-session.md screenshot.png

# Later — verify the demo still works (re-runs all code blocks, diffs output)
uvx showboat verify docs/samsung-tv-remote/demo-session.md

# See the sequence of commands that built the demo
uvx showboat extract docs/samsung-tv-remote/demo-session.md
```

The resulting `demo-session.md` is both readable documentation and a reproducible proof that the app communicates correctly with the TV.

---

## 9. Browser-Based API Testing with `rodney`

`rodney` automates Chrome for testing SmartThings API flows through the web UI or validating token setup.

```bash
# Start headless Chrome
uvx rodney start

# Navigate to SmartThings token page
uvx rodney open https://account.smartthings.com/tokens

# Wait for the token list to load
uvx rodney wait ".token-list"

# Take a screenshot to confirm
uvx rodney screenshot docs/samsung-tv-remote/token-page.png

# Test the SmartThings device API (inject credentials)
uvx rodney open "https://api.smartthings.com/v1/devices"
uvx rodney js "document.cookie"

# Assert the API returns a 200 with device list
uvx rodney assert "document.body.innerText.includes('items')" "true" \
  -m "SmartThings devices endpoint should return items"

# Stop Chrome when done
uvx rodney stop
```

Use `rodney` in CI to:
- Validate that a SmartThings PAT can list devices
- Screenshot the app running in a macOS environment for release notes
- Automate the SmartThings app-launcher catalogue scrape

---

## 10. Code Style & Conventions

### Naming
- `TVConnectionManager` — PascalCase for types
- `sendKey(_:)` — camelCase for methods
- `isConnected` — boolean properties prefixed `is`/`has`/`can`
- `RemoteKey.volumeUp` — enum cases in camelCase

### Async Patterns
All network calls use `async/await`. Avoid completion handlers in new code.

```swift
// Correct
let apps = try await smartThingsService.fetchInstalledApps(deviceId: id)

// Avoid
smartThingsService.fetchInstalledApps(deviceId: id) { apps, error in ... }
```

### Error Handling
Define domain errors as typed enums:

```swift
enum TVConnectionError: LocalizedError {
    case localTimeout
    case cloudAuthFailed
    case tvNotFound
    case pairingRequired
}
```

### SwiftUI State
- Use `@StateObject` for ViewModels owned by a View
- Use `@EnvironmentObject` for shared singletons (e.g., `TVConnectionManager`)
- Use `@AppStorage` for simple persisted preferences (TV IP, app name)

---

## 11. Adding a New Remote Key

1. Add the key code to `Shared/Models/RemoteKey.swift`:
   ```swift
   enum RemoteKey: String {
       // ...existing cases...
       case guide = "KEY_GUIDE"
   }
   ```

2. Add a button to `Shared/Views/RemoteControlView.swift`:
   ```swift
   RemoteButton(label: "Guide", icon: "list.bullet") {
       viewModel.sendKey(.guide)
   }
   ```

3. Add a unit test in `LocalWebSocketServiceTests.swift` verifying the serialised payload contains `"KEY_GUIDE"`.

---

## 12. Adding a New Streaming App

Apps are defined in `Shared/Models/TVApp.swift`:

```swift
static let knownApps: [TVApp] = [
    TVApp(name: "Netflix",     appId: "11101200001", icon: "netflix"),
    TVApp(name: "YouTube",     appId: "111299001912", icon: "youtube"),
    TVApp(name: "Disney+",     appId: "MCmYXNxgcu",  icon: "disney"),
    TVApp(name: "Prime Video", appId: "3201910019365", icon: "prime"),
    // Add new app here:
    TVApp(name: "Apple TV+",   appId: "com.apple.appletv", icon: "appletv"),
]
```

App IDs can be discovered by querying the TV:
```bash
curl "ws://TV_IP:8001/api/v2/applications" --include
```

---

## 13. Branch & PR Workflow

```bash
# Always develop on the feature branch
git checkout claude/samsung-tv-remote-apps-eNy1f

# Make changes, then commit
git add Shared/ iOS/ macOS/
git commit -m "feat: add Guide key and Apple TV+ app launcher"

# Push
git push -u origin claude/samsung-tv-remote-apps-eNy1f
```

PR title format: `feat(remote): <short description>`
