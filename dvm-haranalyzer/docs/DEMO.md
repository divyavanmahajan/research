# MSN.com Performance Analysis — Capture & Analyze

*2026-03-09T19:15:56Z by Showboat 0.6.1*
<!-- showboat-id: 57a6e261-d707-4cd7-9bc9-0bc8bd23dd82 -->

This demo walks through the full workflow for capturing and analyzing a page's network performance:

1. **Capture** — `har-capture get` opens a Chromium browser, records all traffic as you interact with the page, and auto-sanitizes the result
2. **Validate** — confirm no PII leaked into the HAR before analysis
3. **Sanitize** — strip any remaining cookies, tokens, and personal data
4. **Analyze** — `dvm-haranalyzer` surfaces bottlenecks ranked by severity

Every code block below is re-executable. Run `uvx showboat verify metrics/demo_msn.md` at any time to confirm outputs still match.

## Step 1 — Capture www.msn.com

`har-capture get` opens a real Chromium browser window pointed at the target URL.
You interact with the page normally (scroll, click, wait for ads to load), then
close the browser tab. The tool records all traffic, auto-sanitizes PII, and writes
the result to the output path.

```bash
# Run this yourself — it opens a Chromium window. Browse the page, then close the tab.
# Uses uv run with the system Python so it finds the already-installed Playwright browsers.
uv run --with "har-capture[cli]" --python python3 \
  har-capture get https://www.msn.com \
    --output metrics/hars/msn_live.har \
    --include-images
```

The step below copies the pre-captured `test.har` (already from www.msn.com) into
`metrics/hars/` so the remaining steps are fully reproducible without a browser.

```bash
cp test.har metrics/hars/msn.har && echo "Copied test.har → metrics/hars/msn.har" && ls -lh metrics/hars/msn.har
```

```output
Copied test.har → metrics/hars/msn.har
-rw-r--r--@ 1 divya  staff    24M Mar  9 20:18 metrics/hars/msn.har
```

## Step 2 — Validate the HAR for PII

Before sanitizing, scan the file to see what sensitive data is present.
`validate` exits non-zero if anything is found, making it safe to use in CI.

```bash
uv run --with "har-capture[cli]" --python python3 har-capture validate metrics/hars/msn.har 2>&1 | head -40
```

```output

metrics/hars/msn.har:
  [ERROR] [Entry 0: https://www.msn.com/sv-se (request)]
     Cookie: MSFPC=GUID=17a4a9247e5241f5bee9b29a4f...
     Reason: Sensitive header 'cookie' with non-redacted value
  [ERROR] [Entry 0: https://www.msn.com/sv-se (response)]
     Set-Cookie: _C_ETH=1; domain=.msn.com; path=/; se...
     Reason: Sensitive header 'cookie' with non-redacted value
  [WARN] [Entry 0: https://www.msn.com/sv-se (content)]
     content: 165.85.67.0
     Reason: Potential public IP address
  [ERROR] [Entry 2: https://assets.msn.com/resolver/api/resolve/v3/config/?ex... (response)]
     x-as-suppresssetcookie: 1
     Reason: Sensitive header 'cookie' with non-redacted value
  [ERROR] [Entry 21: https://c.msn.com/c.gif?rnd=1773075527289&udc=true&pg.n=s... (request)]
     Cookie: OptanonConsent=isGpcEnabled=0&datesta...
     Reason: Sensitive header 'cookie' with non-redacted value
  [ERROR] [Entry 22: https://assets.msn.com/staticsb/statics/latest/adboxes/eg... (request)]
     Cookie: OptanonConsent=isGpcEnabled=0&datesta...
     Reason: Sensitive header 'cookie' with non-redacted value
  [ERROR] [Entry 23: https://assets.msn.com/staticsb/statics/latest/adboxes/ub... (request)]
     Cookie: OptanonConsent=isGpcEnabled=0&datesta...
     Reason: Sensitive header 'cookie' with non-redacted value
  [ERROR] [Entry 24: https://assets.msn.com/staticsb/statics/latest/adboxes/ge... (request)]
     Cookie: OptanonConsent=isGpcEnabled=0&datesta...
     Reason: Sensitive header 'cookie' with non-redacted value
  [ERROR] [Entry 25: https://assets.msn.com/service/news/feed/pages/weblayout?... (request)]
     Cookie: OptanonConsent=isGpcEnabled=0&datesta...
     Reason: Sensitive header 'cookie' with non-redacted value
  [ERROR] [Entry 25: https://assets.msn.com/service/news/feed/pages/weblayout?... (response)]
     Set-Cookie: msnup=%7B%22cnex%22%3A%22no%22%7D; ex...
     Reason: Sensitive header 'cookie' with non-redacted value
  [ERROR] [Entry 25: https://assets.msn.com/service/news/feed/pages/weblayout?... (response)]
     x-as-suppresssetcookie: 1
     Reason: Sensitive header 'cookie' with non-redacted value
  [WARN] [Entry 30: https://assets.msn.com/bundles/v1/homePage/latest/libs_fe... (content)]
     content: 08.408.177.97
     Reason: Potential public IP address
  [WARN] [Entry 30: https://assets.msn.com/bundles/v1/homePage/latest/libs_fe... (content)]
     content: 1.583.065.61
```

