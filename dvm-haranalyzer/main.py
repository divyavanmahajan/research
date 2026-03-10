#!/usr/bin/env python3
"""
HAR Analyzer — identifies page load bottlenecks from a .har file.

Usage:
    python3 har_analyzer.py <file.har> [--output metrics/reports/]
    python3 har_analyzer.py metrics/hars/mypage.har --output metrics/reports/
"""

import argparse
import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_har(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def get_entries(har: dict) -> list:
    return har["log"]["entries"]


def get_page(har: dict) -> dict:
    pages = har["log"].get("pages", [])
    return pages[0] if pages else {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def transfer_size(entry: dict) -> int:
    """Return transfer size in bytes (fallback to bodySize)."""
    s = entry["response"].get("_transferSize") or entry["response"].get("bodySize") or 0
    return max(int(s), 0)


def mime_base(mime: str) -> str:
    """Strip charset/params and sub-types like +json."""
    m = mime.split(";")[0].strip()
    return re.sub(r"\+.*", "", m)


def host(url: str) -> str:
    return urlparse(url).netloc


def resp_header(entry: dict, name: str) -> str:
    name_lower = name.lower()
    for h in entry["response"]["headers"]:
        if h["name"].lower() == name_lower:
            return h["value"]
    return ""


def timing(entry: dict, key: str) -> float:
    v = entry["timings"].get(key, -1)
    return max(float(v), 0) if v is not None else 0.0


# ---------------------------------------------------------------------------
# Analysis sections
# ---------------------------------------------------------------------------

def analyze_overview(page: dict, entries: list) -> dict:
    dcl = page.get("pageTimings", {}).get("onContentLoad", 0)
    onload = page.get("pageTimings", {}).get("onLoad", 0)
    total_transfer = sum(transfer_size(e) for e in entries)
    return {
        "url": page.get("title", "unknown"),
        "started": page.get("startedDateTime", ""),
        "dom_content_loaded_ms": dcl,
        "on_load_ms": onload,
        "request_count": len(entries),
        "total_transfer_kb": total_transfer / 1024,
    }


def analyze_slowest_requests(entries: list, top_n: int = 15) -> list:
    rows = []
    for e in sorted(entries, key=lambda x: x["time"], reverse=True)[:top_n]:
        rows.append({
            "url": e["request"]["url"],
            "status": e["response"]["status"],
            "time_ms": e["time"],
            "transfer_kb": transfer_size(e) / 1024,
            "dns_ms": timing(e, "dns"),
            "connect_ms": timing(e, "connect"),
            "ssl_ms": timing(e, "ssl"),
            "wait_ms": timing(e, "wait"),
            "receive_ms": timing(e, "receive"),
            "mime": mime_base(e["response"]["content"].get("mimeType", "")),
        })
    return rows


def analyze_domains(entries: list) -> list:
    domains: dict = defaultdict(lambda: {"count": 0, "bytes": 0, "total_ms": 0.0})
    for e in entries:
        d = host(e["request"]["url"])
        domains[d]["count"] += 1
        domains[d]["bytes"] += transfer_size(e)
        domains[d]["total_ms"] += e["time"]
    return sorted(
        [{"domain": d, **v, "avg_ms": v["total_ms"] / v["count"]} for d, v in domains.items()],
        key=lambda x: x["count"],
        reverse=True,
    )


def analyze_large_resources(entries: list, threshold_kb: float = 50.0) -> list:
    rows = []
    for e in entries:
        s = transfer_size(e)
        if s >= threshold_kb * 1024:
            rows.append({
                "url": e["request"]["url"],
                "transfer_kb": s / 1024,
                "mime": mime_base(e["response"]["content"].get("mimeType", "")),
                "time_ms": e["time"],
                "cache_control": resp_header(e, "cache-control"),
            })
    return sorted(rows, key=lambda x: x["transfer_kb"], reverse=True)


def analyze_content_types(entries: list) -> list:
    ct_map: dict = defaultdict(lambda: {"count": 0, "bytes": 0})
    for e in entries:
        ct = mime_base(e["response"]["content"].get("mimeType", "unknown"))
        ct_map[ct]["count"] += 1
        ct_map[ct]["bytes"] += transfer_size(e)
    return sorted(
        [{"mime": ct, **v} for ct, v in ct_map.items()],
        key=lambda x: x["bytes"],
        reverse=True,
    )


def analyze_slow_ttfb(entries: list, threshold_ms: float = 300.0) -> list:
    rows = []
    for e in entries:
        w = timing(e, "wait")
        if w >= threshold_ms:
            rows.append({
                "url": e["request"]["url"],
                "ttfb_ms": w,
                "total_ms": e["time"],
                "domain": host(e["request"]["url"]),
            })
    return sorted(rows, key=lambda x: x["ttfb_ms"], reverse=True)


def analyze_slow_ssl(entries: list, threshold_ms: float = 100.0) -> list:
    rows = []
    for e in entries:
        s = timing(e, "ssl")
        if s >= threshold_ms:
            rows.append({
                "url": e["request"]["url"],
                "ssl_ms": s,
                "domain": host(e["request"]["url"]),
            })
    return sorted(rows, key=lambda x: x["ssl_ms"], reverse=True)


def analyze_slow_dns(entries: list, threshold_ms: float = 50.0) -> list:
    rows = []
    for e in entries:
        d = timing(e, "dns")
        if d >= threshold_ms:
            rows.append({
                "url": e["request"]["url"],
                "dns_ms": d,
                "domain": host(e["request"]["url"]),
            })
    return sorted(rows, key=lambda x: x["dns_ms"], reverse=True)


def analyze_cache(entries: list, min_size_kb: float = 10.0) -> list:
    """Resources above min_size_kb that have no or very short caching."""
    rows = []
    for e in entries:
        s = transfer_size(e)
        if s < min_size_kb * 1024:
            continue
        cc = resp_header(e, "cache-control")
        if not cc or "no-cache" in cc or "no-store" in cc:
            rows.append({
                "url": e["request"]["url"],
                "transfer_kb": s / 1024,
                "cache_control": cc or "(none)",
                "mime": mime_base(e["response"]["content"].get("mimeType", "")),
            })
    return sorted(rows, key=lambda x: x["transfer_kb"], reverse=True)


def analyze_http_versions(entries: list) -> dict:
    versions: dict = defaultdict(int)
    for e in entries:
        v = e["request"].get("httpVersion") or "(unknown)"
        versions[v] += 1
    return dict(versions)


def analyze_redirects(entries: list) -> list:
    rows = []
    for e in entries:
        if e["response"]["status"] in (301, 302, 303, 307, 308):
            loc = resp_header(e, "location")
            rows.append({
                "from": e["request"]["url"],
                "to": loc,
                "status": e["response"]["status"],
            })
    return rows


def analyze_concurrency(entries: list, window_ms: float = 5000.0) -> dict:
    if not entries:
        return {}
    t0 = datetime.datetime.fromisoformat(entries[0]["startedDateTime"].replace("Z", "+00:00"))
    intervals = []
    for e in entries:
        dt = datetime.datetime.fromisoformat(e["startedDateTime"].replace("Z", "+00:00"))
        rel = (dt - t0).total_seconds() * 1000
        if rel > window_ms:
            continue
        intervals.append((rel, rel + e["time"]))

    events = []
    for s, end in intervals:
        events.append((s, 1))
        events.append((end, -1))
    events.sort()
    peak = cur = 0
    for _, delta in events:
        cur += delta
        peak = max(peak, cur)

    return {"window_ms": window_ms, "requests_in_window": len(intervals), "peak_concurrent": peak}


# ---------------------------------------------------------------------------
# Scoring / bottleneck ranking
# ---------------------------------------------------------------------------

SEVERITY = {"critical": "CRITICAL", "warning": "WARNING ", "info": "INFO    "}


def score_bottlenecks(overview: dict, domains: list, large: list, slow_ttfb: list,
                       slow_ssl: list, cache: list, http_versions: dict,
                       content_types: list, concurrency: dict) -> list:
    """Return a ranked list of (severity, title, detail) findings."""
    findings = []

    onload = overview["on_load_ms"]
    dcl = overview["dom_content_loaded_ms"]
    n = overview["request_count"]

    # Overall load time
    if onload > 10000:
        findings.append(("critical", f"onLoad = {onload/1000:.1f}s (>10s)",
                         "Page takes over 10 seconds to fully load. Users will abandon."))
    elif onload > 5000:
        findings.append(("warning", f"onLoad = {onload/1000:.1f}s (>5s)",
                         "Page takes over 5 seconds to fully load."))

    if dcl > 4000:
        findings.append(("critical", f"DOMContentLoaded = {dcl/1000:.1f}s (>4s)",
                         "Render-blocking resources or slow TTFB is delaying first parse."))

    # Request count
    if n > 300:
        findings.append(("critical", f"{n} total requests",
                         "Extremely high request count. Consolidate assets and defer third-party scripts."))
    elif n > 150:
        findings.append(("warning", f"{n} total requests",
                         "High request count. Look for opportunities to consolidate or defer."))

    # JS weight
    js_bytes = next((ct["bytes"] for ct in content_types if "javascript" in ct["mime"]), 0)
    if js_bytes > 500 * 1024:
        findings.append(("critical", f"JavaScript = {js_bytes/1024:.0f} KB",
                         "Excessive JS payload. Apply code splitting, tree-shaking, and defer non-critical bundles."))
    elif js_bytes > 200 * 1024:
        findings.append(("warning", f"JavaScript = {js_bytes/1024:.0f} KB",
                         "High JS payload. Review bundle size and split where possible."))

    # Image weight / format
    img_bytes = sum(ct["bytes"] for ct in content_types if ct["mime"].startswith("image/"))
    webp_bytes = next((ct["bytes"] for ct in content_types if ct["mime"] == "image/webp"), 0)
    avif_bytes = next((ct["bytes"] for ct in content_types if ct["mime"] == "image/avif"), 0)
    if img_bytes > 1024 * 1024 and (webp_bytes + avif_bytes) < img_bytes * 0.2:
        findings.append(("critical", f"Images = {img_bytes/1024:.0f} KB, <20% modern format",
                         "Most images are JPEG/PNG. Convert to WebP or AVIF to save 40–60% image weight."))

    # Third-party ad/tracker overload
    ad_domains = [d for d in domains if any(kw in d["domain"] for kw in
                  ("adnxs", "googlesyndication", "doubleclick", "taboola", "outbrain",
                   "mediago", "udmserve", "rubiconproject", "sharethrough",
                   "deepintent", "thrtle", "lijit", "sovrn", "criteo",
                   "btloader", "adv.", "adsdkprod", "yahoo"))]
    ad_reqs = sum(d["count"] for d in ad_domains)
    if ad_reqs > 30:
        findings.append(("critical", f"{ad_reqs} ad/tracker requests across {len(ad_domains)} domains",
                         "Ad/tracker network requests dominate load time. Load them after onLoad or use async facades."))
    elif ad_reqs > 10:
        findings.append(("warning", f"{ad_reqs} ad/tracker requests across {len(ad_domains)} domains",
                         "Significant ad/tracker load. Consider deferring until after first interaction."))

    # Slow TTFB
    if slow_ttfb:
        worst = slow_ttfb[0]
        findings.append(("warning", f"{len(slow_ttfb)} requests with TTFB >300ms (worst: {worst['ttfb_ms']:.0f}ms)",
                         f"Slow server response on {worst['domain']}. Check server-side rendering, CDN, or DB latency."))

    # Slow SSL
    if len(slow_ssl) > 3:
        findings.append(("warning", f"{len(slow_ssl)} cold TLS handshakes >100ms",
                         "Add <link rel='preconnect'> for top third-party origins to amortize TLS cost."))

    # Cache
    if len(cache) > 5:
        total_uncached_kb = sum(r["transfer_kb"] for r in cache)
        findings.append(("warning", f"{len(cache)} resources ({total_uncached_kb:.0f} KB) with no/short cache",
                         "Add long-lived Cache-Control headers (use content-hash filenames for JS/CSS)."))

    # HTTP/1.1
    h1 = http_versions.get("HTTP/1.1", 0)
    if h1 > 5:
        findings.append(("warning", f"{h1} requests on HTTP/1.1",
                         "Upgrade origins to HTTP/2 to enable multiplexing and reduce head-of-line blocking."))

    # Concurrency
    if concurrency.get("peak_concurrent", 0) > 25:
        findings.append(("warning",
                         f"Peak {concurrency['peak_concurrent']} concurrent requests in first {concurrency['window_ms']/1000:.0f}s",
                         "Browser connection pool is saturated. Defer non-critical requests."))

    # Sort: critical first
    order = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda x: order[x[0]])
    return findings


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self._lines: list = []

    def h1(self, text: str):
        self._lines += ["", "=" * 72, f"  {text}", "=" * 72]

    def h2(self, text: str):
        self._lines += ["", f"--- {text} " + "-" * max(0, 66 - len(text))]

    def line(self, text: str = ""):
        self._lines.append(text)

    def table(self, rows: list, cols: list):
        """cols: list of (header, key, width, fmt)"""
        header = "  ".join(h.ljust(w) for h, _, w, _ in cols)
        self._lines.append(header)
        self._lines.append("-" * len(header))
        for row in rows:
            parts = []
            for h, key, width, fmt in cols:
                val = row.get(key, "")
                if fmt and isinstance(val, (int, float)):
                    cell = fmt.format(val)
                else:
                    cell = str(val)
                parts.append(cell[:width].ljust(width))
            self._lines.append("  ".join(parts))

    def render(self) -> str:
        return "\n".join(self._lines)

    def save(self, path: Path):
        path.write_text(self.render())
        print(f"Report saved to: {path}")


def truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def build_report(har_path: Path, har: dict) -> Report:
    page = get_page(har)
    entries = get_entries(har)

    overview = analyze_overview(page, entries)
    slowest = analyze_slowest_requests(entries)
    domains = analyze_domains(entries)
    large = analyze_large_resources(entries)
    content_types = analyze_content_types(entries)
    slow_ttfb = analyze_slow_ttfb(entries)
    slow_ssl = analyze_slow_ssl(entries)
    slow_dns = analyze_slow_dns(entries)
    cache = analyze_cache(entries)
    http_versions = analyze_http_versions(entries)
    redirects = analyze_redirects(entries)
    concurrency = analyze_concurrency(entries)
    bottlenecks = score_bottlenecks(
        overview, domains, large, slow_ttfb, slow_ssl, cache,
        http_versions, content_types, concurrency
    )

    r = Report()

    # Header
    r.h1("HAR ANALYSIS REPORT")
    r.line(f"  File    : {har_path}")
    r.line(f"  Page    : {overview['url']}")
    r.line(f"  Captured: {overview['started']}")

    # Overview
    r.h2("Overview")
    r.line(f"  DOMContentLoaded : {overview['dom_content_loaded_ms']:,.0f} ms")
    r.line(f"  onLoad           : {overview['on_load_ms']:,.0f} ms")
    r.line(f"  Requests         : {overview['request_count']}")
    r.line(f"  Transferred      : {overview['total_transfer_kb']:.0f} KB")

    # Bottlenecks
    r.h2("Bottleneck Summary (ranked by severity)")
    for i, (sev, title, detail) in enumerate(bottlenecks, 1):
        r.line(f"  [{SEVERITY[sev]}]  {i}. {title}")
        r.line(f"              {detail}")
        r.line()

    # Slowest requests
    r.h2("Top 15 Slowest Requests")
    r.table(
        [{"rank": i + 1, "time": row["time_ms"], "status": row["status"],
          "kb": row["transfer_kb"], "wait": row["wait_ms"],
          "ssl": row["ssl_ms"], "url": truncate(row["url"], 80)}
         for i, row in enumerate(slowest)],
        [("Rank", "rank", 4, None),
         ("Time(ms)", "time", 9, "{:.0f}"),
         ("Status", "status", 6, None),
         ("KB", "kb", 7, "{:.1f}"),
         ("TTFB(ms)", "wait", 9, "{:.0f}"),
         ("SSL(ms)", "ssl", 8, "{:.0f}"),
         ("URL", "url", 80, None)],
    )

    # Large resources
    r.h2(f"Large Resources (>50 KB) — {len(large)} found")
    r.table(
        [{"kb": row["transfer_kb"], "time": row["time_ms"],
          "mime": row["mime"][:25], "cache": row["cache_control"][:20] or "(none)",
          "url": truncate(row["url"], 70)}
         for row in large[:20]],
        [("KB", "kb", 8, "{:.1f}"),
         ("Time(ms)", "time", 9, "{:.0f}"),
         ("Type", "mime", 26, None),
         ("Cache-Control", "cache", 21, None),
         ("URL", "url", 70, None)],
    )

    # Content types
    r.h2("Content Type Breakdown")
    r.table(
        [{"mime": ct["mime"][:35], "count": ct["count"], "kb": ct["bytes"] / 1024}
         for ct in content_types[:15]],
        [("MIME Type", "mime", 36, None),
         ("Requests", "count", 9, None),
         ("KB", "kb", 9, "{:.1f}")],
    )

    # Third-party domains
    r.h2("Top Domains by Request Count")
    r.table(
        [{"domain": truncate(d["domain"], 40), "count": d["count"],
          "kb": d["bytes"] / 1024, "avg": d["avg_ms"]}
         for d in domains[:20]],
        [("Domain", "domain", 41, None),
         ("Reqs", "count", 5, None),
         ("KB", "kb", 8, "{:.1f}"),
         ("Avg ms", "avg", 7, "{:.0f}")],
    )

    # Slow TTFB
    r.h2(f"Slow TTFB >300ms — {len(slow_ttfb)} found")
    if slow_ttfb:
        r.table(
            [{"ttfb": row["ttfb_ms"], "total": row["total_ms"],
              "url": truncate(row["url"], 90)}
             for row in slow_ttfb[:10]],
            [("TTFB(ms)", "ttfb", 9, "{:.0f}"),
             ("Total(ms)", "total", 10, "{:.0f}"),
             ("URL", "url", 90, None)],
        )
    else:
        r.line("  None found.")

    # Slow SSL
    r.h2(f"Slow TLS Handshakes >100ms — {len(slow_ssl)} found")
    if slow_ssl:
        r.table(
            [{"ssl": row["ssl_ms"], "domain": row["domain"],
              "url": truncate(row["url"], 80)}
             for row in slow_ssl[:10]],
            [("SSL(ms)", "ssl", 8, "{:.0f}"),
             ("Domain", "domain", 35, None),
             ("URL", "url", 80, None)],
        )
    else:
        r.line("  None found.")

    # DNS
    r.h2(f"Slow DNS >50ms — {len(slow_dns)} found")
    if slow_dns:
        r.table(
            [{"dns": row["dns_ms"], "url": truncate(row["url"], 90)}
             for row in slow_dns[:10]],
            [("DNS(ms)", "dns", 8, "{:.0f}"),
             ("URL", "url", 90, None)],
        )
    else:
        r.line("  None found.")

    # Cache
    r.h2(f"Poorly Cached Resources (>10 KB, no/short cache) — {len(cache)} found")
    if cache:
        r.table(
            [{"kb": row["transfer_kb"], "cc": row["cache_control"][:25],
              "mime": row["mime"][:20], "url": truncate(row["url"], 70)}
             for row in cache[:15]],
            [("KB", "kb", 8, "{:.1f}"),
             ("Cache-Control", "cc", 26, None),
             ("Type", "mime", 21, None),
             ("URL", "url", 70, None)],
        )
    else:
        r.line("  None found.")

    # Redirects
    r.h2(f"Redirects — {len(redirects)} found")
    if redirects:
        for red in redirects[:10]:
            r.line(f"  [{red['status']}] {truncate(red['from'], 70)}")
            r.line(f"       -> {truncate(red['to'], 70)}")
    else:
        r.line("  None found.")

    # HTTP versions
    r.h2("HTTP Version Breakdown")
    for ver, count in sorted(http_versions.items()):
        r.line(f"  {ver or '(unknown)':<15}: {count} requests")

    # Concurrency
    r.h2("Concurrency")
    r.line(f"  Peak concurrent requests (first {concurrency['window_ms']/1000:.0f}s): {concurrency['peak_concurrent']}")
    r.line(f"  Requests fired in first {concurrency['window_ms']/1000:.0f}s: {concurrency['requests_in_window']}")

    r.h1("END OF REPORT")
    return r


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze a HAR file and report page-load bottlenecks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("har", type=Path, help="Path to the .har file")
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Directory to write the text report (default: print to stdout only)",
    )
    parser.add_argument(
        "--large-kb", type=float, default=50.0,
        help="Threshold in KB for 'large resource' (default: 50)",
    )
    parser.add_argument(
        "--ttfb-ms", type=float, default=300.0,
        help="TTFB threshold in ms (default: 300)",
    )
    parser.add_argument(
        "--ssl-ms", type=float, default=100.0,
        help="SSL handshake threshold in ms (default: 100)",
    )
    parser.add_argument(
        "--dns-ms", type=float, default=50.0,
        help="DNS threshold in ms (default: 50)",
    )
    parser.add_argument(
        "--top-n", type=int, default=15,
        help="Number of slowest requests to show (default: 15)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.har.exists():
        print(f"Error: file not found: {args.har}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {args.har} ...", file=sys.stderr)
    har = load_har(args.har)
    report = build_report(args.har, har)
    text = report.render()

    print(text)

    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        stem = args.har.stem
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = args.output / f"{stem}_{ts}.txt"
        report.save(out_path)


if __name__ == "__main__":
    main()
