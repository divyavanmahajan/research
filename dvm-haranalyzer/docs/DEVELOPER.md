# Developer Guide — HAR Analyzer

This document explains the architecture and how to extend the tool.

## Architecture

`har-analyzer.py` is a single-file script organised in four layers:

```
┌──────────────────────────────────────────┐
│  CLI (parse_args / main)                 │  argument parsing, entry point
├──────────────────────────────────────────┤
│  Report (build_report / Report class)    │  assembles and renders sections
├──────────────────────────────────────────┤
│  Analysis functions (analyze_*)          │  one function per analysis type
├──────────────────────────────────────────┤
│  Helpers / loaders (load_har, host, …)   │  shared utilities
└──────────────────────────────────────────┘
```

### Key design choices

- **No dependencies** — uses only the Python standard library so it runs anywhere.
- **Each analysis function is pure** — it takes `entries: list` (and optionally a threshold)
  and returns a plain list of dicts. Easy to unit-test or reuse.
- **`score_bottlenecks` is separate from display** — scoring logic lives in one place;
  rendering logic lives in `build_report`. Change one without touching the other.
- **`Report` is a simple line buffer** — call `r.h1()`, `r.table()`, `r.line()`, then
  `r.render()` or `r.save()`. No templating library needed.

---

## Adding a New Analysis Section

**Step 1 — Write the analysis function.**

All analysis functions follow the same signature:

```python
def analyze_something(entries: list, threshold: float = 0.0) -> list:
    rows = []
    for e in entries:
        # inspect e['request'], e['response'], e['timings'], e['time']
        if meets_condition(e, threshold):
            rows.append({
                "url": e["request"]["url"],
                "some_metric": e["timings"].get("wait", 0),
            })
    return sorted(rows, key=lambda x: x["some_metric"], reverse=True)
```

Useful fields in an entry:

| Path | Type | Description |
|---|---|---|
| `e["request"]["url"]` | str | Full request URL |
| `e["request"]["method"]` | str | GET, POST, … |
| `e["request"]["httpVersion"]` | str | HTTP/1.1, HTTP/2 |
| `e["response"]["status"]` | int | HTTP status code |
| `e["response"]["content"]["mimeType"]` | str | MIME type |
| `e["response"].get("_transferSize")` | int | Bytes on the wire |
| `e["response"].get("bodySize")` | int | Decoded body bytes |
| `e["timings"]["dns"]` | float | DNS lookup ms (-1 = reused) |
| `e["timings"]["connect"]` | float | TCP connect ms |
| `e["timings"]["ssl"]` | float | TLS handshake ms |
| `e["timings"]["wait"]` | float | TTFB ms |
| `e["timings"]["receive"]` | float | Download ms |
| `e["time"]` | float | Total request duration ms |
| `e["startedDateTime"]` | str | ISO 8601 start time |

**Step 2 — Call it in `build_report`.**

```python
my_results = analyze_something(entries, threshold=200)
```

**Step 3 — Render it with `r.table()` or `r.line()`.**

```python
r.h2(f"My New Section — {len(my_results)} found")
r.table(
    [{"metric": row["some_metric"], "url": truncate(row["url"], 90)}
     for row in my_results[:10]],
    [("Metric(ms)", "metric", 10, "{:.0f}"),
     ("URL",        "url",    90, None)],
)
```

`r.table(rows, cols)` format for `cols`:
```python
(header_label, dict_key, column_width, format_string_or_None)
# format_string applies only to numeric values, e.g. "{:.1f}", "{:.0f}"
```

**Step 4 — Optionally add a finding to `score_bottlenecks`.**

```python
if len(my_results) > 5:
    findings.append((
        "warning",                     # "critical", "warning", or "info"
        f"{len(my_results)} things found",
        "Explanation and recommended fix.",
    ))
```

---

## Adding a CLI Flag for a New Threshold

1. Add to `parse_args()`:
   ```python
   parser.add_argument("--my-threshold", type=float, default=200.0,
                       help="Threshold for my new check (default: 200)")
   ```
2. Pass it through in `main()`:
   ```python
   my_results = analyze_something(entries, threshold=args.my_threshold)
   ```

---

## Changing Output Format

### Plain text (default)
Everything goes through the `Report` class. Adjust `Report.table()` or `Report.h2()` to
change formatting globally.

### JSON output
Add an `--json` flag and call the analysis functions directly, then `json.dump` the results:

```python
if args.json:
    output = {
        "overview": overview,
        "slowest": slowest,
        "large": large,
        # …
    }
    print(json.dumps(output, indent=2))
    return
```

### CSV output
After getting a list of dicts from any `analyze_*` function, write it with `csv.DictWriter`:

```python
import csv, io
buf = io.StringIO()
writer = csv.DictWriter(buf, fieldnames=slowest[0].keys())
writer.writeheader()
writer.writerows(slowest)
print(buf.getvalue())
```

---

## Changing the Bottleneck Scoring

All severity logic lives in `score_bottlenecks()`. Each finding is a tuple:

```python
("critical" | "warning" | "info", "Short title", "Longer explanation.")
```

To add or tune a rule, edit the `if/elif` blocks in that function. The sort order is:
`critical → warning → info`.

To add a new severity level, add it to the `SEVERITY` dict at the top of the file and
include it in the sort `order` dict inside `score_bottlenecks`.

---

## Unit Testing

Because every `analyze_*` function is pure (list in, list out), they are easy to test
without needing a real HAR file:

```python
# test_har-analyzer.py
from har-analyzer import analyze_slow_ttfb

def make_entry(wait_ms, url="https://example.com"):
    return {
        "request": {"url": url},
        "response": {"status": 200, "content": {"mimeType": ""}, "headers": [],
                     "_transferSize": 0, "bodySize": 0},
        "timings": {"wait": wait_ms, "dns": 0, "connect": 0, "ssl": 0, "receive": 0},
        "time": wait_ms,
        "startedDateTime": "2024-01-01T00:00:00.000Z",
    }

def test_slow_ttfb():
    entries = [make_entry(100), make_entry(500), make_entry(800)]
    results = analyze_slow_ttfb(entries, threshold_ms=300)
    assert len(results) == 2
    assert results[0]["ttfb_ms"] == 800
```

Run with:
```bash
python3 -m pytest test_har-analyzer.py
```

---

## Comparing Multiple HAR Files

To compare two runs (e.g. before and after optimisation), run both through the tool and
diff the reports:

```bash
python3 har-analyzer.py metrics/hars/before.har --output metrics/reports/
python3 har-analyzer.py metrics/hars/after.har  --output metrics/reports/
diff metrics/reports/before_*.txt metrics/reports/after_*.txt
```

Or extend `build_report` to accept two `entries` lists and add a "Delta" column to each
table row.
