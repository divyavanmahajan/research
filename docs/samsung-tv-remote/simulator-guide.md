# Samsung TV Simulator — Guide

**Version:** 1.0
**Location:** `SamsungTVRemote/simulator/`

The Samsung TV Simulator is a Python WebSocket server that accurately mimics the Samsung Tizen TV remote control API. Use it to develop and test both the iOS and Mac apps **without needing a real Samsung TV**.

---

## What It Simulates

| Feature | Simulated |
|---|---|
| WebSocket pairing handshake (token exchange) | ✅ |
| All D-pad keys (UP/DOWN/LEFT/RIGHT/OK/BACK) | ✅ |
| Volume up/down/mute (clamped 0–100) | ✅ |
| Channel up/down (min 1) | ✅ |
| Power toggle | ✅ |
| App launch (Netflix, YouTube, Disney+, etc.) | ✅ |
| Multiple simultaneous client connections | ✅ |
| TV state tracking + command log | ✅ |
| HTTP status API + live dashboard | ✅ |

---

## Quick Start

```bash
cd SamsungTVRemote/simulator

# Install dependencies
pip install -r requirements.txt

# Start the simulator
python3 tv_simulator.py
```

Output:
```
============================================================
  Samsung TV WebSocket Simulator
============================================================
  WebSocket : ws://localhost:8001/api/v2/channels/samsung.remote.control
  Status UI : http://localhost:8002/
  JSON API  : http://localhost:8002/status
  Command log: http://localhost:8002/log
============================================================
  Pairing token: SIMULATOR_TOKEN_ABC123
  Waiting for connections…
```

---

## Connecting the App to the Simulator

### iOS (Simulator or Device on same network)

1. Open the Samsung TV Remote app
2. Go to **Settings → Add TV**
3. Set **IP Address** to:
   - `127.0.0.1` if running on Mac Simulator
   - Your Mac's local IP (e.g. `192.168.1.10`) if running on physical iPhone
4. Set **Name** to `TV Simulator`
5. Save — the app will connect and receive the pairing token automatically

### macOS

1. Open the Mac app
2. **⌘, → TVs → Add TV**
3. Set IP to `127.0.0.1`, save
4. The app connects instantly

---

## Monitoring TV State

### Live Dashboard (browser)
Open `http://localhost:8002/` — auto-refreshes every 2 seconds showing power, volume, channel, current app, and the last 20 commands.

### JSON API
```bash
curl http://localhost:8002/status | python3 -m json.tool
```
```json
{
  "power": true,
  "volume": 22,
  "mute": false,
  "channel": 5,
  "current_app": "Netflix",
  "menu_open": false,
  "clients": 1
}
```

### Command Log
```bash
curl http://localhost:8002/log
```

---

## Running the Test Suite

The test suite validates all commands using the same WebSocket protocol as the real app.

```bash
cd SamsungTVRemote/simulator

# Start simulator (in background)
python3 tv_simulator.py &

# Run all tests
python3 -m pytest tests/ -v
```

### Test Coverage

| Test Class | What is tested |
|---|---|
| `TestPairing` | Handshake, token, multi-client |
| `TestVolumeControl` | Vol+/−, mute, bounds (0–100), muted-vol-unchanged |
| `TestChannelControl` | CH+/−, lower bound (ch 1) |
| `TestNavigation` | D-pad keys, Home clears app, CH change clears app |
| `TestPowerControl` | Power toggle, power-off clears app |
| `TestAppLauncher` | Netflix, YouTube, Disney+, Prime, unknown app |
| `TestHTTPStatusAPI` | JSON API, log endpoint, HTML page |

All 24 tests pass against the simulator.

---

## Simulator Command Line Options

```bash
python3 tv_simulator.py --help

# Custom ports
python3 tv_simulator.py --port 9001 --http-port 9002
```

---

## Using `showboat` to Demo the Simulator

```bash
uvx showboat init docs/samsung-tv-remote/demo-session.md "Samsung TV Simulator Demo"

uvx showboat note docs/samsung-tv-remote/demo-session.md \
  "Start the simulator and check the initial TV state."

uvx showboat exec docs/samsung-tv-remote/demo-session.md bash \
  "curl -s http://localhost:8002/status | python3 -m json.tool"

uvx showboat note docs/samsung-tv-remote/demo-session.md \
  "Run the full test suite against the simulator."

uvx showboat exec docs/samsung-tv-remote/demo-session.md bash \
  "cd SamsungTVRemote/simulator && python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30"
```

---

## Using `rodney` to Validate the Simulator Dashboard

```bash
uvx rodney start

# Open the live dashboard
uvx rodney open http://localhost:8002/

# Wait for the page to load
uvx rodney waitload

# Assert the TV state is shown
uvx rodney assert "document.body.innerText.includes('Volume')" "true" \
  -m "Dashboard should show Volume"

# Take a screenshot of the dashboard
uvx rodney screenshot docs/samsung-tv-remote/screenshots/simulator-dashboard.png

uvx rodney stop
```
