# Samsung TV Remote — System Architecture

**Version:** 1.0
**Date:** 2026-03-08
**Platforms:** iOS 16+, macOS 13+

---

## 1. Overview

Samsung TV Remote is a native Apple platform application built with SwiftUI and Swift Concurrency. It provides full remote-control functionality for Samsung Smart TVs using a hybrid connectivity model: direct local WebSocket for low-latency on-network control, with automatic fallback to the Samsung SmartThings cloud API for off-network use.

```
┌─────────────────────────────────────────┐
│          User Interface (SwiftUI)        │
│  iOS target          macOS target        │
└─────────────┬───────────────────────────┘
              │ shared Shared/ module
┌─────────────▼───────────────────────────┐
│        TVConnectionManager              │
│  (Orchestrates local ↔ cloud fallback)  │
└──────┬────────────────────┬─────────────┘
       │                    │
┌──────▼──────┐    ┌────────▼──────────┐
│  Local WS   │    │  SmartThings API  │
│  Service    │    │  Service (REST)   │
│  port 8001  │    │  cloud.api.st.com │
└──────┬──────┘    └───────────────────┘
       │
┌──────▼──────┐
│  Wake-on-   │
│  LAN (UDP)  │
└─────────────┘
              │
       ┌──────▼──────┐
       │  Samsung TV │
       └─────────────┘
```

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| UI Framework | SwiftUI 4 | Declarative cross-platform UI |
| Language | Swift 5.9 | Primary implementation language |
| Async | Swift Concurrency (async/await, Actor) | Non-blocking I/O |
| Local Protocol | Samsung WebSocket API v2 (ws://TV:8001) | Low-latency key commands |
| Cloud Protocol | SmartThings REST API v1 | Remote / off-network control |
| Power-On | Wake-on-LAN (UDP magic packet) | Wake sleeping TV |
| WebSocket Library | Starscream 4.x (via SPM) | WebSocket client |
| Storage | UserDefaults / @AppStorage | TV device preferences |
| Networking | URLSession + Network.framework | HTTP + reachability |

---

## 3. Project Structure

```
SamsungTVRemote/
├── SamsungTVRemote.xcodeproj
│   └── project.pbxproj
├── Package.swift                          # SPM dependencies (Starscream)
│
├── Shared/                                # Shared between iOS & macOS (~90% of code)
│   ├── Models/
│   │   ├── TVDevice.swift                 # TV identity (IP, MAC, name, SmartThings ID)
│   │   ├── TVApp.swift                    # Installed TV app (name, appId, icon)
│   │   └── RemoteKey.swift                # Enum of all Samsung key codes
│   │
│   ├── Services/
│   │   ├── TVConnectionManager.swift      # Strategy selector: local vs cloud
│   │   ├── LocalWebSocketService.swift    # ws:// connection, key command sender
│   │   ├── SmartThingsService.swift       # REST client for SmartThings API
│   │   └── WakeOnLANService.swift         # UDP magic packet broadcast
│   │
│   ├── ViewModels/
│   │   ├── RemoteViewModel.swift          # State for the remote control UI
│   │   └── SettingsViewModel.swift        # TV device config, token storage
│   │
│   └── Views/
│       ├── RemoteControlView.swift        # Root remote layout (adaptive)
│       ├── DPadView.swift                 # Circular D-pad + OK button
│       ├── MediaControlsView.swift        # Volume, channel, mute row
│       ├── AppLauncherView.swift          # Grid of streaming app tiles
│       ├── PowerButtonView.swift          # Power toggle with WoL logic
│       └── SettingsView.swift             # IP, MAC, SmartThings token input
│
├── iOS/
│   ├── SamsungRemoteApp.swift             # @main iOS entry point
│   ├── Info.plist
│   └── Assets.xcassets
│
└── macOS/
    ├── SamsungRemoteApp.swift             # @main macOS entry point
    ├── Info.plist
    └── Assets.xcassets
```

---

## 4. Connection Manager — Fallback Logic

```
sendKey(key) called
        │
        ▼
  Is local WS connected?
   YES ──────────────────► Send via WebSocket ──► Done
        │
       NO
        │
        ▼
  Try connect to ws://TV_IP:8001
  within 2-second timeout
        │
   Success ────────────► Send via WebSocket ──► Mark local=active ──► Done
        │
      Timeout / Error
        │
        ▼
  Send via SmartThings REST API ──► Done
  (mark local=degraded, retry local in 30s)
```

### Power On (TV off)

```
powerOn() called
        │
        ▼
  Send WoL magic packet (UDP broadcast, TV MAC address)
        │
        ▼
  Wait 8 seconds (TV boot time)
        │
        ▼
  Attempt WebSocket connection (retry ×5, 2s apart)
        │
   Connected ──► normal operation
        │
      Failed ──► fall back to SmartThings API
```

---

## 5. Local WebSocket Protocol

Samsung TVs expose a WebSocket server on port 8001 (plain) and 8002 (TLS).

### Connection URL
```
ws://192.168.1.100:8001/api/v2/channels/samsung.remote.control?name=<base64(appName)>
```

### Pairing Handshake (first connection)
1. App connects → TV shows "Allow access?" dialog
2. User accepts on TV → TV sends `{"event":"ms.channel.connect","data":{"token":"<TOKEN>"}}`
3. App stores token in UserDefaults
4. Subsequent connections include `&token=<TOKEN>` in the URL

### Key Command Payload
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

### Key Code Reference

| Action | Key Code |
|---|---|
| Power | `KEY_POWER` |
| Volume Up | `KEY_VOLUMEUP` |
| Volume Down | `KEY_VOLUMEDOWN` |
| Mute | `KEY_MUTE` |
| Channel Up | `KEY_CHUP` |
| Channel Down | `KEY_CHDOWN` |
| D-pad Up | `KEY_UP` |
| D-pad Down | `KEY_DOWN` |
| D-pad Left | `KEY_LEFT` |
| D-pad Right | `KEY_RIGHT` |
| OK / Enter | `KEY_ENTER` |
| Back | `KEY_RETURN` |
| Home | `KEY_HOME` |
| Menu | `KEY_MENU` |

---

## 6. SmartThings API Integration

### Authentication
- Personal Access Token (PAT) generated at: `https://account.smartthings.com/tokens`
- Stored in iOS Keychain / macOS Keychain via `SecItem` APIs
- Sent as `Authorization: Bearer <token>` header

### Key Endpoints Used

| Action | Endpoint |
|---|---|
| List devices | `GET /v1/devices?capability=remoteControlStatus` |
| Send command | `POST /v1/devices/{deviceId}/commands` |
| Get TV status | `GET /v1/devices/{deviceId}/status` |
| List installed apps | `GET /v1/devices/{deviceId}/components/main/capabilities/custom.launchApp/status` |

### Command Payload (SmartThings)
```json
{
  "commands": [{
    "component": "main",
    "capability": "remoteControlStatus",
    "command": "setVolume",
    "arguments": [15]
  }]
}
```

---

## 7. Wake-on-LAN

Wake-on-LAN sends a 102-byte UDP "magic packet" to the broadcast address on port 9.

### Magic Packet Structure
```
FF FF FF FF FF FF          (6 bytes: 0xFF × 6)
AA BB CC DD EE FF × 16    (96 bytes: MAC address repeated 16 times)
```

The packet is sent as a UDP broadcast (`255.255.255.255:9`) so no TV IP address is needed for power-on.

**Requirement:** The TV must have "Power On with Mobile" enabled in:
`Settings → General → Network → Expert Settings → Power On with Mobile`

---

## 8. Platform Differences

| Concern | iOS | macOS |
|---|---|---|
| Window style | Full-screen phone layout | Fixed-size floating panel (400×700) |
| Input method | Touch gestures | Mouse click; keyboard shortcuts |
| Background refresh | Not applicable | Always-on menubar optional |
| Keychain access | iOS Keychain | macOS Keychain |
| Local network permission | `NSLocalNetworkUsageDescription` plist key | Entitlement `com.apple.security.network.client` |
| Wake-on-LAN socket | `CFSocket` raw UDP | `CFSocket` raw UDP |

---

## 9. Data Flow — Sending a Key Press

```
User taps "Volume Up" button
        │
        ▼
RemoteViewModel.sendKey(.volumeUp)
        │
        ▼
TVConnectionManager.send(key: .volumeUp)
        │
   [local connected?]
    YES ──► LocalWebSocketService.send(RemoteKey.volumeUp.rawValue)
              │
              ▼
           WebSocket frame → Samsung TV
              │
              ▼
           TV adjusts volume
    NO  ──► SmartThingsService.sendCommand(.setVolume, args: [currentVolume+1])
              │
              ▼
           URLSession POST → SmartThings cloud → TV
```

---

## 10. Security Considerations

- SmartThings PAT stored in OS Keychain (never in UserDefaults)
- WebSocket token stored in UserDefaults (low sensitivity)
- Local WebSocket only connects to IP addresses the user has explicitly configured
- Network calls validated against expected TV hostname to prevent MITM on local network
- TLS port 8002 supported as opt-in for local connections
