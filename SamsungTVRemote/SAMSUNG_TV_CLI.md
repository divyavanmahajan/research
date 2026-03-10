# samsung-tv.swift — Samsung TV Remote CLI

A zero-dependency Swift script that lets you control any Samsung Tizen TV (2016+) from the command line. Connect, pair, send keys, launch apps, scan for TVs on the network, and diagnose connection problems — all in one file.

No Xcode project required. Run directly with `swift samsung-tv.swift`.

---

## Quick Start

```bash
# 1. Find your TV on the network
swift samsung-tv.swift scan

# 2. Connect and pair (TV will show an "Allow remote control?" popup)
swift samsung-tv.swift connect 192.168.1.42

# 3. Send a key
swift samsung-tv.swift key home

# 4. Launch Netflix
swift samsung-tv.swift app netflix
```

Credentials are saved automatically to `~/.samsung-tv.json` after a successful connect. All subsequent commands use the saved IP and token — you only need to pair once.

---

## Installation

No installation step is needed. The script requires Swift (available on any Mac with Xcode Command Line Tools):

```bash
xcode-select --install   # if Swift is not already installed
```

Copy `samsung-tv.swift` to any directory and run it with `swift samsung-tv.swift`.

**Optional — make it executable:**

```bash
chmod +x samsung-tv.swift
./samsung-tv.swift scan         # shortcut if the file is executable
```

Or add a shell alias to `~/.zshrc`:

```bash
alias samsung-tv="swift /path/to/samsung-tv.swift"
samsung-tv scan
```

---

## Command Reference

| Command | Description |
|---|---|
| `connect [IP]` | Connect and pair with a TV, save credentials |
| `status` | Show saved config and current TV health |
| `key KEY [KEY2 ...]` | Send one or more key presses |
| `app NAME` | Launch a streaming app |
| `scan` | Discover Samsung TVs on the local network (SSDP) |
| `forget` | Delete saved config (`~/.samsung-tv.json`) |
| `keys` | Print all supported key names and KEY_* codes |
| `apps` | Print all known app names and their App IDs |
| `doctor [IP]` | Run numbered step-by-step connection diagnostics |

---

## Detailed Command Reference

### `connect [IP]`

Connects to a Samsung TV, performs the WebSocket pairing handshake, and saves the IP, TV name, and token to `~/.samsung-tv.json`.

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `IP` | No | IP address of the TV. If omitted, the saved IP is used. |

**What it does:**

1. Fetches the TV name from the REST API (`http://IP:8001/api/v2/`).
2. Opens a WSS connection to port 8002.
3. If the TV responds with "unauthorized", prints step-by-step instructions for accepting the pairing popup on the TV screen, waits 25 seconds, then reconnects automatically.
4. On success, saves `~/.samsung-tv.json` with IP, TV name, and pairing token.

**Examples:**

```bash
# Connect to a specific IP (first time)
swift samsung-tv.swift connect 192.168.1.42

# Reconnect using the saved IP
swift samsung-tv.swift connect

# Override the saved IP without forgetting it permanently
swift samsung-tv.swift connect 192.168.1.99
```

**Saved config format (`~/.samsung-tv.json`):**

```json
{
  "ip": "192.168.1.42",
  "name": "Samsung AU7105 43 TV",
  "token": "10105999"
}
```

---

### `status`

Displays the saved config and probes the TV for live status information.

**What it shows:**

- Saved TV name, IP, and masked token (first 3 chars + `***`)
- REST API: PowerState, model name, OS version, network type
- WebSocket: Connected / Unauthorized / Timeout

**Example:**

```bash
swift samsung-tv.swift status
```

```
── Saved Config ──
   Name:  Samsung AU7105 43 TV
   IP:    192.168.1.42
   Token: 101***

── REST API  http://192.168.1.42:8001/api/v2/ ──
   ✓  Reachable
   PowerState:  on
   Model:       UA43AU7105KXXL
   OS:          Tizen
   Network:     wireless

── WebSocket  wss://192.168.1.42:8002 ──
   ✓  Connected
```

---

### `key KEY [KEY2 ...]`

Sends one or more remote-control key presses. Keys are sent sequentially using the WebSocket connection.

**Arguments:**

| Argument | Description |
|---|---|
| `KEY` | Key name (friendly or raw `KEY_*` code). Multiple keys accepted. |

**Key resolution:**