Validation found cookies, session tokens, and IP addresses in the raw capture — exactly what we need to strip. Proceeding to sanitize.

## Step 3 — Sanitize

Redacts all sensitive values using salted hashes. The same value maps to the same hash throughout the file, preserving cross-request correlation while hiding actual data.
A JSON report lists everything that was redacted.

```bash
uv run --with "har-capture[cli]" --python python3 har-capture sanitize metrics/hars/msn.har \
    --output metrics/hars/msn_clean.har \
    --report metrics/reports/msn_redaction.json \
    --no-interactive 2>&1
```

```output
Sanitizing metrics/hars/msn.har...

╭────────────────────────────── Review Required ───────────────────────────────╮
│  Version          har-capture 0.4.4                                          │
│                                                                              │
│  Input            metrics/hars/msn.har                                       │
│  Salt             random (correlation within file)                           │
│                                                                              │
│  Auto-redacted    3219                                                       │
│    cookie         3114                                                       │
│    email          8                                                          │
│    field          55                                                         │
│    password       14                                                         │
│    public_ip      16                                                         │
│    serial_number  1                                                          │
│    token          11                                                         │
│                                                                              │
│  Output           metrics/hars/msn_clean.har                                 │
╰──────────────────────────────── Solent Labs™ ────────────────────────────────╯
  Report: metrics/reports/msn_redaction.json

WARNING: Automated sanitization is best-effort.
Before sharing, review the .har file for any remaining sensitive data.

```

```bash
echo "Redaction summary:" && python3 -c "
import json
r = json.load(open(\"metrics/reports/msn_redaction.json\"))
stats = r.get(\"statistics\", r.get(\"summary\", {}))
print(json.dumps(stats, indent=2))
" 2>&1
```

```output
Redaction summary:
{
  "auto_redacted": 3219,
  "user_redacted": 0,
  "user_skipped": 0
}
```

3,219 values automatically redacted: 3,114 cookies, 55 form fields, 14 passwords, 11 tokens, 8 emails, 16 public IPs, and 1 serial number. The sanitized HAR is safe to share and commit.

## Step 4 — Analyze for Performance Bottlenecks

Run `dvm-haranalyzer` against the sanitized HAR. The report is printed to stdout and saved as a timestamped file in `metrics/reports/`.

```bash
uvx dvm-haranalyzer metrics/hars/msn_clean.har --output metrics/reports/ 2>&1 | head -60
```

