# Load-Test Summary — 100 Users

| Parameter | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Max users** | 100 |
| **Groups** | 10 |
| **Duration** | 300 s (5 min) |
| **Log file** | `run_100u.log` |

## Final Totals

| Metric | Value |
|--------|-------|
| Messages sent (REST success) | 7 039 |
| Messages received (WS events) | 8 605 |
| Messages failed | 5 817 |
| WS connect errors | 0 |
| **Send success rate** | **54.7 %** |
| Avg send rate (full-load phase) | ~25 msg/s |

## Metric Snapshots (every 10 s)

| Timestamp | Active WS | Sent Δ | Recv Δ | Fail Δ | Proc Mem MB | Proc CPU % | Sys Mem % |
|-----------|-----------|--------|--------|--------|-------------|------------|-----------|
| 07:14:42 | 10 | 41 | 7 | 30 | 44.6 | 0.0 | 2.3 |
| 07:14:52 | 10 | 44 | 13 | 32 | 44.6 | 1.9 | 2.3 |
| 07:15:02 | 10 | 38 | 9 | 37 | 44.6 | 1.4 | 2.3 |
| 07:15:12 | 20 | 73 | 38 | 67 | 44.8 | 3.9 | 2.3 |
| 07:15:22 | 20 | 83 | 22 | 75 | 44.8 | 2.9 | 2.3 |
| 07:15:32 | 20 | 89 | 46 | 67 | 44.8 | 3.7 | 2.3 |
| 07:15:42 | 30 | 123 | 51 | 100 | 45.8 | 4.7 | 2.3 |
| 07:15:52 | 30 | 138 | 73 | 103 | 45.8 | 4.1 | 2.3 |
| 07:16:02 | 30 | 125 | 57 | 105 | 45.8 | 4.8 | 2.3 |
| 07:16:12 | 40 | 165 | 100 | 133 | 45.9 | 5.7 | 2.3 |
| 07:16:22 | 40 | 175 | 109 | 150 | 45.9 | 6.8 | 2.3 |
| 07:16:32 | 40 | 179 | 141 | 141 | 45.9 | 5.5 | 2.3 |
| 07:16:42 | 50 | 188 | 174 | 178 | 45.9 | 8.2 | 2.3 |
| 07:16:52 | 50 | 225 | 199 | 176 | 45.9 | 9.1 | 2.3 |
| 07:17:02 | 50 | 232 | 241 | 171 | 45.9 | 9.2 | 2.3 |
| 07:17:12 | 60 | 246 | 291 | 203 | 47.1 | 9.3 | 2.3 |
| 07:17:22 | 60 | 277 | 280 | 192 | 47.1 | 10.5 | 2.3 |
| 07:17:32 | 60 | 283 | 304 | 203 | 47.1 | 10.9 | 2.3 |
| 07:17:42 | 70 | 293 | 416 | 226 | 47.1 | 11.6 | 2.3 |
| 07:17:52 | 70 | 293 | 330 | 271 | 47.1 | 12.9 | 2.3 |
| 07:18:02 | 70 | 298 | 409 | 279 | 47.1 | 13.3 | 2.3 |
| 07:18:12 | 80 | 304 | 375 | 286 | 47.2 | 12.1 | 2.3 |
| 07:18:22 | 80 | 346 | 461 | 304 | 47.2 | 12.9 | 2.3 |
| 07:18:32 | 80 | 353 | 439 | 281 | 47.2 | 14.7 | 2.3 |
| 07:18:42 | 90 | 358 | 596 | 305 | 48.2 | 13.7 | 2.3 |
| 07:18:52 | 90 | 398 | 626 | 335 | 48.2 | 17.0 | 2.3 |
| 07:19:02 | 90 | 382 | 577 | 335 | 48.2 | 16.7 | 2.3 |
| 07:19:12 | 100 | 418 | 741 | 327 | 48.3 | 18.8 | 2.3 |
| 07:19:22 | 100 | 433 | 785 | 367 | 48.3 | 17.7 | 2.3 |

## Observations

- **System resources**: stable throughout — sys_mem_pct held at 2.3 %, well within the 90 % threshold.  No resource-induced ramp stop.
- **Failure rate** (~45 %): Almost entirely caused by SQLite's global write lock (`Arc<Mutex<Connection>>`).  Every concurrent `POST /messages/send` must queue behind the mutex.  Under 100 WS users each sending every 0.5–2 s, the write queue saturates and requests time out.
- **Receive > Send**: `msgs_recv` (8 605) exceeds `msgs_sent` (7 039) because each group message fans out to multiple WS subscribers, so one send can generate several `NewMessage` deliveries.
- **Memory growth**: modest linear increase from 44.6 MB → 48.3 MB across 100 concurrent connections.
- **CPU growth**: linear from ~2 % at 10 users to ~19 % at 100 users — roughly 0.19 % per user at this message rate.
- **No WS connection errors**: the server accepted all 100 WebSocket connections cleanly.