Friendly names are mapped to Samsung key codes automatically. Raw `KEY_*` codes are passed through unchanged. See the [Key Reference](#key-reference) table below for all mappings.

**Examples:**

```bash
# Single key
swift samsung-tv.swift key home

# Multiple keys in sequence
swift samsung-tv.swift key volup volup volup

# Change channel up
swift samsung-tv.swift key channelup

# Raw KEY_* code
swift samsung-tv.swift key KEY_MENU

# Navigate: down, down, enter
swift samsung-tv.swift key down down enter
```

---

### `app NAME`

Launches a streaming app on the TV using the Samsung REST API.

**Arguments:**

| Argument | Description |
|---|---|
| `NAME` | App name (case-insensitive). See [App Reference](#app-reference) for all names. |

**Examples:**

```bash
swift samsung-tv.swift app netflix
swift samsung-tv.swift app youtube
swift samsung-tv.swift app disney+
swift samsung-tv.swift app prime
swift samsung-tv.swift app appletv
swift samsung-tv.swift app spotify
```

The TV must be on and the app must be installed. The CLI sends a POST request to `http://IP:8001/api/v2/applications/APP_ID`.

---

### `scan`

Sends an SSDP M-SEARCH broadcast to discover Samsung TVs on the local network. Listens for 5 seconds for responses, then fetches UPnP XML and REST API info from each TV found.

**Example:**

```bash
swift samsung-tv.swift scan
```

```
── SSDP Scan (Samsung TVs on local network) ──
   Sending M-SEARCH to 239.255.255.250:1900…
   Listening 5 seconds for responses…

+----------------+-------------------------+--------------------+
| IP             | Friendly Name           | Model              |
+----------------+-------------------------+--------------------+
| 192.168.1.42   | Samsung AU7105 43 TV    | UA43AU7105KXXL     |
+----------------+-------------------------+--------------------+

   To connect to a TV:
     swift samsung-tv.swift connect 192.168.1.42
```

**Notes:**

- TV must be powered on for SSDP to respond.
- If no TVs appear, try `connect <IP>` directly (SSDP is unreliable on some network configurations).

---

### `forget`

Deletes the saved config file (`~/.samsung-tv.json`). Use this to reset the pairing or switch to a different TV.

**Example:**

```bash
swift samsung-tv.swift forget
# ✓  Config deleted: /Users/you/.samsung-tv.json

# Then connect to a new TV
swift samsung-tv.swift connect 192.168.1.99
```

---

### `keys`

Prints a table of all supported friendly key names and their `KEY_*` codes, grouped by category.

**Example:**

```bash
swift samsung-tv.swift keys
```

```
── Supported Key Names ──

  Navigation
  +------------------------+------------+
  | Friendly Name          | KEY_* Code |
  +------------------------+------------+
  | up                     | KEY_UP     |
  | down                   | KEY_DOWN   |
  ...
```

---

### `apps`

Prints a table of all known streaming app names and their Samsung App IDs.

**Example:**

```bash
swift samsung-tv.swift apps
```

---

### `doctor [IP]`

Runs four numbered diagnostic steps against the TV and prints colored results with specific fix instructions for any failures.

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `IP` | No | IP to diagnose. If omitted, uses saved IP. |

**Diagnostic steps:**

| Step | What it checks |
|---|---|
| 1 | TCP connectivity (port 80 probe — proxy for "ping") |
| 2 | REST API (`GET http://IP:8001/api/v2/` → HTTP 200) |
| 3 | WebSocket port open (TCP probe on port 8002) |
| 4 | WebSocket handshake (full WSS connect attempt) |

**Example:**

```bash
swift samsung-tv.swift doctor
swift samsung-tv.swift doctor 192.168.1.42
```

```
── Diagnostics for Samsung TV at 192.168.1.42 ──

  Step 1: TV reachable (TCP probe on port 80)
   ✓  TCP port 80 responded — TV is reachable on the network

  Step 2: REST API  (GET http://192.168.1.42:8001/api/v2/)
   ✓  REST API returned HTTP 200
   Name:  Samsung AU7105 43 TV
   Model: UA43AU7105KXXL
   Power: on

  Step 3: WebSocket port 8002 reachable (TCP probe)
   ✓  TCP port 8002 is open

  Step 4: WebSocket handshake (WSS connect attempt)
   ✓  WebSocket handshake succeeded

   ✓  All diagnostics passed — your TV should be working with this CLI.
```

---

## Complete Example Workflow

This walkthrough covers a full first-time setup from zero to controlling the TV.

### Step 1 — Discover the TV

```bash
swift samsung-tv.swift scan
```

The TV must be on. Note the IP address printed in the table (e.g., `192.168.1.42`).

If the scan finds nothing (SSDP is sometimes blocked by routers), skip to Step 2 and supply the IP manually.

### Step 2 — Connect and Pair

```bash
swift samsung-tv.swift connect 192.168.1.42
```

The TV will display an **"Allow remote control?"** popup.

1. Pick up the TV remote.
2. Select **"Allow"**.

The CLI waits 25 seconds for you to accept, then automatically reconnects and saves credentials to `~/.samsung-tv.json`.

```
── Connecting to Samsung TV at 192.168.1.42 ──
   ✓  REST API reachable — Samsung AU7105 43 TV
   Attempting WSS connection (port 8002)…

   The TV is showing a pairing popup. Steps:
     1. Look at the TV screen now — a dialog should say "Allow remote control?"
     2. Use the TV remote to select "Allow".
     ...
   Waiting 25 seconds for you to accept the popup on the TV…
   Reconnecting…
   ✓  Connected to "Samsung AU7105 43 TV"
   IP:    192.168.1.42
   Token: 101***
   Config saved to /Users/you/.samsung-tv.json
```

### Step 3 — Check Status

```bash
swift samsung-tv.swift status
```

Confirms that the saved config is correct and the TV is reachable.

### Step 4 — Send Keys

```bash
# Go to home screen
swift samsung-tv.swift key home

# Raise volume three times
swift samsung-tv.swift key volup volup volup

# Mute
swift samsung-tv.swift key mute

# Navigate a menu: down, down, select
swift samsung-tv.swift key down down enter

# Go back
swift samsung-tv.swift key back
```

### Step 5 — Launch an App

```bash
swift samsung-tv.swift app netflix
swift samsung-tv.swift app youtube
swift samsung-tv.swift app disney+
```

### Step 6 — Run Doctor if Anything Is Wrong

```bash
swift samsung-tv.swift doctor
```

This prints specific fix instructions for each failed step.

### Step 7 — Forget and Reconnect to a Different TV

```bash
swift samsung-tv.swift forget
swift samsung-tv.swift connect 192.168.1.99
```

---

## Troubleshooting

### "Allow remote control?" popup — step-by-step

When you first connect, the TV shows a pairing dialog. If the CLI detects the unauthorized response, it prints these steps automatically:

1. **Look at the TV screen** — a dialog should say "Allow remote control?"
2. **Use the TV remote** to select **"Allow"**.
3. If no popup appeared:
   - On the TV go to **Settings → General → External Device Manager → Device Connect Manager → Access Notification**
   - Set it to **"First Time Only"** (not "Never").
   - If it was already "First Time Only", the TV may have a stored decision. Go to the same menu, open **"Allowed/Blocked Devices"**, and remove this device's entry, then retry.
4. After accepting, the CLI will automatically reconnect.

### Connection timeout

```
✗ Could not connect. Check:
  1. TV and this Mac are on the same Wi-Fi network.
  2. TV is powered on (not in deep sleep — try the power button first).
  3. Port 8002 is not blocked by a router firewall.
  4. Run: swift samsung-tv.swift doctor   for a full step-by-step diagnosis.
```

### Keys not working after reconnect

The pairing token may have expired. Reconnect to get a fresh token:

```bash
swift samsung-tv.swift connect
```

### App launch fails

- Ensure the app is installed on the TV.
- The TV must be fully on (not in standby).
- Some app IDs are region-specific — the TV may reject the launch silently.

### SSDP scan finds nothing

Some routers block UDP multicast between devices. Alternatives:

- Check your router's DHCP client list for a device named "Samsung" and note its IP.
- Look in the TV's **Settings → General → Network → Network Status** for its IP.
- Then connect directly: `swift samsung-tv.swift connect <IP>`

---

## Key Reference

| Friendly Name | KEY_* Code | Category |
|---|---|---|
| up | KEY_UP | Navigation |
| down | KEY_DOWN | Navigation |
| left | KEY_LEFT | Navigation |
| right | KEY_RIGHT | Navigation |
| ok / enter / select | KEY_ENTER | Navigation |
| back / return | KEY_RETURN | Navigation |
| home | KEY_HOME | Navigation |
| menu | KEY_MENU | Navigation |
| volup / volumeup | KEY_VOLUP | Volume |
| voldown / volumedown | KEY_VOLDOWN | Volume |
| mute | KEY_MUTE | Volume |
| chup / channelup | KEY_CHUP | Channel |
| chdown / channeldown | KEY_CHDOWN | Channel |
| power | KEY_POWER | System |

**Raw codes:** Any `KEY_*` string not in the table above is passed through to the TV as-is. The TV firmware defines hundreds of additional codes — consult Samsung's Tizen SDK documentation for the full list.

---

## App Reference

| Friendly Name(s) | App Name | App ID |
|---|---|---|
| netflix | Netflix | 3201907018807 |
| youtube | YouTube | 111299001912 |
| disney, disney+ | Disney+ | 3201901017640 |
| prime, primevideo, amazon | Prime Video | 3201910019365 |
| appletv, appletvplus | Apple TV+ | 3201807016597 |
| spotify | Spotify | 3201606009684 |

App IDs are Samsung's internal identifiers. They are model- and region-independent for the apps listed above, but Samsung may change them in firmware updates.

---

## Technical Notes

- **WebSocket:** Uses `URLSessionWebSocketTask` over WSS (port 8002) with a custom `URLSessionDelegate` that accepts Samsung's self-signed TLS certificate.
- **App name sent to TV:** `SamsungTVCLI` encoded as Base64 (`U2Ftc3VuZ1RWQ0xJ`).
- **Config location:** `~/.samsung-tv.json`
- **Dependencies:** None — pure Foundation + Darwin (ships with macOS).
- **Token lifetime:** Pairing tokens are persistent on supported firmware. If the TV is factory reset, run `swift samsung-tv.swift connect` again.
- **Compatibility:** Tizen-based Samsung TVs from 2016 onwards (models with the `ms.remote.control` WebSocket API). Pre-2016 models using the legacy TCP protocol on port 55000 are not supported by this CLI.
