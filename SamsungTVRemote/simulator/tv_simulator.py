#!/usr/bin/env python3
"""
Samsung TV WebSocket Simulator
Mimics the Samsung Tizen TV WebSocket remote control API on port 8001.

Usage:
    python3 tv_simulator.py [--port 8001] [--verbose]

The simulator:
  - Accepts WebSocket connections on ws://localhost:8001/api/v2/channels/samsung.remote.control
  - Sends a pairing handshake with a fake token on connect
  - Accepts key commands (KEY_VOLUMEUP, KEY_POWER, etc.) and prints state changes
  - Accepts app launch events (ed.apps.launch)
  - Exposes a simple HTTP status page on http://localhost:8002/status
  - Tracks TV state: power, volume, channel, current app, mute
"""

import asyncio
import json
import http.server
import threading
import argparse
import time
from datetime import datetime, timezone

try:
    import websockets
except ImportError:
    print("ERROR: websockets library not found. Install with:")
    print("  pip install websockets")
    raise


# ── TV State ──────────────────────────────────────────────────────────────────

class TVState:
    def __init__(self):
        self.power      = True
        self.volume     = 20
        self.mute       = False
        self.channel    = 5
        self.current_app: str | None = None
        self.menu_open  = False
        self.connected_clients = 0
        self.command_log: list[dict] = []
        self.pairing_token = "SIMULATOR_TOKEN_ABC123"

    def apply_key(self, key_code: str) -> str:
        """Apply a key command and return a human-readable description."""
        ts = datetime.now().strftime("%H:%M:%S")
        result = ""

        if key_code == "KEY_POWER":
            self.power = not self.power
            self.current_app = None
            result = f"Power {'ON' if self.power else 'OFF'}"

        elif key_code == "KEY_VOLUMEUP":
            if not self.mute:
                self.volume = min(100, self.volume + 1)
            result = f"Volume: {self.volume}{'  [MUTED]' if self.mute else ''}"

        elif key_code == "KEY_VOLUMEDOWN":
            if not self.mute:
                self.volume = max(0, self.volume - 1)
            result = f"Volume: {self.volume}{'  [MUTED]' if self.mute else ''}"

        elif key_code == "KEY_MUTE":
            self.mute = not self.mute
            result = f"Mute: {'ON' if self.mute else 'OFF'}  (Volume: {self.volume})"

        elif key_code == "KEY_CHUP":
            self.channel += 1
            self.current_app = None
            result = f"Channel: {self.channel}"

        elif key_code == "KEY_CHDOWN":
            self.channel = max(1, self.channel - 1)
            self.current_app = None
            result = f"Channel: {self.channel}"

        elif key_code == "KEY_UP":    result = "D-pad UP"
        elif key_code == "KEY_DOWN":  result = "D-pad DOWN"
        elif key_code == "KEY_LEFT":  result = "D-pad LEFT"
        elif key_code == "KEY_RIGHT": result = "D-pad RIGHT"
        elif key_code == "KEY_ENTER": result = "OK / Enter"

        elif key_code == "KEY_RETURN":
            self.menu_open = False
            result = "Back"

        elif key_code == "KEY_HOME":
            self.current_app = None
            self.menu_open = False
            result = "Home screen"

        elif key_code == "KEY_MENU":
            self.menu_open = not self.menu_open
            result = f"Menu {'opened' if self.menu_open else 'closed'}"

        else:
            result = f"Unknown key: {key_code}"

        entry = {"time": ts, "key": key_code, "result": result}
        self.command_log.append(entry)
        if len(self.command_log) > 100:
            self.command_log.pop(0)
        return result

    def apply_app_launch(self, app_id: str) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        app_names = {
            "11101200001":    "Netflix",
            "111299001912":   "YouTube",
            "MCmYXNxgcu":     "Disney+",
            "3201910019365":  "Prime Video",
            "3201601007625":  "Hulu",
            "com.apple.appletv": "Apple TV+",
        }
        name = app_names.get(app_id, f"App({app_id})")
        self.current_app = name
        result = f"Launched: {name}"
        entry = {"time": ts, "key": f"LAUNCH:{app_id}", "result": result}
        self.command_log.append(entry)
        return result

    def status_dict(self) -> dict:
        return {
            "power":       self.power,
            "volume":      self.volume,
            "mute":        self.mute,
            "channel":     self.channel,
            "current_app": self.current_app,
            "menu_open":   self.menu_open,
            "clients":     self.connected_clients,
        }


TV = TVState()


# ── WebSocket Server ───────────────────────────────────────────────────────────

PAIRING_RESPONSE = {
    "event": "ms.channel.connect",
    "data": {
        "token": TV.pairing_token,
        "id":    "samsung-tv-simulator",
        "name":  "Samsung TV [Simulator]",
    }
}


