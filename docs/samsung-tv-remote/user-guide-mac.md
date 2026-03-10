# Samsung TV Remote — Mac User Guide

**Version:** 1.0
**Platform:** macOS 13 Ventura or later

---

## Getting Started

### What You Need
- Mac running macOS 13 (Ventura) or later
- Samsung Smart TV (2016 or newer, Tizen OS)
- Both Mac and TV on the **same Wi-Fi or wired network** for local control
- (Optional) SmartThings account for remote control when away from home

---

## Installation

### From the Mac App Store
1. Open the **App Store** on your Mac
2. Search for **Samsung TV Remote**
3. Click **Get**, then **Install**
4. Launch from Launchpad or Applications folder

### First Launch Permission

macOS will ask for network access on first launch:

> **"Samsung TV Remote" wants to accept incoming network connections.**

Click **Allow** — this lets the app receive pairing confirmations from your TV.

---

## Setting Up Your TV

### Step 1 — Open Preferences

Press **⌘,** or choose **Samsung TV Remote → Preferences** from the menu bar.

### Step 2 — Add Your TV

1. Click the **+** button in the TV list
2. Enter the TV's **IP address**
   - Find on your TV: `Settings → General → Network → Network Status → IP Settings`
3. Enter a **name** (e.g. "Living Room")
4. Enter the TV's **MAC address** (for Wake-on-LAN power-on)
   - Found at: `TV Settings → General → Network → Network Status`
5. Click **Save**

### Step 3 — Pair with TV

1. Click your TV in the list to connect
2. A dialog appears on your TV screen — on the **TV remote**, press **Allow**
3. Pairing is saved; you won't need to do this again

---

## The Remote Window

The app opens as a compact **floating panel** that stays in front of other windows so you can control your TV while working.

```
┌────────────────────────────┐
│ ⚡ Living Room    ⚙  [–][□] │
│ ● Connected (Local)        │
├────────────────────────────┤
│            (⏻)              │
├────────────────────────────┤
│          ▲                │
│      ◀   OK  ▶            │
│          ▼                │
├────────────────────────────┤
│  ⌂ Home   ← Back   ☰ Menu │
├────────────────────────────┤
│  VOL–  🔇  VOL+            │
│  CH–       CH+             │
├────────────────────────────┤
│  Netflix  YouTube  Disney+ │
│  Prime    Hulu    Apple TV+│
└────────────────────────────┘
```

### Keyboard Shortcuts

| Key | Action |
|---|---|
| ↑ ↓ ← → | D-pad navigation |
| Return / Enter | OK / Select |
| Escape | Back |
| ⌘H | Home |
| ⌘M | Menu |
| + / – | Volume up / down |
| M | Toggle mute |
| Page Up / Page Down | Channel up / down |
| Space | Toggle power |

### Power Button
- Click once to **toggle power** (on ↔ off)
- Turning on sends a **Wake-on-LAN** UDP packet — requires:
  `TV Settings → General → Network → Expert Settings → Power On with Mobile → ON`

### D-Pad
Click the directional arrows or use keyboard arrow keys to navigate TV menus.

### App Launcher
Click any app tile to launch it on your TV. The grid scrolls if you have more apps configured.

---

## Menu Bar

The app can optionally live in the **menu bar** for quick access without a window:

1. **Preferences → General → Show in menu bar** — enable the toggle
2. A TV icon (📺) appears in your menu bar
3. Click it to open a mini remote popover
4. Your main window stays hidden until you click **Show Full Remote** in the popover

---

## Connection Status

| Indicator | Meaning |
|---|---|
| 🟢 Connected (Local) | Direct Wi-Fi control — fastest response |
| 🟡 Connected (Cloud) | SmartThings cloud — works away from home |
| 🔴 Disconnected | TV unreachable; check power and network |

The app **automatically falls back to cloud** when local connection fails.

---

## Preferences (⌘,)

### TVs Tab
- Add, edit, or remove TVs
- Set default TV
- Re-pair (if TV has reset)

### Connection Tab
| Setting | Default | Description |
|---|---|---|
| Prefer local network | ON | Try WebSocket before cloud |
| Local timeout | 2 seconds | How long to wait for local before switching to cloud |
| Auto-reconnect | ON | Re-establish local connection when TV wakes |

### SmartThings Tab
- **Personal Access Token** — paste from `account.smartthings.com/tokens`
- **Discover Devices** — scans your SmartThings account for Samsung TVs
- **Token Scope Required:** Devices (read + write)

### Appearance Tab
| Setting | Options |
|---|---|
| Window always on top | ON / OFF |
| Show in menu bar | ON / OFF |
| Window size | Compact / Normal / Large |

---

## SmartThings Setup (Remote Control)

To control your TV when **not on home Wi-Fi**:

1. Visit `https://account.smartthings.com/tokens` in your browser
2. Sign in with your Samsung account
3. Click **Generate new token** → name it, select **Devices**, click **Generate**
4. Copy the token
5. In the app: **⌘, → SmartThings → paste token → Discover Devices**

---

## Troubleshooting

### TV doesn't respond
- Confirm Mac and TV are on the same network
- Try **Preferences → TVs → Re-pair**
- Check macOS firewall: **System Settings → Network → Firewall → Options** — ensure Samsung TV Remote is allowed

### Power On doesn't work
- Verify MAC address in Preferences matches `ifconfig` output on the TV
- Enable on TV: `Settings → General → Network → Expert Settings → Power On with Mobile`
- Some routers block UDP broadcasts — try connecting Mac directly to same switch as TV

### Keyboard shortcuts not working
- Ensure the Remote window is focused (click on it first)
- Some keys (like arrow keys) may be captured by the window manager if the TV list is selected — click the D-pad area first

### "Disconnected" even when TV is on
- TV may have cleared the pairing whitelist after an update — Re-pair in Preferences
- Check TV's Wi-Fi: `TV Settings → General → Network → Network Status`

### App won't open after macOS update
- Open **System Settings → Privacy & Security → Local Network** — ensure Samsung TV Remote is listed and enabled

---

## Uninstalling

1. Quit the app: **Samsung TV Remote → Quit** (or ⌘Q)
2. Drag **Samsung TV Remote.app** from Applications to Trash
3. To remove all data: delete `~/Library/Application Support/SamsungTVRemote/` and `~/Library/Preferences/com.yourcompany.samsungremote.mac.plist`
4. To remove the Keychain entry: open **Keychain Access**, search for "SamsungTVRemote", delete the entry
