#!/usr/bin/env python3
"""
Integration tests for the Samsung TV Simulator.
Connects via WebSocket (like the real iOS/Mac app would) and validates
that every command produces the correct state change.

Usage:
    # Start simulator first:
    python3 ../tv_simulator.py &

    # Run tests:
    python3 test_simulator.py

    # Or run via pytest:
    pip install pytest pytest-asyncio websockets
    pytest test_simulator.py -v
"""

import asyncio
import json
import time
import subprocess
import sys
import os
import signal
import pytest
import websockets
import urllib.request

WS_URL  = "ws://localhost:8001/api/v2/channels/samsung.remote.control?name=U2Ftc3VuZ1RWUmVtb3Rl"
HTTP_URL = "http://localhost:8002"


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_tv_state() -> dict:
    """Fetch current TV state from the simulator HTTP API."""
    with urllib.request.urlopen(f"{HTTP_URL}/status", timeout=3) as r:
        return json.loads(r.read())


async def connect_ws():
    """Connect to the simulator WebSocket and consume the pairing handshake."""
    ws = await websockets.connect(WS_URL)
    # Consume pairing ack
    msg = await asyncio.wait_for(ws.recv(), timeout=3)
    data = json.loads(msg)
    assert data["event"] == "ms.channel.connect", f"Expected pairing ack, got: {data}"
    assert "token" in data["data"], "Expected token in pairing data"
    return ws


async def send_key(ws, key_code: str):
    payload = json.dumps({
        "method": "ms.remote.control",
        "params": {
            "Cmd":          "Click",
            "DataOfCmd":    key_code,
            "Option":       "false",
            "TypeOfRemote": "SendRemoteKey"
        }
    })
    await ws.send(payload)
    await asyncio.sleep(0.1)  # let simulator process


async def send_app_launch(ws, app_id: str):
    payload = json.dumps({
        "method": "ms.channel.emit",
        "params": {
            "event": "ed.apps.launch",
            "to":    "host",
            "data": {
                "appId":       app_id,
                "action_type": "NATIVE_LAUNCH"
            }
        }
    })
    await ws.send(payload)
    await asyncio.sleep(0.1)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def simulator():
    """Start the TV simulator as a subprocess for the test session."""
    proc = subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(__file__), "..", "tv_simulator.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    time.sleep(1.5)  # wait for simulator to start
    yield proc
    proc.send_signal(signal.SIGINT)
    proc.wait(timeout=5)


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestPairing:
    @pytest.mark.asyncio
    async def test_pairing_handshake(self, simulator):
        """First connection receives a ms.channel.connect event with a token."""
        ws = await websockets.connect(WS_URL)
        msg = await asyncio.wait_for(ws.recv(), timeout=3)
        data = json.loads(msg)
        assert data["event"] == "ms.channel.connect"
        assert isinstance(data["data"]["token"], str)
        assert len(data["data"]["token"]) > 0
        await ws.close()

    @pytest.mark.asyncio
    async def test_multiple_clients(self, simulator):
        """Simulator accepts multiple simultaneous connections."""
        ws1 = await connect_ws()
        ws2 = await connect_ws()
        state = get_tv_state()
        assert state["clients"] == 2
        await ws1.close()
        await ws2.close()
        await asyncio.sleep(0.2)
        state = get_tv_state()
        assert state["clients"] == 0


