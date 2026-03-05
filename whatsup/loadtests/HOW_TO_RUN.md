# WhatsUp Load-Test Harness — How to Run

## Prerequisites

```bash
pip install aiohttp psutil
```

The **whatsup-server** must be running before starting the harness.

## Starting the server

```bash
cd /path/to/whatsup

# 1. Copy and fill in the environment file
cp .env.example .env
#    Set JWT_SECRET and TOTP_ENCRYPTION_KEY to 64-hex-char random values:
#    openssl rand -hex 32

# 2. Build (release recommended for realistic perf numbers)
cargo build --release -p whatsup-server

# 3. Start
export $(cat .env | xargs)
./target/release/whatsup-server
```

The server binds to `http://127.0.0.1:3000` by default.
Check liveness: `curl http://127.0.0.1:3000/health`

## Running the harness

```bash
cd /path/to/whatsup

python3 harness.py \
  --max-users  100 \
  --base-url   http://127.0.0.1:3000 \
  --log-file   loadtests/run_100u.log \
  --duration   300
```

| Flag | Default | Description |
|------|---------|-------------|
| `--max-users` | 100 | Total users to create; groups = max_users // 10 |
| `--base-url` | `http://127.0.0.1:3000` | Server URL |
| `--log-file` | `harness.log` | Output log (line-buffered, appended) |
| `--duration` | 0 (unlimited) | Seconds to run; 0 = until Ctrl+C |

## Metric format (every 10 seconds)

```
METRICS ts=<ISO8601>
        total_users=<N>  active_ws=<N>  ws_errors=<N>
        msgs_sent=<N>  msgs_recv=<N>  msgs_fail=<N>
        delta_sent=<N>  delta_recv=<N>  delta_fail=<N>
        proc_mem_mb=<F>  proc_cpu=<F>
        sys_mem_pct=<F>  sys_cpu_pct=<F>
```

- **delta_*** = increment since the last 10-second snapshot
- **active_ws** = currently open WebSocket connections
- **msgs_recv** = `NewMessage` events delivered over WS to connected users

## Log files

Log files are stored in `loadtests/` with the naming pattern `run_<N>u.log`.
Summary markdown files follow the pattern `run_<N>u_summary.md`.

## Notes on throughput limits

- **Argon2id** (m=64 MiB, t=3) is used for every register + login.
  Registration is limited to 3 concurrent calls; expect 5–15 s per user on busy hardware.
- **SQLite** with a global write lock serialises all message inserts.
  Latency rises steeply beyond ~50 concurrent message senders.
- **WS tickets** expire after 60 s; the harness issues and uses them in a single shot.
- **JWT access tokens** expire after 900 s; the harness refreshes at 720 s.
