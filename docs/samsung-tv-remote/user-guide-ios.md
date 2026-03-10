# Samsung TV Remote — iOS User Guide

**Version:** 1.0
**Platform:** iPhone (iOS 16+)

---

## Getting Started

### What You Need
- iPhone running iOS 16 or later
- Samsung Smart TV (2016 or newer, Tizen OS)
- Both iPhone and TV on the **same Wi-Fi network** for local control
- (Optional) SmartThings account for remote control over the internet

---

## First Launch

### Step 1 — Allow Local Network Access

On first launch, iOS will ask:

> **"Samsung TV Remote" would like to find and connect to devices on your local network.**

Tap **Allow**. This permission is required for the app to discover and control your TV directly over Wi-Fi. Without it, the app falls back to the SmartThings cloud (slower).

### Step 2 — Add Your TV

1. Tap the **Settings** button (gear icon, top-right)
2. Tap **Add TV**
3. Enter your TV's IP address
   - Find it on your TV: `Settings → General → Network → Network Status → IP Settings`
4. Enter your TV's name (e.g. "Living Room TV")
5. Tap **Save**

### Step 3 — Pair with Your TV

1. Tap your TV in the device list
2. On your TV, a dialog appears: **"Allow access from Samsung TV Remote?"**
3. On your TV remote, press **Allow**
4. Your iPhone is now paired — this is a one-time step

> **Tip:** If the pairing dialog doesn't appear, ensure your TV's network is active and try restarting the TV's SmartThings or smart hub service in `Settings → Support → Device Care`.

---

## The Remote Screen

```
┌────────────────────────┐
│  ⚡ Living Room TV  ⚙  │  ← TV name + Settings
│  ● Connected (Local)   │  ← Connection status
├────────────────────────┤
│         (⏻)            │  ← Power button
├────────────────────────┤
│      ▲               │
│   ◀  OK  ▶          │  ← D-pad + OK
│      ▼               │
├────────────────────────┤
│  ⌂ Home  ← Back  ☰ Menu│
├────────────────────────┤
│  VOL ▲  VOL ▼   🔇   │  ← Volume + Mute
│  CH  ▲  CH  ▼        │  ← Channel
├────────────────────────┤
│  [Netflix] [YouTube]   │
│  [Disney+] [Prime]     │  ← App Launcher
│  [Hulu]   [Apple TV+]  │
└────────────────────────┘
```

### Power Button
- **Tap once** — Turns TV off (if on) or on (if off)
- Turning **on** uses Wake-on-LAN; your TV must have "Power On with Mobile" enabled:
  `TV Settings → General → Network → Expert Settings → Power On with Mobile → ON`

### D-Pad
| Button | Action |
|---|---|
| ▲ ▼ ◀ ▶ | Navigate menus / move cursor |
| OK | Select / confirm |
| Back (←) | Go back one level |
| Home (⌂) | Return to TV home screen |
| Menu (☰) | Open TV settings menu |

### Volume & Channel
| Button | Action |
|---|---|
| VOL ▲ | Volume up |
| VOL ▼ | Volume down |
| 🔇 | Toggle mute |
| CH ▲ | Channel up |
| CH ▼ | Channel down |

### App Launcher
Tap any app tile to launch it directly on your TV. The TV will switch to that app immediately.

To scroll: swipe left/right on the app grid for more apps.

---

## Connection Status Indicator

| Indicator | Meaning |
|---|---|
| 🟢 Connected (Local) | Controlling TV directly on your Wi-Fi — fastest |
| 🟡 Connected (Cloud) | Controlling via SmartThings cloud — works remotely |
| 🔴 Disconnected | Cannot reach TV; check network and TV power |

When local connection fails, the app **automatically switches to cloud** without any action from you.

---

## Settings

Open **Settings** (gear icon) to configure:

### TV Settings
- **TV Name** — Friendly display name
- **IP Address** — Local network IP of your TV
- **MAC Address** — For Wake-on-LAN power-on

### SmartThings (Optional)
- **Personal Access Token** — From `account.smartthings.com/tokens`
- **Device ID** — Auto-discovered after entering your token

### Connection Preferences
- **Prefer Local** — Try Wi-Fi first (recommended, default ON)
- **Local Timeout** — Seconds before falling back to cloud (default: 2s)

---

## SmartThings Setup (Optional — for Remote Control)

If you want to control your TV when **not on your home Wi-Fi**:

1. Open a browser and go to: `https://account.smartthings.com/tokens`
2. Sign in with your Samsung account
3. Tap **Generate new token**
4. Name it (e.g. "TV Remote App"), select **Devices** scope, tap **Generate**
5. Copy the token
6. In the app: **Settings → SmartThings → Paste token**
7. Tap **Find My TVs** — the app will auto-discover your Samsung TV

---

## Troubleshooting

### TV doesn't respond to commands
- Confirm TV and iPhone are on the same Wi-Fi network
- Restart the TV (hold power button on TV remote for 5 seconds)
- In app: **Settings → Re-pair TV**

### Power On doesn't work
- Enable on TV: `Settings → General → Network → Expert Settings → Power On with Mobile`
- Verify the MAC address in Settings matches your TV's MAC
- Your router must support UDP broadcast forwarding

### App shows "Disconnected" even though TV is on
- TV may have reset the pairing; tap **Settings → Re-pair TV**
- Check TV is connected to Wi-Fi: `TV Settings → General → Network`

### SmartThings shows no devices
- Confirm your Samsung TV is added in the SmartThings mobile app first
- Ensure the token has **Devices** read/write scope
- Token may be expired — regenerate at `account.smartthings.com/tokens`

---

## Privacy & Data

- Your SmartThings token is stored encrypted in iOS Keychain
- The app does **not** collect analytics or send data to any third party
- Local WebSocket traffic stays entirely on your home network
- The only external connection is to `api.smartthings.com` (Samsung's servers) when using cloud fallback
