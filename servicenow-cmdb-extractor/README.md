# sn-cmdb-extractor

> Browser-based ServiceNow CMDB extractor — download any CMDB table into a
> local SQLite database using only your browser session. No API credentials required.

See **[docs/README.md](docs/README.md)** for full documentation.

## Quick Start

```bash
pip install -e .
playwright install chromium

sn-cmdb login --instance https://dev12345.service-now.com
sn-cmdb download all --instance https://dev12345.service-now.com
sn-cmdb status
sn-cmdb diagram
```

For LLM/AI usage, see **[CLAUDE.md](CLAUDE.md)**.
