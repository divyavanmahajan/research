#!/usr/bin/env python3
"""
WhatsUp Load-Testing Harness
============================

Creates up to --max-users simulated users and max_users//10 groups, then
ramps up concurrent WebSocket connections and REST message sends, measuring
server performance every 10 seconds and increasing load every 30 seconds.

Usage
-----
    python harness.py [--max-users N] [--base-url URL] [--log-file PATH]
                      [--duration SECONDS] [--setup-first]

Setup metrics
-------------
When --setup-first is given (or always logged), each setup phase emits a
SETUP_METRICS log line in the following format:

    SETUP_METRICS phase=<register|login>  total=N  ok=N  fail=N \
        elapsed_s=F  rate_per_s=F  concurrency=N

A final SETUP_SUMMARY line is emitted once all users are ready.

Requirements
------------
    pip install aiohttp psutil

Notes on the server
-------------------
* POST /api/v1/auth/register  → {"user_id": ...}   (HTTP 201, or 409 if duplicate)
* POST /api/v1/auth/login     → {"access_token":..., "refresh_token":..., "expires_in":900}
  - login does NOT return user_id; call GET /users/me afterwards
* POST /api/v1/auth/ws-ticket → {"ticket": ...}  (60-second single-use ticket)
* GET  /ws?ticket=...         → WebSocket (server pushes NewMessage events here)
* POST /messages/send         → actually persists and fans out messages (ciphertext must be valid base64)
* POST /groups                → {"group_id": ...}  (HTTP 201)
* Argon2id (m=64 MiB, t=3, p=4) is used for every register AND login - inherently slow
* SQLite with Arc<Mutex<Connection>> serialises ALL DB writes (one writer at a time)
* JWT access tokens expire in 900 s (15 min); refresh before that with POST /api/v1/auth/refresh

Known failure modes
-------------------
1.  Argon2id throughput cap: register + login are CPU-heavy and serialised through
    the SQLite mutex, so concurrency beyond a few simultaneous auth calls causes
    timeouts.  The harness uses a low semaphore (REGISTER_CONCURRENCY=3).
2.  SQLite global write lock: all message inserts are serialised. Under heavy load
    every POST /messages/send queues behind the mutex.  Expect latency spikes.
3.  WS ticket 60 s TTL: if we do not connect within 60 s after issuing a ticket
    the server rejects it with HTTP 401.  The harness connects immediately.
4.  JWT expiry at 900 s: the harness refreshes tokens at 720 s (12 min) to leave
    a 3-minute safety margin.  A failed refresh causes the user task to exit.
5.  WS SendMessage is a stub: the server WS handler discards SendMessage events
    (let _ = req).  We send messages via REST POST /messages/send instead.
6.  Ciphertext must be valid base64: the server calls base64::decode() before
    doing anything else, returning HTTP 400 on failure.  The harness encodes
    random bytes to base64 before sending.
7.  OPK pool: the server does not require OPKs for the harness message flow (we
    skip the X3DH handshake and send dummy ciphertext), so OPKs are not consumed.
8.  File descriptor limits: each WS connection is a socket.  ulimit -n may need
    raising for large --max-users values.
9.  Receive-side counters: the harness counts NewMessage events received over WS.
    If a user is not connected when a message arrives the server delivers it
    over WS only to currently connected recipients; the counter will undercount.
10. Token refresh race: if two tasks for the same account both detect token_age > 720
    they will both try to refresh, and the second refresh will fail because the
    family rotation deletes the first token.  Guarded by per-account asyncio.Lock.
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

try:
    import aiohttp
except ImportError:
    sys.exit("aiohttp is required: pip install aiohttp")

try:
    import psutil
except ImportError:
    sys.exit("psutil is required: pip install psutil")

# ── Tuneable constants ─────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://127.0.0.1:3000"
DEFAULT_MAX_USERS = 100
DEFAULT_LOG_FILE = "harness.log"

MEASURE_INTERVAL = 10       # seconds between metric snapshots
RAMP_INTERVAL    = 30       # seconds between concurrency increases
RAMP_STEP_PCT    = 0.10     # fraction of max_users added per ramp step
INITIAL_PCT      = 0.10     # fraction of max_users active at start

# Inter-message delay per user (seconds, chosen uniformly at random)
MSG_INTERVAL_MIN = 0.5
MSG_INTERVAL_MAX = 2.0

# HTTP timeout constants (seconds)
REGISTER_TIMEOUT  = 90      # Argon2id hashing can be slow
LOGIN_TIMEOUT     = 90
ME_TIMEOUT        = 10
WS_TICKET_TIMEOUT = 10
SEND_MSG_TIMEOUT  = 15
CREATE_GRP_TIMEOUT = 15

# Refresh access token when it is this many seconds old
TOKEN_REFRESH_AT  = 720     # 900 s expiry; refresh at 12 min

# System resource thresholds that stop ramping (but keep running existing load)
MAX_SYS_MEM_PCT = 90.0
MAX_SYS_CPU_PCT = 95.0

# Shared password for all harness accounts
PASSWORD = "HarnessTest@1!"

# Concurrency limits for the setup phase (Argon2id is expensive).
# --setup-first mode uses higher concurrency since the simulation is not
# competing for server resources yet.
REGISTER_CONCURRENCY        = 3
LOGIN_CONCURRENCY           = 5
SETUP_FIRST_REGISTER_CONCURRENCY = 10
SETUP_FIRST_LOGIN_CONCURRENCY    = 20

# Max base64-encoded ciphertext size (must be <= 64 KB decoded, i.e. 48 KB raw)
FAKE_MSG_BYTES = 64         # raw random bytes → ~88 base64 chars

# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class UserAccount:
    username: str
    user_id: str
    access_token: str
    refresh_token: str
    token_obtained_at: float = field(default_factory=time.monotonic)
    refresh_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@dataclass
class GroupRecord:
    group_id: str
    name: str
    member_ids: list


# ── Shared counters (accessed only from the asyncio event loop – no locking) ──

class Counters:
    __slots__ = (
        "msgs_sent", "msgs_received", "msgs_failed",
        "ws_active", "ws_connect_errors", "setup_errors",
    )

    def __init__(self):
        self.msgs_sent         = 0
        self.msgs_received     = 0
        self.msgs_failed       = 0
        self.ws_active         = 0
        self.ws_connect_errors = 0
        self.setup_errors      = 0


# ── Logging ────────────────────────────────────────────────────────────────────

def setup_logging(log_file: str) -> logging.Logger:
    logger = logging.getLogger("harness")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    # line_buffering=True flushes after every log record – avoids losing data
    # if the process is killed.  (Python 3.7+ FileHandler uses buffered I/O
    # by default; reconfigure() switches to line-buffered mode.)
    try:
        fh.stream.reconfigure(line_buffering=True)
    except AttributeError:
        # Older Python or TextIOWrapper without reconfigure – fall back to
        # setting the write-through flag explicitly.
        import io
        fh.stream = io.TextIOWrapper(
            fh.stream.buffer, encoding="utf-8", line_buffering=True
        )
    logger.addHandler(fh)
    return logger


# ── Helper: valid base64 dummy ciphertext ─────────────────────────────────────

def make_fake_ciphertext() -> str:
    """Return a base64-encoded string of random bytes.

    The server calls base64::decode() before touching the ciphertext, so we
    must supply proper base64.  The size is well within the 64 KB limit.
    """
    return base64.b64encode(os.urandom(FAKE_MSG_BYTES)).decode()


# ── HTTP helpers ───────────────────────────────────────────────────────────────

async def register_user(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str,
    logger: logging.Logger,
) -> Optional[str]:
    """POST /api/v1/auth/register → user_id or None."""
    url = f"{base_url}/api/v1/auth/register"
    payload = {
        "username": username,
        "password": PASSWORD,
        "display_name": username,
    }
    try:
        async with session.post(
            url, json=payload,
            timeout=aiohttp.ClientTimeout(total=REGISTER_TIMEOUT),
        ) as resp:
            if resp.status == 201:
                data = await resp.json()
                return data.get("user_id")
            if resp.status == 409:
                # Username already taken (previous run) – ok, we will login
                return "ALREADY_EXISTS"
            body = await resp.text()
            logger.warning("register %s → HTTP %d: %.200s", username, resp.status, body)
            return None
    except asyncio.TimeoutError:
        logger.warning("register %s timed out", username)
        return None
    except aiohttp.ClientError as exc:
        logger.warning("register %s client error: %s", username, exc)
        return None


async def login_user(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str,
    logger: logging.Logger,
) -> Optional[tuple]:
    """POST /api/v1/auth/login → (access_token, refresh_token) or None."""
    url = f"{base_url}/api/v1/auth/login"
    try:
        async with session.post(
            url,
            json={"username": username, "password": PASSWORD},
            timeout=aiohttp.ClientTimeout(total=LOGIN_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                at = data.get("access_token")
                rt = data.get("refresh_token")
                if at and rt:
                    return at, rt
            body = await resp.text()
            logger.warning("login %s → HTTP %d: %.200s", username, resp.status, body)
            return None
    except asyncio.TimeoutError:
        logger.warning("login %s timed out", username)
        return None
    except aiohttp.ClientError as exc:
        logger.warning("login %s client error: %s", username, exc)
        return None


async def get_my_user_id(
    session: aiohttp.ClientSession,
    base_url: str,
    access_token: str,
    logger: logging.Logger,
) -> Optional[str]:
    """GET /users/me → user_id or None."""
    url = f"{base_url}/users/me"
    try:
        async with session.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=aiohttp.ClientTimeout(total=ME_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("id")
            body = await resp.text()
            logger.warning("GET /users/me → HTTP %d: %.200s", resp.status, body)
            return None
    except asyncio.TimeoutError:
        logger.warning("GET /users/me timed out")
        return None
    except aiohttp.ClientError as exc:
        logger.warning("GET /users/me client error: %s", exc)
        return None


async def do_token_refresh(
    session: aiohttp.ClientSession,
    base_url: str,
    account: UserAccount,
    logger: logging.Logger,
) -> bool:
    """POST /api/v1/auth/refresh.  Updates account in-place. Returns True on success.

    Uses account.refresh_lock so only one concurrent refresh fires per account
    (see failure mode #10 in the module docstring).
    """
    async with account.refresh_lock:
        # Re-check age after acquiring the lock – another task may have already
        # refreshed the token while we were waiting.
        if time.monotonic() - account.token_obtained_at < TOKEN_REFRESH_AT:
            return True

        url = f"{base_url}/api/v1/auth/refresh"
        try:
            async with session.post(
                url,
                json={"refresh_token": account.refresh_token},
                timeout=aiohttp.ClientTimeout(total=LOGIN_TIMEOUT),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    account.access_token  = data["access_token"]
                    account.refresh_token = data["refresh_token"]
                    account.token_obtained_at = time.monotonic()
                    logger.debug("Refreshed token for %s", account.username)
                    return True
                body = await resp.text()
                logger.warning(
                    "token refresh for %s → HTTP %d: %.200s",
                    account.username, resp.status, body,
                )
                return False
        except Exception as exc:
            logger.warning("token refresh for %s failed: %s", account.username, exc)
            return False


async def get_ws_ticket(
    session: aiohttp.ClientSession,
    base_url: str,
    access_token: str,
    logger: logging.Logger,
) -> Optional[str]:
    """POST /api/v1/auth/ws-ticket → ticket UUID or None."""
    url = f"{base_url}/api/v1/auth/ws-ticket"
    try:
        async with session.post(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=aiohttp.ClientTimeout(total=WS_TICKET_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("ticket")
            body = await resp.text()
            logger.warning("ws-ticket → HTTP %d: %.200s", resp.status, body)
            return None
    except Exception as exc:
        logger.warning("ws-ticket failed: %s", exc)
        return None


async def rest_send_message(
    session: aiohttp.ClientSession,
    base_url: str,
    account: UserAccount,
    kind: str,          # "direct" or "group"
    to: str,            # recipient user_id or group_id
    counters: Counters,
    logger: logging.Logger,
) -> None:
    """POST /messages/send.  Updates counters in-place."""
    url = f"{base_url}/messages/send"
    msg_id = str(uuid.uuid4())
    payload = {
        "message_id": msg_id,
        "kind": kind,
        "to": to,
        "ciphertext": make_fake_ciphertext(),
        "message_type": "text",
        "file_id": None,
    }
    headers = {"Authorization": f"Bearer {account.access_token}"}
    try:
        async with session.post(
            url, json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=SEND_MSG_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                counters.msgs_sent += 1
            else:
                counters.msgs_failed += 1
                body = await resp.text()
                logger.debug(
                    "send_message %s → HTTP %d: %.200s",
                    account.username, resp.status, body,
                )
    except asyncio.TimeoutError:
        counters.msgs_failed += 1
        logger.debug("send_message %s timed out", account.username)
    except aiohttp.ClientError as exc:
        counters.msgs_failed += 1
        logger.debug("send_message %s client error: %s", account.username, exc)


async def create_group(
    session: aiohttp.ClientSession,
    base_url: str,
    creator: UserAccount,
    name: str,
    member_ids: list,
    logger: logging.Logger,
) -> Optional[str]:
    """POST /groups → group_id or None."""
    url = f"{base_url}/groups"
    headers = {"Authorization": f"Bearer {creator.access_token}"}
    payload = {"name": name, "member_ids": member_ids}
    try:
        async with session.post(
            url, json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=CREATE_GRP_TIMEOUT),
        ) as resp:
            if resp.status == 201:
                data = await resp.json()
                return data.get("group_id")
            body = await resp.text()
            logger.warning("create_group %s → HTTP %d: %.200s", name, resp.status, body)
            return None
    except Exception as exc:
        logger.warning("create_group %s failed: %s", name, exc)
        return None


# ── WebSocket user simulation ──────────────────────────────────────────────────

async def simulate_user(
    account: UserAccount,
    base_url: str,
    all_accounts: list,
    groups: list,
    counters: Counters,
    stop_event: asyncio.Event,
    logger: logging.Logger,
) -> None:
    """Maintain a WS connection (for receiving) and send messages via REST.

    Reconnects automatically if the WS drops.  Refreshes the JWT when it
    approaches expiry.
    """
    ws_base = (
        base_url.replace("http://", "ws://").replace("https://", "wss://")
    )

    while not stop_event.is_set():
        # ── Token refresh if approaching expiry ──────────────────────────────
        if time.monotonic() - account.token_obtained_at >= TOKEN_REFRESH_AT:
            async with aiohttp.ClientSession() as sess:
                ok = await do_token_refresh(sess, base_url, account, logger)
            if not ok:
                logger.error(
                    "Cannot refresh token for %s; user task stopping",
                    account.username,
                )
                return

        # ── Obtain a WS ticket immediately before connecting ─────────────────
        # The ticket has a 60-second TTL, so we issue it and connect in one shot.
        async with aiohttp.ClientSession() as sess:
            ticket = await get_ws_ticket(
                sess, base_url, account.access_token, logger
            )
        if not ticket:
            counters.ws_connect_errors += 1
            logger.warning(
                "No WS ticket for %s; retrying in 5 s", account.username
            )
            await asyncio.sleep(5)
            continue

        ws_url = f"{ws_base}/ws?ticket={ticket}"

        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.ws_connect(
                    ws_url,
                    # aiohttp sends WS pings automatically when heartbeat is set;
                    # the server's Axum auto-responds to WS pings.
                    heartbeat=20,
                    timeout=aiohttp.ClientTimeout(total=None, connect=10),
                ) as ws:
                    counters.ws_active += 1
                    logger.debug(
                        "WS up: %s  (active=%d)",
                        account.username, counters.ws_active,
                    )
                    try:
                        await _run_ws_session(
                            ws, sess, account, base_url,
                            all_accounts, groups,
                            counters, stop_event, logger,
                        )
                    finally:
                        counters.ws_active -= 1
                        logger.debug(
                            "WS down: %s  (active=%d)",
                            account.username, counters.ws_active,
                        )

        except aiohttp.WSServerHandshakeError as exc:
            counters.ws_connect_errors += 1
            logger.warning(
                "WS handshake error for %s (status=%s): %s",
                account.username, exc.status, exc,
            )
        except aiohttp.ClientConnectorError as exc:
            counters.ws_connect_errors += 1
            logger.warning(
                "WS connect error for %s: %s", account.username, exc
            )
        except Exception as exc:
            counters.ws_connect_errors += 1
            logger.warning(
                "Unexpected WS error for %s: %s", account.username, exc
            )

        if not stop_event.is_set():
            # Brief pause before reconnect to avoid hammering the server
            await asyncio.sleep(3)


async def _run_ws_session(
    ws: aiohttp.ClientWebSocketResponse,
    sess: aiohttp.ClientSession,
    account: UserAccount,
    base_url: str,
    all_accounts: list,
    groups: list,
    counters: Counters,
    stop_event: asyncio.Event,
    logger: logging.Logger,
) -> None:
    """Concurrent send and receive loops for one WebSocket lifetime."""
    send_task = asyncio.create_task(
        _send_loop(
            sess, account, base_url, all_accounts, groups,
            counters, stop_event, logger,
        ),
        name=f"send-{account.username}",
    )
    recv_task = asyncio.create_task(
        _recv_loop(ws, counters, stop_event, logger),
        name=f"recv-{account.username}",
    )

    done, pending = await asyncio.wait(
        [send_task, recv_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for t in pending:
        t.cancel()
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass


async def _send_loop(
    sess: aiohttp.ClientSession,
    account: UserAccount,
    base_url: str,
    all_accounts: list,
    groups: list,
    counters: Counters,
    stop_event: asyncio.Event,
    logger: logging.Logger,
) -> None:
    """Periodically send messages via REST POST /messages/send."""
    while not stop_event.is_set():
        delay = random.uniform(MSG_INTERVAL_MIN, MSG_INTERVAL_MAX)
        await asyncio.sleep(delay)
        if stop_event.is_set():
            break

        # Refresh token if needed (inline here so send continues after refresh)
        if time.monotonic() - account.token_obtained_at >= TOKEN_REFRESH_AT:
            await do_token_refresh(sess, base_url, account, logger)

        # Pick direct or group target (50/50 when groups are available)
        use_group = bool(groups) and random.random() < 0.5
        
        if use_group:
            my_groups = [g for g in groups if account.user_id in g.member_ids]
            if my_groups:
                g = random.choice(my_groups)
                await rest_send_message(
                    sess, base_url, account, "group", g.group_id, counters, logger
                )
            else:
                use_group = False
                
        if not use_group:
            # Direct message to a random other user
            candidates = [
                a for a in all_accounts if a.user_id != account.user_id
            ]
            if not candidates:
                continue
            peer = random.choice(candidates)
            await rest_send_message(
                sess, base_url, account, "direct", peer.user_id,
                counters, logger,
            )


async def _recv_loop(
    ws: aiohttp.ClientWebSocketResponse,
    counters: Counters,
    stop_event: asyncio.Event,
    logger: logging.Logger,
) -> None:
    """Count NewMessage events pushed by the server over WebSocket."""
    async for msg in ws:
        if stop_event.is_set():
            break
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                evt = json.loads(msg.data)
                evt_type = evt.get("type", "")
                if evt_type == "NewMessage":
                    counters.msgs_received += 1
                elif evt_type == "Error":
                    err_payload = evt.get("payload", {})
                    logger.debug("Server WS Error: %s", err_payload)
            except (json.JSONDecodeError, TypeError):
                pass
        elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
            logger.debug("WS closed/error: %s", msg)
            break


# ── Metrics loop ───────────────────────────────────────────────────────────────

async def metrics_loop(
    accounts: list,
    counters: Counters,
    stop_event: asyncio.Event,
    logger: logging.Logger,
) -> None:
    """Log a metrics snapshot every MEASURE_INTERVAL seconds."""
    proc = psutil.Process(os.getpid())

    prev_sent   = 0
    prev_recv   = 0
    prev_failed = 0

    while not stop_event.is_set():
        await asyncio.sleep(MEASURE_INTERVAL)
        if stop_event.is_set():
            break

        sent_delta   = counters.msgs_sent   - prev_sent
        recv_delta   = counters.msgs_received - prev_recv
        fail_delta   = counters.msgs_failed - prev_failed
        prev_sent    = counters.msgs_sent
        prev_recv    = counters.msgs_received
        prev_failed  = counters.msgs_failed

        try:
            proc_mem_mb = proc.memory_info().rss / (1024 * 1024)
            # cpu_percent(interval=None) is non-blocking; the first call
            # returns 0.0 (reference point).  Subsequent calls give the
            # percentage since the previous call.
            proc_cpu    = proc.cpu_percent(interval=None)
        except psutil.NoSuchProcess:
            proc_mem_mb = 0.0
            proc_cpu    = 0.0

        sys_mem = psutil.virtual_memory()
        sys_cpu = psutil.cpu_percent(interval=None)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info(
            "METRICS ts=%s "
            "total_users=%d active_ws=%d ws_errors=%d "
            "msgs_sent=%d msgs_recv=%d msgs_fail=%d "
            "delta_sent=%d delta_recv=%d delta_fail=%d "
            "proc_mem_mb=%.1f proc_cpu=%.1f "
            "sys_mem_pct=%.1f sys_cpu_pct=%.1f",
            ts,
            len(accounts), counters.ws_active, counters.ws_connect_errors,
            counters.msgs_sent, counters.msgs_received, counters.msgs_failed,
            sent_delta, recv_delta, fail_delta,
            proc_mem_mb, proc_cpu,
            sys_mem.percent, sys_cpu,
        )


# ── Resource guard ─────────────────────────────────────────────────────────────

def resources_ok(logger: logging.Logger) -> bool:
    """Return False if system memory or CPU exceeds the stop threshold."""
    sys_mem = psutil.virtual_memory()
    sys_cpu = psutil.cpu_percent(interval=1)
    if sys_mem.percent >= MAX_SYS_MEM_PCT:
        logger.warning(
            "System memory %.1f%% ≥ %.1f%% threshold; stopping ramp",
            sys_mem.percent, MAX_SYS_MEM_PCT,
        )
        return False
    if sys_cpu >= MAX_SYS_CPU_PCT:
        logger.warning(
            "System CPU %.1f%% ≥ %.1f%% threshold; stopping ramp",
            sys_cpu, MAX_SYS_CPU_PCT,
        )
        return False
    return True


# ── Ramp controller ────────────────────────────────────────────────────────────

async def ramp_controller(
    accounts: list,
    groups: list,
    base_url: str,
    max_users: int,
    counters: Counters,
    stop_event: asyncio.Event,
    logger: logging.Logger,
) -> None:
    """Start with INITIAL_PCT of accounts active; add RAMP_STEP_PCT every 30 s."""
    active_tasks: dict[str, asyncio.Task] = {}

    def start_user(acc: UserAccount) -> None:
        if acc.user_id not in active_tasks:
            t = asyncio.create_task(
                simulate_user(
                    acc, base_url, accounts, groups,
                    counters, stop_event, logger,
                ),
                name=f"user-{acc.username}",
            )
            active_tasks[acc.user_id] = t

    # Initial batch
    initial_n = max(1, int(max_users * INITIAL_PCT))
    for acc in accounts[:initial_n]:
        start_user(acc)
    logger.info("Ramp: initial batch of %d users started", initial_n)

    ramp_index   = initial_n
    next_ramp_at = time.monotonic() + RAMP_INTERVAL

    while not stop_event.is_set():
        await asyncio.sleep(1)

        # Prune completed (crashed) tasks so we don't keep stale references
        finished = [uid for uid, t in active_tasks.items() if t.done()]
        for uid in finished:
            del active_tasks[uid]

        if time.monotonic() < next_ramp_at:
            continue

        next_ramp_at = time.monotonic() + RAMP_INTERVAL

        if ramp_index >= len(accounts):
            logger.info(
                "Ramp: all %d accounts are active; holding steady",
                len(accounts),
            )
            continue

        if not resources_ok(logger):
            logger.warning(
                "Ramp: resource threshold hit with %d active tasks; "
                "stopping ramp (keeping existing tasks running)",
                len(active_tasks),
            )
            continue

        step = max(1, int(max_users * RAMP_STEP_PCT))
        batch = accounts[ramp_index : ramp_index + step]
        for acc in batch:
            start_user(acc)
        ramp_index += step
        logger.info(
            "Ramp: +%d users → ramp_index=%d / %d  active_tasks=%d",
            len(batch), ramp_index, len(accounts), len(active_tasks),
        )

    # Stop requested – cancel all user tasks
    logger.info("Stop event set; cancelling %d user tasks", len(active_tasks))
    for t in active_tasks.values():
        t.cancel()
    if active_tasks:
        await asyncio.gather(*active_tasks.values(), return_exceptions=True)


# ── Setup: users ───────────────────────────────────────────────────────────────

async def setup_users(
    base_url: str,
    max_users: int,
    logger: logging.Logger,
    setup_first: bool = False,
) -> list:
    """Register (or detect existing) and log in all max_users accounts.

    Returns a list of UserAccount objects ready for simulation.

    When *setup_first* is True the function uses higher concurrency and
    completes all registration + logins before returning, ensuring the
    simulation phase only starts once every account is ready.  In both
    modes a SETUP_METRICS log line is emitted for each phase, plus a
    SETUP_SUMMARY at the end.

    Failure modes handled:
    * Argon2id is slow → concurrency semaphore limits parallelism
    * Username already exists (409) → skip register, proceed to login
    * Login does not return user_id → call GET /users/me
    """
    reg_concurrency   = SETUP_FIRST_REGISTER_CONCURRENCY if setup_first else REGISTER_CONCURRENCY
    login_concurrency = SETUP_FIRST_LOGIN_CONCURRENCY    if setup_first else LOGIN_CONCURRENCY

    mode_label = "setup-first" if setup_first else "interleaved"
    logger.info(
        "Setting up %d users (mode=%s, Argon2id – may be slow)…",
        max_users, mode_label,
    )
    usernames = [f"harness_u{i:05d}" for i in range(max_users)]

    # ── Registration ──────────────────────────────────────────────────────────
    reg_sem  = asyncio.Semaphore(reg_concurrency)
    reg_ok   = 0
    reg_fail = 0
    reg_lock = asyncio.Lock()
    reg_t0   = time.monotonic()

    async def register_one(sess: aiohttp.ClientSession, username: str) -> None:
        nonlocal reg_ok, reg_fail
        async with reg_sem:
            result = await register_user(sess, base_url, username, logger)
            async with reg_lock:
                if result is not None:
                    reg_ok += 1
                else:
                    reg_fail += 1
                    logger.warning("register %s failed; will try login anyway", username)

    async with aiohttp.ClientSession() as sess:
        await asyncio.gather(*[register_one(sess, u) for u in usernames])

    reg_elapsed = time.monotonic() - reg_t0
    reg_rate    = reg_ok / reg_elapsed if reg_elapsed > 0 else 0.0
    logger.info(
        "SETUP_METRICS phase=register  total=%d  ok=%d  fail=%d  "
        "elapsed_s=%.1f  rate_per_s=%.2f  concurrency=%d",
        max_users, reg_ok, reg_fail, reg_elapsed, reg_rate, reg_concurrency,
    )

    # ── Login ─────────────────────────────────────────────────────────────────
    logger.info("Logging in %d users…", max_users)
    login_sem  = asyncio.Semaphore(login_concurrency)
    accounts: list[UserAccount] = []
    login_fail = 0
    login_lock = asyncio.Lock()
    login_t0   = time.monotonic()

    async def login_one(sess: aiohttp.ClientSession, username: str) -> Optional[UserAccount]:
        async with login_sem:
            tokens = await login_user(sess, base_url, username, logger)
            if tokens is None:
                return None
            at, rt = tokens
            uid = await get_my_user_id(sess, base_url, at, logger)
            if uid is None:
                logger.warning(
                    "Could not resolve user_id for %s; skipping", username
                )
                return None
            return UserAccount(
                username=username,
                user_id=uid,
                access_token=at,
                refresh_token=rt,
            )

    async with aiohttp.ClientSession() as sess:
        results = await asyncio.gather(
            *[login_one(sess, u) for u in usernames]
        )

    for r in results:
        if r is not None:
            accounts.append(r)
        else:
            login_fail += 1

    login_elapsed = time.monotonic() - login_t0
    login_rate    = len(accounts) / login_elapsed if login_elapsed > 0 else 0.0
    logger.info(
        "SETUP_METRICS phase=login  total=%d  ok=%d  fail=%d  "
        "elapsed_s=%.1f  rate_per_s=%.2f  concurrency=%d",
        max_users, len(accounts), login_fail, login_elapsed, login_rate, login_concurrency,
    )

    total_elapsed = time.monotonic() - reg_t0
    logger.info(
        "SETUP_SUMMARY users_ready=%d  users_failed=%d  "
        "total_elapsed_s=%.1f  reg_rate_per_s=%.2f  login_rate_per_s=%.2f",
        len(accounts), reg_fail + login_fail,
        total_elapsed, reg_rate, login_rate,
    )
    logger.info(
        "User setup complete: %d ready, %d failed",
        len(accounts), reg_fail + login_fail,
    )
    return accounts


# ── Setup: groups ──────────────────────────────────────────────────────────────

async def setup_groups(
    base_url: str,
    accounts: list,
    max_users: int,
    logger: logging.Logger,
) -> list:
    """Create max_users // 10 groups (at least 1).

    Each group gets ~10 random members.  The first account is the creator
    (and becomes admin) for all groups.
    """
    if len(accounts) < 2:
        logger.warning("Too few accounts to create groups")
        return []

    num_groups = max(1, max_users // 10)
    logger.info("Creating %d groups…", num_groups)

    creator = accounts[0]
    other_ids = [a.user_id for a in accounts if a.user_id != creator.user_id]
    groups: list[GroupRecord] = []

    async with aiohttp.ClientSession() as sess:
        for i in range(num_groups):
            sample_size = min(9, len(other_ids))
            members = random.sample(other_ids, sample_size) if sample_size else []
            name = f"harness_grp_{i:04d}"
            gid = await create_group(
                sess, base_url, creator, name, members, logger
            )
            if gid:
                groups.append(
                    GroupRecord(
                        group_id=gid,
                        name=name,
                        member_ids=[creator.user_id] + members,
                    )
                )
            else:
                logger.warning("Failed to create group %s", name)

    logger.info("Group setup: %d / %d created", len(groups), num_groups)
    return groups


# ── Duration timer ─────────────────────────────────────────────────────────────

async def duration_timer(
    duration_secs: int,
    stop_event: asyncio.Event,
    logger: logging.Logger,
) -> None:
    if duration_secs > 0:
        await asyncio.sleep(duration_secs)
        logger.info("Duration limit (%d s) reached; signalling stop", duration_secs)
        stop_event.set()
    else:
        # Run forever until stop_event is set externally (e.g. Ctrl+C)
        await stop_event.wait()


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="WhatsUp load-testing harness",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--max-users", type=int, default=DEFAULT_MAX_USERS,
        help="Maximum number of simulated users",
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL,
        help="Server base URL",
    )
    parser.add_argument(
        "--log-file", default=DEFAULT_LOG_FILE,
        help="Log file path (appended, line-buffered)",
    )
    parser.add_argument(
        "--duration", type=int, default=0,
        help="Run for this many seconds then stop (0 = run until Ctrl+C)",
    )
    parser.add_argument(
        "--setup-first", action="store_true", default=False,
        help=(
            "Complete registration + login for ALL users before starting "
            "the simulation (uses higher concurrency during setup). "
            "Emits SETUP_METRICS lines for register and login phases."
        ),
    )
    args = parser.parse_args()

    if args.max_users < 10:
        print("ERROR: --max-users must be >= 10", file=sys.stderr)
        sys.exit(1)

    logger = setup_logging(args.log_file)

    logger.info("=" * 60)
    logger.info("WhatsUp Testing Harness")
    logger.info(
        "max_users=%d  base_url=%s  log_file=%s  duration=%s  setup_first=%s",
        args.max_users, args.base_url, args.log_file,
        f"{args.duration}s" if args.duration else "unlimited",
        args.setup_first,
    )
    logger.info("=" * 60)

    stop_event = asyncio.Event()

    # ── Signal handlers ────────────────────────────────────────────────────────
    loop = asyncio.get_running_loop()
    try:
        import signal

        def _handle_signal():
            logger.info("Shutdown signal received; stopping…")
            stop_event.set()

        loop.add_signal_handler(signal.SIGINT,  _handle_signal)
        loop.add_signal_handler(signal.SIGTERM, _handle_signal)
    except (ImportError, NotImplementedError):
        pass  # Windows does not support add_signal_handler

    # ── Server liveness check ──────────────────────────────────────────────────
    logger.info("Checking server health at %s/health …", args.base_url)
    async with aiohttp.ClientSession() as sess:
        try:
            async with sess.get(
                f"{args.base_url}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                if r.status != 200:
                    logger.error(
                        "Health check returned HTTP %d – is the server running?",
                        r.status,
                    )
                    sys.exit(1)
                data = await r.json()
                logger.info("Server healthy: %s", data)
        except Exception as exc:
            logger.error(
                "Cannot reach server at %s: %s", args.base_url, exc
            )
            sys.exit(1)

    # ── User and group setup ───────────────────────────────────────────────────
    counters = Counters()

    accounts = await setup_users(args.base_url, args.max_users, logger, setup_first=args.setup_first)
    if not accounts:
        logger.error("No accounts available after setup; aborting")
        sys.exit(1)

    groups = await setup_groups(
        args.base_url, accounts, args.max_users, logger
    )

    logger.info(
        "Setup complete – %d users, %d groups.  Starting simulation…",
        len(accounts), len(groups),
    )
    logger.info("Press Ctrl+C to stop.")

    # ── Run ────────────────────────────────────────────────────────────────────
    await asyncio.gather(
        metrics_loop(accounts, counters, stop_event, logger),
        ramp_controller(
            accounts, groups, args.base_url, args.max_users,
            counters, stop_event, logger,
        ),
        duration_timer(args.duration, stop_event, logger),
    )

    # ── Final summary ──────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Harness finished.")
    logger.info(
        "Final totals: msgs_sent=%d  msgs_received=%d  msgs_failed=%d  "
        "ws_connect_errors=%d",
        counters.msgs_sent, counters.msgs_received,
        counters.msgs_failed, counters.ws_connect_errors,
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