async def handle_client(websocket):
    addr = websocket.remote_address
    TV.connected_clients += 1
    print(f"\n[{_ts()}] Client connected: {addr}  (total: {TV.connected_clients})")

    # Send pairing handshake
    await websocket.send(json.dumps(PAIRING_RESPONSE))
    print(f"[{_ts()}] Sent pairing handshake to {addr}")
    print_state()

    try:
        async for message in websocket:
            await process_message(message, addr)
    except Exception as e:
        print(f"[{_ts()}] Client {addr} disconnected: {e}")
    finally:
        TV.connected_clients -= 1
        print(f"[{_ts()}] Client gone: {addr}  (total: {TV.connected_clients})")


async def process_message(raw: str, addr):
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[{_ts()}] Bad JSON from {addr}: {raw[:80]}")
        return

    method = msg.get("method", "")
    params = msg.get("params", {})

    if method == "ms.remote.control":
        key = params.get("DataOfCmd", "")
        result = TV.apply_key(key)
        _log_command("KEY", key, result)

    elif method == "ms.channel.emit":
        event = params.get("event", "")
        data  = params.get("data", {})
        if event == "ed.apps.launch":
            app_id = data.get("appId", "unknown")
            result = TV.apply_app_launch(app_id)
            _log_command("APP", app_id, result)
        else:
            print(f"[{_ts()}] Unknown event: {event}")

    else:
        print(f"[{_ts()}] Unknown method: {method}")


def _log_command(kind: str, code: str, result: str):
    bar = "─" * 50
    print(f"\n{bar}")
    print(f"  [{_ts()}] {kind}: {code}")
    print(f"  → {result}")
    print_state()


def print_state():
    s = TV.status_dict()
    print(f"  TV State │ Power: {'ON' if s['power'] else 'OFF'} │ "
          f"Vol: {s['volume']}{'🔇' if s['mute'] else ''} │ "
          f"CH: {s['channel']} │ "
          f"App: {s['current_app'] or 'Live TV'}")


def _ts():
    return datetime.now().strftime("%H:%M:%S")


# ── HTTP Status Server ─────────────────────────────────────────────────────────

class StatusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            body = json.dumps(TV.status_dict(), indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/log":
            body = json.dumps(TV.command_log, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/":
            html = _status_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # suppress HTTP access logs


def _status_html() -> str:
    s = TV.status_dict()
    log_rows = "".join(
        f"<tr><td>{e['time']}</td><td><code>{e['key']}</code></td><td>{e['result']}</td></tr>"
        for e in reversed(TV.command_log[-20:])
    )
    return f"""<!DOCTYPE html>
<html>
<head>
  <title>Samsung TV Simulator</title>
  <meta http-equiv="refresh" content="2">
  <style>
    body {{ font-family: monospace; background: #1a1a2e; color: #eee; padding: 2rem; }}
    h1 {{ color: #00d4ff; }}
    .state {{ background: #16213e; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
    .on  {{ color: #00ff88; font-weight: bold; }}
    .off {{ color: #ff4444; font-weight: bold; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ padding: 6px 12px; border: 1px solid #333; text-align: left; }}
    th {{ background: #0f3460; }}
    code {{ color: #ffd700; }}
  </style>
</head>
<body>
  <h1>📺 Samsung TV Simulator</h1>
  <div class="state">
    <p>Power: <span class="{'on' if s['power'] else 'off'}">{'ON' if s['power'] else 'OFF'}</span></p>
    <p>Volume: {s['volume']} {'🔇 MUTED' if s['mute'] else ''}</p>
    <p>Channel: {s['channel']}</p>
    <p>App: {s['current_app'] or 'Live TV'}</p>
    <p>Connected clients: {s['clients']}</p>
  </div>
  <h2>Last 20 Commands</h2>
  <table>
    <tr><th>Time</th><th>Command</th><th>Result</th></tr>
    {log_rows}
  </table>
  <p style="color:#666;font-size:0.8em">Auto-refreshes every 2 seconds</p>
</body>
</html>"""


def run_http_server(port: int):
    server = http.server.HTTPServer(("0.0.0.0", port), StatusHandler)
    server.serve_forever()


# ── Entry Point ────────────────────────────────────────────────────────────────

async def main(ws_port: int, http_port: int):
    print("=" * 60)
    print("  Samsung TV WebSocket Simulator")
    print("=" * 60)
    print(f"  WebSocket : ws://localhost:{ws_port}/api/v2/channels/samsung.remote.control")
    print(f"  Status UI : http://localhost:{http_port}/")
    print(f"  JSON API  : http://localhost:{http_port}/status")
    print(f"  Command log: http://localhost:{http_port}/log")
    print("=" * 60)
    print(f"  Pairing token: {TV.pairing_token}")
    print("  Waiting for connections… (Ctrl+C to stop)")
    print()

    # Start HTTP status server in a background thread
    t = threading.Thread(target=run_http_server, args=(http_port,), daemon=True)
    t.start()

    # Start WebSocket server
    async with websockets.serve(handle_client, "0.0.0.0", ws_port):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Samsung TV WebSocket Simulator")
    parser.add_argument("--port",      type=int, default=8001, help="WebSocket port (default: 8001)")
    parser.add_argument("--http-port", type=int, default=8002, help="HTTP status port (default: 8002)")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.port, args.http_port))
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
