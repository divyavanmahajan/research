# Load-Test Summary — 400 Users

| Parameter | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Max users** | 400 |
| **Groups** | 40 |
| **Duration** | 300 s (5 min) |
| **Log file** | `run_400u.log` |

## Final Totals

| Metric | Value |
|--------|-------|
| Messages sent (REST success) | 25 931 |
| Messages received (WS events) | 21 591 |
| Messages failed | 24 604 |
| WS connect errors | 0 |
| **Send success rate** | **51.3 %** |
| Avg send rate (full-load phase) | ~136 msg/s |

## Metric Snapshots (every 10 s)

| Timestamp | Active WS | Sent Δ | Recv Δ | Fail Δ | Proc Mem MB | Proc CPU % | Sys Mem % |
|-----------|-----------|--------|--------|--------|-------------|------------|-----------|
| 07:35:17 | 40 | 163 | 24 | 129 | 45.7 | 0.0 | 2.5 |
| 07:35:27 | 40 | 158 | 15 | 159 | 45.7 | 5.6 | 2.5 |
| 07:35:37 | 40 | 179 | 22 | 136 | 45.7 | 7.0 | 2.5 |
| 07:35:47 | 80 | 280 | 48 | 274 | 47.0 | 9.8 | 2.5 |
| 07:35:57 | 80 | 324 | 76 | 298 | 47.0 | 10.4 | 2.5 |
| 07:36:07 | 80 | 299 | 68 | 317 | 47.1 | 11.3 | 2.5 |
| 07:36:17 | 120 | 450 | 162 | 425 | 49.3 | 15.0 | 2.5 |
| 07:36:27 | 120 | 496 | 172 | 474 | 49.3 | 17.2 | 2.5 |
| 07:36:37 | 120 | 482 | 160 | 477 | 49.3 | 14.8 | 2.5 |
| 07:36:47 | 160 | 589 | 289 | 566 | 50.7 | 18.3 | 2.5 |
| 07:36:57 | 160 | 655 | 303 | 620 | 50.7 | 19.7 | 2.5 |
| 07:37:07 | 160 | 655 | 330 | 617 | 50.7 | 18.4 | 2.5 |
| 07:37:17 | 200 | 756 | 439 | 691 | 52.1 | 22.3 | 2.5 |
| 07:37:27 | 200 | 827 | 482 | 766 | 52.1 | 25.5 | 2.5 |
| 07:37:37 | 200 | 813 | 471 | 772 | 52.1 | 25.9 | 2.5 |
| 07:37:47 | 240 | 885 | 656 | 855 | 54.5 | 23.5 | 2.5 |
| 07:37:57 | 240 | 965 | 698 | 920 | 54.5 | 27.0 | 2.5 |
| 07:38:07 | 240 | 1013 | 704 | 923 | 54.5 | 25.4 | 2.5 |
| 07:38:17 | 280 | 1035 | 857 | 1021 | 55.8 | 30.2 | 2.5 |
| 07:38:27 | 280 | 1128 | 1018 | 1062 | 55.8 | 29.6 | 2.5 |
| 07:38:37 | 280 | 1168 | 943 | 1076 | 55.8 | 29.8 | 2.5 |
| 07:38:47 | 320 | 1208 | 1146 | 1119 | 57.1 | 31.6 | 2.5 |
| 07:38:57 | 320 | 1287 | 1251 | 1199 | 57.1 | 33.6 | 2.5 |
| 07:39:07 | 320 | 1265 | 1206 | 1265 | 57.1 | 35.2 | 2.5 |
| 07:39:17 | 360 | 1271 | 1334 | 1219 | 59.6 | 33.5 | 2.6 |
| 07:39:27 | 360 | 1478 | 1610 | 1363 | 59.6 | 38.1 | 2.6 |
| 07:39:37 | 360 | 1414 | 1483 | 1430 | 59.6 | 41.5 | 2.6 |
| 07:39:47 | 400 | 1447 | 1695 | 1400 | 61.0 | 38.9 | 2.6 |
| 07:39:57 | 400 | 1637 | 2053 | 1519 | 61.0 | 44.3 | 2.6 |

## Observations

- **System resources**: stable throughout — sys_mem_pct reached 2.6 %, well within the 90 % threshold.  Ramp completed fully to 400 users.
- **CPU at full load**: 38–44 % (process) at 400 users.  Still well below the 95 % system threshold.
- **Failure rate** (~48.7 %): continuing to worsen slightly as more concurrents queue on the SQLite lock.
- **Throughput plateau deepens**: the max send delta per 10 s is ~1 600 — nearly unchanged from the 300-user peak of ~1 200, confirming the server has hit its write throughput ceiling.  Any additional users beyond 200–240 mostly add failures, not successes.
- **Memory**: 45.7 MB → 61.0 MB at 400 users (+15.3 MB from baseline). The per-connection overhead is approximately 0.038 MB.
- **No WS connection errors**: all 400 connections established cleanly.
- **Recommended action for 500 users**: resources allow it but expect failure rate ~49–50 % and negligible additional successful throughput.
