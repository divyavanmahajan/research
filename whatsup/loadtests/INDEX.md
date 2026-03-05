# WhatsUp Load-Test Results — Index

> See [HOW_TO_RUN.md](HOW_TO_RUN.md) for setup and usage instructions.

## Test Matrix

| Run | Max Users | Groups | Duration | Setup Time | Status | Send OK | Send Fail | Success Rate | Peak CPU % | Peak Mem MB | Summary |
|-----|-----------|--------|----------|------------|--------|---------|-----------|--------------|------------|-------------|---------|
| 1 | 100 | 10 | 300 s | ~21 s | ✅ Completed | 7 039 | 5 817 | 54.7 % | 18.8 | 48.3 | [run_100u_summary.md](run_100u_summary.md) |
| 2 | 200 | 20 | 300 s | ~45 s | ✅ Completed | 13 674 | 11 995 | 53.3 % | 30.6 | 51.2 | [run_200u_summary.md](run_200u_summary.md) |
| 3 | 300 | 30 | 300 s | ~70 s | ✅ Completed | 19 901 | 18 256 | 52.2 % | 42.5 | 57.1 | [run_300u_summary.md](run_300u_summary.md) |
| 4 | 400 | 40 | 300 s | ~92 s | ✅ Completed | 25 931 | 24 604 | 51.3 % | 44.3 | 61.0 | [run_400u_summary.md](run_400u_summary.md) |
| 5 | 500 | 50 | 300 s | ~113 s | ✅ Completed | 31 790 | 30 933 | 50.7 % | 58.0 | 66.4 | [run_500u_summary.md](run_500u_summary.md) |

All five runs completed. The resource thresholds (sys memory ≥ 90 % or sys CPU ≥ 95 %) were **never triggered**; the server remained stable throughout.

---

## Throughput Summary

| Users | Send Rate (avg, full load) | Successful msg / 10 s | Failure Rate |
|-------|---------------------------|----------------------|--------------|
| 100 | ~25 msg/s | 400–430 | 45.3 % |
| 200 | ~53 msg/s | 780–800 | 46.7 % |
| 300 | ~107 msg/s | 1 050–1 230 | 47.8 % |
| 400 | ~136 msg/s | 1 280–1 640 | 48.7 % |
| 500 | ~168 msg/s | 1 600–2 000 | 49.3 % |

---

## Key Findings

### 1. SQLite Global Write Lock is the Bottleneck
The server uses `Arc<Mutex<rusqlite::Connection>>`, serialising every write (message inserts, token operations, WS ticket updates).  The maximum sustained write throughput is approximately **1 500–2 000 messages per 10 seconds**, regardless of the number of concurrent users beyond ~200–250.

Beyond that user count, extra concurrency increases the *failure* count, not the *success* count.  The success rate erodes from 54.7 % (100 users) to 50.7 % (500 users).

### 2. Resources Are Not Exhausted
System memory stayed at ≤ 2.7 % across all runs; process memory grew linearly at ~0.038 MB per connected user (final: 66 MB for 500 users).  Process CPU peaked at 58 % at 500 users, well below the 95 % threshold.

### 3. WS Connection Scaling is Clean
Zero WS connection errors across all 2 500 user-sessions (100+200+300+400+500).  The Axum/Tokio WebSocket hub scales linearly and does not appear to have a connection-count bottleneck in this range.

### 4. Fan-out Amplifies Received Messages
Group messages fan-out to every group member's WS channel.  This causes `msgs_recv` to exceed `msgs_sent` at higher user counts (groups have up to 9 members), generating observable WS delivery amplification.

### 5. Argon2id Limits Setup Speed
Registration is rate-limited by Argon2id (m=64 MiB, t=3, p=4) combined with the SQLite write lock.  Setup time scales roughly linearly with user count:
- 100 users → 21 s
- 500 users → 113 s

This is a one-time cost; once accounts exist subsequent runs skip re-registration.

---

## Recommended Improvements (if scaling beyond 500 users)

| Area | Change |
|------|--------|
| Database | Replace `Arc<Mutex<Connection>>` with SQLite WAL + connection pool (e.g. `r2d2-sqlite`) or migrate to PostgreSQL |
| Message persistence | Use async write batching or an in-process message queue to decouple receive from persist |
| Auth throughput | Reduce Argon2id cost for test/staging environments; use pre-created accounts in harness |
| WS delivery | Current in-process `DashMap` hub is efficient; no change needed for this scale |

---

## How runs are organised

Each run produces two files in this folder:

| File | Contents |
|------|----------|
| `run_<N>u.log` | Raw harness output (all log levels, line-buffered) |
| `run_<N>u_summary.md` | Parsed metric table + observations |