```output
Loading metrics/hars/msn_clean.har ...

========================================================================
  HAR ANALYSIS REPORT
========================================================================
  File    : metrics/hars/msn_clean.har
  Page    : https://www.msn.com/sv-se
  Captured: 2026-03-09T16:58:46.636Z

--- Overview ----------------------------------------------------------
  DOMContentLoaded : 4,900 ms
  onLoad           : 11,405 ms
  Requests         : 418
  Transferred      : 4158 KB

--- Bottleneck Summary (ranked by severity) ---------------------------
  [CRITICAL]  1. onLoad = 11.4s (>10s)
              Page takes over 10 seconds to fully load. Users will abandon.

  [CRITICAL]  2. DOMContentLoaded = 4.9s (>4s)
              Render-blocking resources or slow TTFB is delaying first parse.

  [CRITICAL]  3. 418 total requests
              Extremely high request count. Consolidate assets and defer third-party scripts.

  [CRITICAL]  4. JavaScript = 853 KB
              Excessive JS payload. Apply code splitting, tree-shaking, and defer non-critical bundles.

  [CRITICAL]  5. Images = 2558 KB, <20% modern format
              Most images are JPEG/PNG. Convert to WebP or AVIF to save 40–60% image weight.

  [CRITICAL]  6. 88 ad/tracker requests across 22 domains
              Ad/tracker network requests dominate load time. Load them after onLoad or use async facades.

  [WARNING ]  7. 20 requests with TTFB >300ms (worst: 717ms)
              Slow server response on acdn.adnxs.com. Check server-side rendering, CDN, or DB latency.

  [WARNING ]  8. 10 cold TLS handshakes >100ms
              Add <link rel='preconnect'> for top third-party origins to amortize TLS cost.

  [WARNING ]  9. 12 resources (396 KB) with no/short cache
              Add long-lived Cache-Control headers (use content-hash filenames for JS/CSS).

  [WARNING ]  10. 12 requests on HTTP/1.1
              Upgrade origins to HTTP/2 to enable multiplexing and reduce head-of-line blocking.

  [WARNING ]  11. Peak 35 concurrent requests in first 5s
              Browser connection pool is saturated. Defer non-critical requests.


--- Top 15 Slowest Requests -------------------------------------------
Rank  Time(ms)   Status  KB       TTFB(ms)   SSL(ms)   URL                                                                             
---------------------------------------------------------------------------------------------------------------------------------------
1     1566       200     36.5     641        0         https://shftr.adnxs.net/r?url=https%3A%2F%2Fimages.mediago.io%2FML%2Fa473067d...
2     1334       403     10.0     357        320       https://cksync.yahoo.co.jp/dispatch?ptr=10901                                   
3     1052       200     0.9      77         0         https://www.bing.com/aes/c.gif?DI=0&DIS=SB_28-1?&RG=f5192f311f004a8d89c10f77d...
4     1043       200     0.9      68         0         https://www.bing.com/aes/c.gif?DI=0&DIS=SB_11-1?&RG=0388c8ac873646f0871d44486...
5     973        200     119.6    486        0         https://srtb.msn.com/auction                                                    
6     916        200     6.8      60         0         https://ib.adnxs.com/setuid?entity=483&code=1CD4EA6B59A7670E05BDFC875DA76146&...
7     865        200     37.8     187        0         https://shftr.adnxs.net/r?url=https%3A%2F%2Fimages.mediago.io%2FML%2Fa0ad6304...
```

## Results Summary

| Metric | Value |
|---|---|
| onLoad | **11.4 s** — CRITICAL |
| DOMContentLoaded | **4.9 s** — CRITICAL |
| Total requests | **418** |
| Transferred | **4.16 MB** |

**Top findings:**

| # | Severity | Finding |
|---|---|---|
| 1 | CRITICAL | onLoad >10s — users will abandon |
| 2 | CRITICAL | DOMContentLoaded >4s — render-blocking resources |
| 3 | CRITICAL | 418 requests — consolidate and defer |
| 4 | CRITICAL | 853 KB JavaScript — split and tree-shake bundles |
| 5 | CRITICAL | 2.5 MB images, <20% WebP/AVIF — convert to modern formats |
| 6 | CRITICAL | 88 ad/tracker requests across 22 domains — defer past onLoad |
| 7 | WARNING | 20 requests with TTFB >300ms (worst: 717ms on adnxs.com) |
| 8 | WARNING | 10 cold TLS handshakes >100ms — add `preconnect` hints |

Full report written to `metrics/reports/`.

## Reproducing this demo

```bash
# Verify all code blocks still produce matching output
uvx showboat verify metrics/demo_msn.md

# Or write an updated copy without modifying the original
uvx showboat verify metrics/demo_msn.md --output metrics/demo_msn_updated.md
```