class TestVolumeControl:
    @pytest.mark.asyncio
    async def test_volume_up(self, simulator):
        ws = await connect_ws()
        before = get_tv_state()["volume"]
        await send_key(ws, "KEY_VOLUMEUP")
        after = get_tv_state()["volume"]
        assert after == before + 1, f"Expected volume {before+1}, got {after}"
        await ws.close()

    @pytest.mark.asyncio
    async def test_volume_down(self, simulator):
        ws = await connect_ws()
        # Raise volume first so we're not at 0
        await send_key(ws, "KEY_VOLUMEUP")
        await send_key(ws, "KEY_VOLUMEUP")
        before = get_tv_state()["volume"]
        await send_key(ws, "KEY_VOLUMEDOWN")
        after = get_tv_state()["volume"]
        assert after == before - 1
        await ws.close()

    @pytest.mark.asyncio
    async def test_volume_does_not_go_below_zero(self, simulator):
        ws = await connect_ws()
        # Force volume to 0
        for _ in range(110):
            await send_key(ws, "KEY_VOLUMEDOWN")
        state = get_tv_state()
        assert state["volume"] == 0
        await ws.close()

    @pytest.mark.asyncio
    async def test_volume_does_not_exceed_100(self, simulator):
        ws = await connect_ws()
        for _ in range(110):
            await send_key(ws, "KEY_VOLUMEUP")
        state = get_tv_state()
        assert state["volume"] == 100
        await ws.close()

    @pytest.mark.asyncio
    async def test_mute_toggle(self, simulator):
        ws = await connect_ws()
        before = get_tv_state()["mute"]
        await send_key(ws, "KEY_MUTE")
        after = get_tv_state()["mute"]
        assert after != before, "Mute should toggle"
        # Toggle back
        await send_key(ws, "KEY_MUTE")
        assert get_tv_state()["mute"] == before
        await ws.close()

    @pytest.mark.asyncio
    async def test_volume_unchanged_when_muted(self, simulator):
        ws = await connect_ws()
        # Ensure muted
        state = get_tv_state()
        if not state["mute"]:
            await send_key(ws, "KEY_MUTE")
        vol_before = get_tv_state()["volume"]
        await send_key(ws, "KEY_VOLUMEUP")
        assert get_tv_state()["volume"] == vol_before, "Volume should not change while muted"
        # Unmute
        await send_key(ws, "KEY_MUTE")
        await ws.close()


class TestChannelControl:
    @pytest.mark.asyncio
    async def test_channel_up(self, simulator):
        ws = await connect_ws()
        before = get_tv_state()["channel"]
        await send_key(ws, "KEY_CHUP")
        assert get_tv_state()["channel"] == before + 1
        await ws.close()

    @pytest.mark.asyncio
    async def test_channel_down(self, simulator):
        ws = await connect_ws()
        # Make sure channel > 1
        await send_key(ws, "KEY_CHUP")
        await send_key(ws, "KEY_CHUP")
        before = get_tv_state()["channel"]
        await send_key(ws, "KEY_CHDOWN")
        assert get_tv_state()["channel"] == before - 1
        await ws.close()

    @pytest.mark.asyncio
    async def test_channel_does_not_go_below_1(self, simulator):
        ws = await connect_ws()
        for _ in range(20):
            await send_key(ws, "KEY_CHDOWN")
        assert get_tv_state()["channel"] == 1
        await ws.close()


class TestNavigation:
    @pytest.mark.asyncio
    async def test_dpad_keys_accepted(self, simulator):
        """D-pad keys don't raise errors — simulator accepts them."""
        ws = await connect_ws()
        for key in ["KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_ENTER"]:
            await send_key(ws, key)
        # State should not have changed in any tracked field
        state = get_tv_state()
        assert state is not None
        await ws.close()

    @pytest.mark.asyncio
    async def test_home_clears_app(self, simulator):
        ws = await connect_ws()
        # Launch an app first
        await send_app_launch(ws, "11101200001")
        assert get_tv_state()["current_app"] == "Netflix"
        # Press Home
        await send_key(ws, "KEY_HOME")
        assert get_tv_state()["current_app"] is None
        await ws.close()

    @pytest.mark.asyncio
    async def test_channel_change_clears_app(self, simulator):
        ws = await connect_ws()
        await send_app_launch(ws, "111299001912")
        assert get_tv_state()["current_app"] == "YouTube"
        await send_key(ws, "KEY_CHUP")
        assert get_tv_state()["current_app"] is None
        await ws.close()


class TestPowerControl:
    @pytest.mark.asyncio
    async def test_power_toggle(self, simulator):
        ws = await connect_ws()
        before = get_tv_state()["power"]
        await send_key(ws, "KEY_POWER")
        assert get_tv_state()["power"] != before
        # Toggle back
        await send_key(ws, "KEY_POWER")
        assert get_tv_state()["power"] == before
        await ws.close()

    @pytest.mark.asyncio
    async def test_power_off_clears_app(self, simulator):
        ws = await connect_ws()
        await send_app_launch(ws, "11101200001")
        await send_key(ws, "KEY_POWER")  # off
        assert get_tv_state()["current_app"] is None
        await send_key(ws, "KEY_POWER")  # back on
        await ws.close()


