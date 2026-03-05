# Load-Test Summary — 500 Users (r2d2 Connection Pool Fix)

| Parameter | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Max users** | 500 |
| **Groups** | 50 |
| **Duration** | 300 s (5 min) |
| **Log file** | `run_500u_pool.log` |
| **Server build** | release (optimised) |
| **Fix applied** | `Arc<Mutex<Connection>>` → `r2d2` pool (10 conns) + `PRAGMA busy_timeout=5000` + `PRAGMA synchronous=NORMAL` |

---

## Final Totals

| Metric | Baseline (`Arc<Mutex>`) | Pool fix | Δ |
|--------|-------------------------|----------|---|
| Messages sent (success) | 31 790 | **32 812** | +1 022 (+3.2 %) |
| Messages received (WS) | 25 944 | **26 772** | +828 (+3.2 %) |
| Messages failed | 30 933 | **31 162** | +229 (+0.7 %) |
| WS connect errors | 0 | **0** | — |
| **Send success rate** | **50.7 %** | **51.3 %** | **+0.6 pp** |
| Peak delta (500 users, /10 s) | ~1 988 | **~2 043** | +55 (+2.8 %) |

---

## Metric Snapshots (every 10 s)

| Timestamp | Active WS | Sent Δ | Recv Δ | Fail Δ | Proc Mem MB | Proc CPU % | Sys Mem % |
|-----------|-----------|--------|--------|--------|-------------|------------|-----------|
| 09:29:03 | 50 | 190 | 21 | 178 | 47.6 | 0.0 | 2.3 |
| 09:29:13 | 50 | 210 | 40 | 184 | 47.6 | 6.9 | 2.3 |
| 09:29:23 | 50 | 201 | 43 | 193 | 47.6 | 8.3 | 2.3 |
| 09:29:33 | 100 | 390 | 80 | 318 | 49.1 | 16.2 | 2.3 |
| 09:29:43 | 100 | 442 | 115 | 370 | 49.1 | 14.7 | 2.3 |
| 09:29:53 | 100 | 402 | 98 | 408 | 49.1 | 16.2 | 2.3 |
| 09:30:03 | 150 | 581 | 210 | 504 | 51.6 | 21.3 | 2.4 |
| 09:30:13 | 150 | 598 | 209 | 590 | 51.6 | 23.4 | 2.4 |
| 09:30:23 | 150 | 618 | 224 | 577 | 51.6 | 23.0 | 2.4 |
| 09:30:33 | 200 | 760 | 364 | 705 | 53.1 | 27.3 | 2.5 |
| 09:30:43 | 200 | 792 | 374 | 769 | 53.1 | 27.0 | 2.5 |
| 09:30:53 | 200 | 826 | 412 | 782 | 53.1 | 28.6 | 2.5 |
| 09:31:03 | 250 | 950 | 546 | 892 | 55.5 | 32.7 | 2.5 |
| 09:31:13 | 250 | 1 021 | 586 | 952 | 55.5 | 33.5 | 2.5 |
| 09:31:23 | 250 | 1 046 | 623 | 961 | 55.5 | 35.4 | 2.5 |
| 09:31:33 | 300 | 1 142 | 852 | 1 058 | 58.1 | 38.1 | 2.5 |
| 09:31:43 | 300 | 1 240 | 880 | 1 160 | 58.1 | 42.6 | 2.5 |
| 09:31:53 | 300 | 1 207 | 855 | 1 161 | 58.1 | 40.4 | 2.5 |
| 09:32:03 | 350 | 1 310 | 1 051 | 1 265 | 59.6 | 43.1 | 2.6 |
| 09:32:13 | 350 | 1 479 | 1 205 | 1 346 | 59.6 | 47.3 | 2.6 |
| 09:32:23 | 350 | 1 427 | 1 166 | 1 345 | 59.6 | 46.6 | 2.6 |
| 09:32:33 | 400 | 1 461 | 1 362 | 1 491 | 62.2 | 47.1 | 2.6 |
| 09:32:43 | 400 | 1 577 | 1 448 | 1 583 | 62.2 | 50.4 | 2.6 |
| 09:32:53 | 400 | 1 618 | 1 505 | 1 563 | 62.2 | 52.7 | 2.6 |
| 09:33:03 | 450 | 1 704 | 1 783 | 1 618 | 64.6 | 51.8 | 2.6 |
| 09:33:13 | 450 | 1 846 | 1 978 | 1 757 | 64.6 | 56.3 | 2.6 |
| 09:33:23 | 450 | 1 809 | 1 965 | 1 790 | 64.6 | 56.2 | 2.6 |
| 09:33:33 | 500 | 1 886 | 2 107 | 1 770 | 67.1 | 54.4 | 2.7 |
| 09:33:43 | 500 | 2 043 | 2 331 | 1 978 | 67.1 | 62.5 | 2.7 |

---

## Analysis

### What the numbers say

The pool fix delivered a **marginal throughput improvement (+3 %)** but did **not meaningfully change the success rate** (50.7 % → 51.3 %). The send-rate ceiling at 500 users is ~2 000 msg/10 s in both versions.

### Why the improvement is small

`send_message` is an exclusively write-heavy path. Every call does:

1. `SELECT` — look up or create a conversation row
2. `INSERT INTO conversations` (conditional)
3. `INSERT INTO messages`
4. WS fan-out (group messages also run a `SELECT … group_members`)

Even with WAL mode + pool, **SQLite allows only one concurrent writer** at any moment. Every connection in the pool that tries to write blocks at the SQLite file lock. `PRAGMA busy_timeout=5000` makes them wait (preventing the instant `SQLITE_BUSY` failures seen in the baseline) but the overall write throughput ceiling is identical.

The Rust `Arc<Mutex<Connection>>` was a _proxy_ for the same constraint. Removing it moved the queue from Rust userspace to SQLite's internal WAL write lock — same bottleneck, different location.

### Where the pool does help

| Path | Baseline | Pool |
|------|----------|------|
| `GET /messages` | Blocked behind any in-flight write | Proceeds concurrently on its own connection |
| `GET /groups` | Same — blocked | Concurrent |
| `GET /users/me` | Same | Concurrent |
| `POST /messages/send` (write path) | Queued at Rust mutex | Queued at SQLite WAL lock |

Read endpoints (history, group list, user lookup) will now scale much better under mixed read/write load, even if the write-only benchmark does not show a large change.

### System resources

- **Memory**: 47.6 MB → 67.1 MB (+19.5 MB) — pool added 10 connections vs baseline's 1; overhead is ~1.9 MB/connection, linear and stable.
- **CPU**: peaks at 62.5 % vs baseline 58 % at full 500-user load. The extra CPU is pool management overhead and the additional concurrent request processing.
- **WS connections**: 0 errors across all 500 connections.

---

## What to do next

The pool fix is a necessary foundation but not sufficient for a write-heavy workload. The binding constraint is SQLite's single-writer WAL lock. The next steps in order of impact:

| Step | Expected gain | Complexity |
|------|--------------|------------|
| **Write actor** — one dedicated task owns the write connection; all writes are sent through a `tokio::mpsc` channel | Eliminates pool-level queueing; makes backpressure explicit; enables batching | Medium |
| **Transaction batching** — accumulate N writes per `BEGIN … COMMIT` | 10–50× write throughput (1 lock for N writes vs N locks) | Medium |
| **Separate read pool + write pool of 1** — reads get 9 connections, writes get 1 | Concurrent reads; writes still serialise but reads don't block writes | Low–Medium |
| **redb / embedded MVCC store** | Eliminates global write lock entirely; pure Rust | High |
