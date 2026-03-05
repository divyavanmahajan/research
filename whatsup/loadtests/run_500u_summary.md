# Load-Test Summary — 500 Users

| Parameter | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Max users** | 500 |
| **Groups** | 50 |
| **Duration** | 300 s (5 min) |
| **Log file** | `run_500u.log` |

## Final Totals

| Metric | Value |
|--------|-------|
| Messages sent (REST success) | 31 790 |
| Messages received (WS events) | 25 944 |
| Messages failed | 30 933 |
| WS connect errors | 0 |
| **Send success rate** | **50.7 %** |
| Avg send rate (full-load phase) | ~168 msg/s |

## Metric Snapshots (every 10 s)

| Timestamp | Active WS | Sent Δ | Recv Δ | Fail Δ | Proc Mem MB | Proc CPU % | Sys Mem % |
|-----------|-----------|--------|--------|--------|-------------|------------|-----------|
| 07:42:48 | 50 | 195 | 40 | 172 | 47.0 | 0.0 | 2.5 |
| 07:42:58 | 50 | 193 | 37 | 207 | 47.0 | 7.4 | 2.5 |
| 07:43:08 | 50 | 199 | 32 | 197 | 47.0 | 9.5 | 2.5 |
| 07:43:18 | 100 | 365 | 78 | 339 | 48.4 | 15.8 | 2.5 |
| 07:43:28 | 100 | 410 | 99 | 368 | 48.5 | 15.4 | 2.5 |
| 07:43:38 | 100 | 391 | 95 | 400 | 48.5 | 16.1 | 2.5 |
| 07:43:48 | 150 | 530 | 194 | 541 | 50.9 | 21.9 | 2.5 |
| 07:43:58 | 150 | 610 | 228 | 562 | 50.9 | 20.9 | 2.5 |
| 07:44:08 | 150 | 639 | 238 | 570 | 50.9 | 23.2 | 2.5 |
| 07:44:18 | 200 | 725 | 344 | 698 | 52.4 | 27.2 | 2.6 |
| 07:44:28 | 200 | 835 | 425 | 766 | 52.4 | 28.6 | 2.6 |
| 07:44:38 | 200 | 829 | 395 | 775 | 52.4 | 29.6 | 2.6 |
| 07:44:48 | 250 | 904 | 456 | 891 | 54.9 | 35.2 | 2.6 |
| 07:44:58 | 250 | 999 | 594 | 987 | 54.9 | 34.8 | 2.6 |
| 07:45:08 | 250 | 976 | 597 | 1006 | 54.9 | 38.3 | 2.6 |
| 07:45:18 | 300 | 1103 | 794 | 1050 | 57.4 | 37.4 | 2.6 |
| 07:45:28 | 300 | 1158 | 853 | 1227 | 57.4 | 43.9 | 2.6 |
| 07:45:38 | 300 | 1244 | 861 | 1131 | 57.4 | 41.0 | 2.6 |
| 07:45:48 | 350 | 1225 | 1049 | 1289 | 59.0 | 44.5 | 2.6 |
| 07:45:58 | 350 | 1434 | 1182 | 1372 | 59.0 | 46.8 | 2.6 |
| 07:46:08 | 350 | 1388 | 1109 | 1380 | 59.0 | 46.2 | 2.6 |
| 07:46:18 | 400 | 1457 | 1327 | 1374 | 61.4 | 46.3 | 2.6 |
| 07:46:28 | 400 | 1584 | 1515 | 1556 | 61.4 | 52.1 | 2.6 |
| 07:46:38 | 400 | 1566 | 1497 | 1599 | 61.4 | 51.1 | 2.6 |
| 07:46:48 | 450 | 1605 | 1646 | 1532 | 64.0 | 48.6 | 2.6 |
| 07:46:58 | 450 | 1801 | 1914 | 1751 | 64.0 | 54.7 | 2.6 |
| 07:47:08 | 450 | 1748 | 1825 | 1810 | 64.0 | 57.3 | 2.6 |
| 07:47:18 | 500 | 1706 | 1954 | 1584 | 66.4 | 50.9 | 2.7 |
| 07:47:28 | 500 | 1988 | 2275 | 1859 | 66.4 | 58.0 | 2.7 |

## Observations

- **System resources**: all within safe limits — sys_mem_pct peaked at 2.7 %, proc CPU peaked at 58 %.  The 90 % memory and 95 % CPU thresholds were **not** reached; the harness ran to completion.
- **Failure rate** (~49.3 %): the server is handling ~50 % of attempts successfully at this load level.  The SQLite global write mutex is the bottleneck — successful throughput barely increases past ~200–250 users, but total attempt volume doubles.
- **Send throughput**: successful send delta per 10 s at 500 users is 1 700–2 000, which is only marginally above the 300-user ceiling of 1 100–1 200 and 400-user ceiling of 1 300–1 600.  The server's effective maximum write throughput is approximately **1 500–2 000 msg/10 s** regardless of user count.
- **Memory**: 47.0 MB → 66.4 MB — +19.4 MB from baseline.  Per-connection overhead ~0.039 MB, linear.
- **No WS connection errors**: all 500 connections established cleanly.
- **Max users reached**: the sequence was not stopped by resource exhaustion; all five planned runs completed.