class TestAppLauncher:
    @pytest.mark.asyncio
    async def test_launch_netflix(self, simulator):
        ws = await connect_ws()
        await send_app_launch(ws, "11101200001")
        assert get_tv_state()["current_app"] == "Netflix"
        await ws.close()

    @pytest.mark.asyncio
    async def test_launch_youtube(self, simulator):
        ws = await connect_ws()
        await send_app_launch(ws, "111299001912")
        assert get_tv_state()["current_app"] == "YouTube"
        await ws.close()

    @pytest.mark.asyncio
    async def test_launch_disney_plus(self, simulator):
        ws = await connect_ws()
        await send_app_launch(ws, "MCmYXNxgcu")
        assert get_tv_state()["current_app"] == "Disney+"
        await ws.close()

    @pytest.mark.asyncio
    async def test_launch_prime_video(self, simulator):
        ws = await connect_ws()
        await send_app_launch(ws, "3201910019365")
        assert get_tv_state()["current_app"] == "Prime Video"
        await ws.close()

    @pytest.mark.asyncio
    async def test_launch_unknown_app(self, simulator):
        ws = await connect_ws()
        await send_app_launch(ws, "unknown.app.id")
        state = get_tv_state()
        assert state["current_app"] is not None
        assert "unknown.app.id" in state["current_app"] or "App(" in state["current_app"]
        await ws.close()


class TestHTTPStatusAPI:
    def test_status_endpoint_returns_json(self, simulator):
        state = get_tv_state()
        assert "power" in state
        assert "volume" in state
        assert "mute" in state
        assert "channel" in state
        assert "current_app" in state

    def test_log_endpoint(self, simulator):
        with urllib.request.urlopen(f"{HTTP_URL}/log", timeout=3) as r:
            log = json.loads(r.read())
        assert isinstance(log, list)

    def test_html_status_page(self, simulator):
        with urllib.request.urlopen(f"{HTTP_URL}/", timeout=3) as r:
            html = r.read().decode()
        assert "Samsung TV Simulator" in html
        assert "Volume" in html


# ── Standalone runner (no pytest) ─────────────────────────────────────────────

async def run_standalone():
    """Quick smoke test without pytest — run directly with python3."""
    print("Samsung TV Simulator — Standalone Test Run")
    print("=" * 50)

    tests_passed = 0
    tests_failed = 0

    async def check(name: str, coro):
        nonlocal tests_passed, tests_failed
        try:
            await coro
            print(f"  ✓  {name}")
            tests_passed += 1
        except Exception as e:
            print(f"  ✗  {name}: {e}")
            tests_failed += 1

    ws = await connect_ws()
    print(f"  ✓  WebSocket connected, pairing token received")
    tests_passed += 1

    # Volume tests
    before_vol = get_tv_state()["volume"]
    await send_key(ws, "KEY_VOLUMEUP")
    await check("Volume up increments", asyncio.coroutine(lambda: None)() if get_tv_state()["volume"] == before_vol + 1 else (_ for _ in ()).throw(AssertionError(f"Expected {before_vol+1}")))

    await send_key(ws, "KEY_MUTE")
    await check("Mute toggles", asyncio.coroutine(lambda: None)() if get_tv_state()["mute"] else (_ for _ in ()).throw(AssertionError("Mute should be ON")))
    await send_key(ws, "KEY_MUTE")

    # App launch
    await send_app_launch(ws, "11101200001")
    state = get_tv_state()
    if state["current_app"] == "Netflix":
        print("  ✓  Netflix launched")
        tests_passed += 1
    else:
        print(f"  ✗  Netflix launch: expected 'Netflix', got '{state['current_app']}'")
        tests_failed += 1

    # Home clears app
    await send_key(ws, "KEY_HOME")
    state = get_tv_state()
    if state["current_app"] is None:
        print("  ✓  Home clears current app")
        tests_passed += 1
    else:
        print(f"  ✗  Home should clear app, got '{state['current_app']}'")
        tests_failed += 1

    await ws.close()

    print()
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


if __name__ == "__main__":
    import sys
    ok = asyncio.run(run_standalone())
    sys.exit(0 if ok else 1)
