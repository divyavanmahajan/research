# Samsung TV Remote — Getting Started

## Prerequisites

- macOS 14 (Sonoma) or later
- Xcode 15 or later (includes Swift and Command Line Tools)
- iPhone running iOS 16 or later (for the iOS app)
- Samsung Tizen TV (2016 or later) on the same Wi-Fi network as your Mac/iPhone

If Xcode is not installed, install the Command Line Tools first:

```bash
xcode-select --install
```

---

## Mac App

### Build and Run

Open Terminal, navigate to the project folder, then run:

```bash
cd /path/to/SamsungTVRemote
swift build -c debug
open .build/arm64-apple-macosx/debug/SamsungRemote-macOS
```

Or use the provided build script, which builds and launches in one step:

```bash
./build.sh mac
```

> **Note:** On Apple Silicon Macs the binary is under `.build/arm64-apple-macosx/debug/`.
> On Intel Macs it will be under `.build/x86_64-apple-macosx/debug/`.

### First Launch

1. The app opens as a small remote-control window.
2. Click the **gear icon** (top right) to open Settings.
3. Go to the **TVs** tab and click **+ Add TV**.
4. Either:
   - Click **Scan Local Network** to discover Samsung TVs automatically, or
   - Fill in the TV name, IP address, and optionally a pairing token manually.
5. Click **Add**, then close the sheet.
6. The app will attempt to connect automatically. Watch the **connection status dot** at the top of the remote.

### Pairing (first time only)

If the status shows **"Accept pairing on TV screen…"**:

1. Look at the TV — a popup saying **"Allow remote control?"** should appear.
2. Use the TV remote to select **Allow**.
3. The app reconnects automatically and saves the pairing token.

If no popup appears, see the **Help** tab in Settings for step-by-step troubleshooting.

### Reconnecting

If the status dot turns red (Disconnected), a **Reconnect** button appears next to it. Click it to reconnect without going into Settings.

---

## iOS App

The iOS app uses the same source code as the Mac app and is built via `xcodebuild`.

### Option 1 — Deploy to a physical iPhone (USB)

Connect your iPhone to the Mac via USB and trust the Mac if prompted, then run:

```bash
./build.sh ios
```

The script will:
1. Detect the connected iPhone automatically.
2. Build the app and install it on the device.
3. Launch it.

If the script cannot install automatically, it will print the `.app` path. You can then drag it onto the device in **Xcode → Window → Devices and Simulators**.

### Option 2 — Run in the iPhone Simulator

```bash
./build.sh ios sim
```

This boots the best available iPhone Simulator and launches the app inside it.

> **Note:** The Simulator cannot reach real TVs on your local network. Use it for UI exploration only. Connect a real iPhone for actual TV control.

### Option 3 — Open in Xcode (manual build)

If you prefer to build from Xcode:

1. Open Xcode.
2. Choose **File → Open** and select the `SamsungTVRemote` folder.
3. Xcode will detect the Swift Package. Select the **SamsungRemote-iOS** scheme (top toolbar).
4. Choose your iPhone as the destination.
5. Press **⌘R** to build and run.

### First Launch on iPhone

The steps are the same as the Mac app:

1. Tap the **gear icon** to open Settings.
2. Tap **Add TV** and scan or enter the TV details.
3. The app connects and shows the remote.
4. If asked to pair, accept the popup on the TV screen.

---

## CLI Tool

A standalone command-line remote is included. No build step required — run it directly with Swift:

```bash
# Discover TVs on your network
swift samsung-tv.swift scan

# Connect and pair with your TV
swift samsung-tv.swift connect 192.168.66.128

# Send keys
swift samsung-tv.swift key home
swift samsung-tv.swift key volup

# Launch an app
swift samsung-tv.swift app netflix

# Show connection status (includes full pairing token)
swift samsung-tv.swift status

# Run diagnostics if something isn't working
swift samsung-tv.swift doctor
```

See **SAMSUNG_TV_CLI.md** for full CLI documentation.

---

## TV Settings (required once)

Before the first connection, check this setting on the TV:

1. On the TV remote press **Menu** or the **Settings** gear.
2. Go to **General → External Device Manager → Device Connect Manager**.
3. Set **Access Notification** to **"First Time Only"** (not "Never").

On newer firmware (2022+) the path may be:
**General & Privacy → External Device Manager → Device Connect Manager**

This allows the pairing popup to appear. Once paired, the token is saved and this step is not needed again.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| No popup on TV when connecting | Set Access Notification to "First Time Only" in TV settings (see above) |
| Popup appeared but was not accepted | Tap **Reconnect** in the app, or re-run `swift samsung-tv.swift connect` |
| Buttons do nothing after connecting | Go to Settings → edit the TV entry → paste the token from `swift samsung-tv.swift status` |
| TV listed 3 times in Settings | Tap the trash icon to remove duplicates, keep one entry |
| App shows Disconnected on launch | Tap **Reconnect** next to the status dot |
| Build fails with "scheme not found" | Make sure Xcode Command Line Tools are installed: `xcode-select --install` |
| iOS build fails — no device found | Connect iPhone via USB, unlock it, and tap "Trust This Computer" |

For a detailed step-by-step diagnosis, run:

```bash
swift samsung-tv.swift doctor
```

Or open the app → Settings → **Help** tab.
