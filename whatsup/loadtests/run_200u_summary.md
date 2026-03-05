# Load-Test Summary — 200 Users

| Parameter | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Max users** | 200 |
| **Groups** | 20 |
| **Duration** | 300 s (5 min) |
| **Log file** | `run_200u.log` |

## Final Totals

| Metric | Value |
|--------|-------|
| Messages sent (REST success) | 13 674 |
| Messages received (WS events) | 13 546 |
| Messages failed | 11 995 |
| WS connect errors | 0 |
| **Send success rate** | **53.3 %** |
| Avg send rate (full-load phase) | ~53 msg/s |

## Metric Snapshots (every 10 s)

| Timestamp | Active WS | Sent Δ | Recv Δ | Fail Δ | Proc Mem MB | Proc CPU % | Sys Mem % |
|-----------|-----------|--------|--------|--------|-------------|------------|-----------|
| 07:21:15 | 20 | 79 | 11 | 71 | 43.9 | 0.0 | 2.3 |
| 07:21:25 | 20 | 89 | 24 | 72 | 43.9 | 3.7 | 2.3 |
| 07:21:35 | 20 | 86 | 28 | 81 | 43.9 | 4.0 | 2.3 |
| 07:21:45 | 40 | 152 | 51 | 131 | 45.0 | 6.9 | 2.3 |
| 07:21:55 | 40 | 177 | 52 | 144 | 45.0 | 6.6 | 2.3 |
| 07:22:05 | 40 | 167 | 43 | 142 | 45.0 | 5.0 | 2.3 |
| 07:22:15 | 60 | 240 | 109 | 194 | 46.1 | 9.6 | 2.3 |
| 07:22:25 | 60 | 282 | 120 | 206 | 46.1 | 9.0 | 2.3 |
| 07:22:35 | 60 | 262 | 99 | 219 | 46.1 | 10.1 | 2.3 |
| 07:22:45 | 80 | 305 | 155 | 286 | 46.2 | 13.2 | 2.4 |
| 07:22:55 | 80 | 325 | 177 | 314 | 46.2 | 12.5 | 2.4 |
| 07:23:05 | 80 | 361 | 204 | 296 | 46.2 | 14.2 | 2.4 |
| 07:23:15 | 100 | 433 | 327 | 324 | 47.5 | 14.3 | 2.4 |
| 07:23:25 | 100 | 457 | 325 | 352 | 47.5 | 14.9 | 2.4 |
| 07:23:35 | 100 | 430 | 319 | 365 | 47.5 | 15.7 | 2.4 |
| 07:23:45 | 120 | 467 | 385 | 442 | 48.7 | 21.3 | 2.4 |
| 07:23:55 | 120 | 499 | 407 | 447 | 48.7 | 17.7 | 2.4 |
| 07:24:05 | 120 | 519 | 462 | 438 | 48.7 | 20.0 | 2.4 |
| 07:24:15 | 140 | 547 | 547 | 466 | 48.8 | 21.5 | 2.4 |
| 07:24:25 | 140 | 620 | 676 | 520 | 48.8 | 24.0 | 2.4 |
| 07:24:35 | 140 | 578 | 572 | 545 | 48.8 | 24.3 | 2.4 |
| 07:24:45 | 160 | 609 | 705 | 566 | 50.0 | 24.7 | 2.4 |
| 07:24:55 | 160 | 658 | 698 | 609 | 50.0 | 24.2 | 2.4 |
| 07:25:05 | 160 | 694 | 797 | 567 | 50.0 | 25.4 | 2.4 |
| 07:25:15 | 180 | 709 | 952 | 635 | 51.1 | 28.3 | 2.4 |
| 07:25:25 | 180 | 749 | 1013 | 679 | 51.1 | 27.0 | 2.4 |
| 07:25:35 | 180 | 739 | 862 | 675 | 51.1 | 30.6 | 2.4 |
| 07:25:45 | 200 | 800 | 1170 | 692 | 51.2 | 30.3 | 2.4 |
| 07:25:55 | 200 | 797 | 1077 | 778 | 51.2 | 30.1 | 2.4 |

## Observations

- **System resources**: stable — sys_mem_pct held at 2.3–2.4 %, well within the 90 % threshold.  Ramp completed to all 200 users without any resource stop.
- **Failure rate** (~47 %): slightly worse than the 100-user run; SQLite write-lock contention continues to dominate failures.  At 200 concurrent senders the queue is longer and more requests time out.
- **Throughput scales linearly**: send rate doubled from ~25 msg/s (100 users) to ~53 msg/s (200 users) — expected for a lock-serialised workload where each request takes about the same service time.
- **Recv > Send at high concurrency**: group message fan-out means each successful send generates multiple WS `NewMessage` deliveries.
- **Memory growth**: 43.9 MB → 51.2 MB across 200 connections (+7.3 MB vs 100 users' +3.7 MB), approximately linear.
- **CPU growth**: peaks ~30 % at 200 users vs ~19 % at 100 users — consistent ~0.15 % per user.
- **No WS connection errors**: all 200 connections established successfully.
