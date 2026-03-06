# WhatsUp Load-Test Results — Index

> See [HOW_TO_RUN.md](HOW_TO_RUN.md) for setup and usage instructions.

## Test Matrix

| Run | Engine | Max Users | Groups | Duration | Setup Time | WS Errors | Send OK | Send Fail | Success Rate | Peak CPU % | Peak Mem MB | Summary |
|-----|--------|-----------|--------|----------|------------|-----------|---------|-----------|--------------|------------|-------------|---------|
| 1 | Direct SQLite (mutex) | 100 | 10 | 300 s | ~21 s | — | 7 039 | 5 817 | 54.7 % | 18.8 | 48.3 | [run_100u_summary.md](run_100u_summary.md) |
| 2 | Direct SQLite (mutex) | 200 | 20 | 300 s | ~45 s | — | 13 674 | 11 995 | 53.3 % | 30.6 | 51.2 | [run_200u_summary.md](run_200u_summary.md) |
| 3 | Direct SQLite (mutex) | 300 | 30 | 300 s | ~70 s | — | 19 901 | 18 256 | 52.2 % | 42.5 | 57.1 | [run_300u_summary.md](run_300u_summary.md) |
| 4 | Direct SQLite (mutex) | 400 | 40 | 300 s | ~92 s | — | 25 931 | 24 604 | 51.3 % | 44.3 | 61.0 | [run_400u_summary.md](run_400u_summary.md) |
| 5 | Direct SQLite (mutex) | 500 | 50 | 300 s | ~113 s | — | 31 790 | 30 933 | 50.7 % | 58.0 | 66.4 | [run_500u_summary.md](run_500u_summary.md) |
| **6** | **Batched writer + r2d2 fix** | **500** | **50** | **300 s** | **~78 s** | **0** | **64 147** | **4** | **99.99 %** | **18.4** | **56.7** | [run_500u_v6 (inline)](#run-6-verification-500-users) |
| **7** | **Batched writer + r2d2 fix** | **1 000** | **100** | **300 s** | **~145 s** | **0** | **126 268** | **723** | **99.4 %** | **24.8** | **97.5** | [run_1000u_summary.md](run_1000u_summary.md) |

---

## Before vs After: Performance Fix Impact

| Metric | 500 u (old engine) | 500 u (new engine) | Change |
|--------|--------------------|--------------------|--------|
| WS connect errors | unknown | **0** | ✅ |
| Messages sent | 31 790 | 64 147 | **+102 %** |
| Success rate | 50.7 % | **99.99 %** | **+49 pp** |
| Peak server CPU | 58.0 % | 18.4 % | **−68 %** |
| Peak server RSS | 66.4 MB | 56.7 MB | −15 % |

The batched background writer (+ Argon2 spawn_blocking + r2d2 pool fix) more than doubled message throughput while cutting CPU by two thirds and eliminating ws-ticket failures entirely.

---

## Throughput Summary (new engine)

| Users | Peak delta_sent (msg/10 s) | Per-user rate | Success rate |
|-------|---------------------------|---------------|--------------|
| 500 | ~4 000 | ~8.0 msg/s | 99.99 % |
| 1 000 | ~7 918 | ~7.9 msg/s | 99.4 % |

Throughput scales **linearly** with user count — the server is not bottlenecked on connection count or fan-out.

---

## Key Findings (updated post-fix)

### 1. Background writer eliminates WS-ticket failures
The new `db/writer.rs` OS-thread writer batches all writes into 5 ms windows and
holds the SQLite write lock for as short a time as possible. ws-ticket requests
that previously starved (HTTP 500) now succeed reliably at 1 000 concurrent users.

### 2. r2d2 pool exhaustion was a hidden bottleneck
`send_message` held an r2d2 connection across the async `await` of the writer
channel. Under 500+ concurrent senders this exhausted the pool and caused
cascading timeouts. Scoping the connections to short read blocks fixed it.

### 3. Argon2 no longer blocks Tokio workers
Registration and login ran Argon2id on Tokio worker threads, starving async I/O.
Moving hash/verify into `spawn_blocking` freed workers and cut setup time by ~30 %.

### 4. Resources are not exhausted at 1 000 users
- Server RSS: **97.5 MB** at 1 000 connections (~0.10 MB / conn)
- Server CPU: **24.8 %** — well below saturation
- System memory: stable at **68 %** throughout

### 5. Remaining 0.6 % failure rate is ramp-burst artefact
The 723 failures at 1 000 users occur almost entirely during the 100-user ramp
bursts when write volume briefly spikes. `delta_fail` is 0 at steady state.
This is an inherent SQLite single-writer limitation; PostgreSQL would eliminate it.

### 6. Fan-out amplification
`msgs_recv` (306 077) is 2.4× `msgs_sent` (126 268) — consistent with 10-member
groups. The in-process `DashMap` WS hub handles fan-out with no measurable overhead.

---

## Run 6 Verification: 500 Users

| Metric | Value |
|--------|-------|
| Peak active_ws | 500 / 500 |
| WS connect errors | **0** |
| msgs_sent | 64 147 |
| msgs_received | 151 472 |
| msgs_failed | **4** |
| Success rate | **99.99 %** |
| Peak delta_sent | ~4 000 msg/10s |
| Peak server CPU | 18.4 % |
| Peak server RSS | 56.7 MB |

---

## Recommended Improvements (if scaling beyond 1 000 users)

| Area | Change |
|------|--------|
| Database | Migrate to PostgreSQL or use SQLite with multiple write shards to eliminate ramp-burst failures |
| Connection limits | Tune OS-level `ulimit -n` and Tokio worker count for > 1 000 concurrent sockets |
| Auth throughput | Use pre-created accounts in harness for test speed; keep Argon2 params for production |
| WS delivery | Current in-process `DashMap` hub is efficient; consider Redis pub/sub for multi-process deployments |

---

## How runs are organised

Each run produces two files in this folder:

| File | Contents |
|------|----------|
| `run_<N>u.log` | Raw harness output (all log levels, line-buffered) |
| `run_<N>u_summary.md` | Parsed metric table + observations |
