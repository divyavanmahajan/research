# Load-Test Summary — 300 Users

| Parameter | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Max users** | 300 |
| **Groups** | 30 |
| **Duration** | 300 s (5 min) |
| **Log file** | `run_300u.log` |

## Final Totals

| Metric | Value |
|--------|-------|
| Messages sent (REST success) | 19 901 |
| Messages received (WS events) | 18 160 |
| Messages failed | 18 256 |
| WS connect errors | 0 |
| **Send success rate** | **52.2 %** |
| Avg send rate (full-load phase) | ~107 msg/s |

## Metric Snapshots (every 10 s)

| Timestamp | Active WS | Sent Δ | Recv Δ | Fail Δ | Proc Mem MB | Proc CPU % | Sys Mem % |
|-----------|-----------|--------|--------|--------|-------------|------------|-----------|
| 07:28:05 | 30 | 124 | 31 | 97 | 45.9 | 0.0 | 2.4 |
| 07:28:15 | 30 | 144 | 31 | 106 | 45.9 | 4.9 | 2.4 |
| 07:28:25 | 30 | 139 | 29 | 104 | 45.9 | 5.7 | 2.4 |
| 07:28:35 | 60 | 218 | 71 | 197 | 47.2 | 9.0 | 2.4 |
| 07:28:45 | 60 | 256 | 87 | 219 | 47.2 | 9.4 | 2.4 |
| 07:28:55 | 60 | 253 | 89 | 227 | 47.2 | 9.4 | 2.4 |
| 07:29:05 | 90 | 336 | 156 | 307 | 48.4 | 11.2 | 2.4 |
| 07:29:15 | 90 | 385 | 161 | 354 | 48.4 | 13.4 | 2.4 |
| 07:29:25 | 90 | 354 | 166 | 355 | 48.4 | 15.9 | 2.4 |
| 07:29:35 | 120 | 456 | 226 | 405 | 49.7 | 16.7 | 2.4 |
| 07:29:45 | 120 | 512 | 255 | 448 | 49.7 | 16.5 | 2.4 |
| 07:29:55 | 120 | 511 | 268 | 444 | 49.7 | 19.0 | 2.4 |
| 07:30:06 | 150 | 526 | 366 | 559 | 50.8 | 19.7 | 2.4 |
| 07:30:16 | 150 | 642 | 442 | 556 | 50.8 | 22.6 | 2.4 |
| 07:30:26 | 150 | 620 | 427 | 585 | 50.8 | 20.9 | 2.4 |
| 07:30:36 | 180 | 701 | 560 | 612 | 52.1 | 23.4 | 2.4 |
| 07:30:46 | 180 | 759 | 605 | 679 | 52.1 | 29.1 | 2.4 |
| 07:30:56 | 180 | 696 | 537 | 721 | 52.1 | 26.3 | 2.4 |
| 07:31:06 | 210 | 795 | 714 | 729 | 53.3 | 26.1 | 2.5 |
| 07:31:16 | 210 | 858 | 764 | 807 | 53.3 | 30.8 | 2.5 |
| 07:31:26 | 210 | 841 | 775 | 822 | 53.3 | 30.5 | 2.5 |
| 07:31:36 | 240 | 915 | 977 | 854 | 54.6 | 32.2 | 2.5 |
| 07:31:46 | 240 | 991 | 965 | 881 | 54.6 | 32.9 | 2.5 |
| 07:31:56 | 240 | 1011 | 1090 | 891 | 54.6 | 36.5 | 2.5 |
| 07:32:06 | 270 | 1045 | 1197 | 947 | 55.9 | 34.1 | 2.5 |
| 07:32:16 | 270 | 1132 | 1343 | 1012 | 55.9 | 38.7 | 2.5 |
| 07:32:26 | 270 | 1096 | 1268 | 1022 | 55.9 | 37.6 | 2.5 |
| 07:32:36 | 300 | 1129 | 1528 | 1048 | 57.1 | 38.2 | 2.5 |
| 07:32:46 | 300 | 1232 | 1504 | 1130 | 57.1 | 42.5 | 2.5 |

## Observations

- **System resources**: stable — sys_mem_pct at 2.4–2.5 %, far within threshold.  Ramp completed fully to 300 users.
- **CPU at full load**: 38–43 % (process) at 300 users — up from 30 % at 200 users.  Trend is accelerating due to SQLite write contention causing more goroutine stalls.
- **Failure rate** (~47.8 %): holds at ~47–48 %; the bottleneck remains the SQLite global mutex.  The actual throughput ceiling of the server is around 1 100–1 200 successful msg/10 s regardless of user count beyond ~200.
- **Send throughput plateau starting**: at 240–300 users the successful Δ send per 10 s stabilises around 1 000–1 200 (roughly the SQLite write ceiling).  Additional users generate more failures rather than more successes.
- **Memory**: 45.9 MB → 57.1 MB at 300 users — steady ~0.037 MB per additional user.
- **No WS connection errors**: all 300 connections established cleanly.
