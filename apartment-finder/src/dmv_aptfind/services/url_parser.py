"""URL parser for extracting listing IDs from supported listing URLs."""

import re

# Matches URLs like:
#   https://qasa.com/se/en/home/1348599
#   https://www.qasa.com/se/en/home/1348599
#   https://qasa.se/home/1348599
#   https://qasa.com/home/1348599/anything-else
QASA_URL_PATTERN = re.compile(r"https?://(?:www\.)?qasa\.(?:com|se)/.*/home/(\d+)")

# Matches KEY Relocation listing URLs, e.g.:
#   https://kr-backoffice-web-production.azurewebsites.net/FEA64C9F-F2B2-4CA4-AB40-5A755038247C
KR_URL_PATTERN = re.compile(
    r"https?://kr-backoffice-web[^/]*/([0-9A-Fa-f-]{36})",
    re.IGNORECASE,
)


def extract_home_id(url: str) -> str | None:
    """Extract the numeric home ID from a Qasa listing URL.

    Returns the ID string if found, or None if the URL doesn't match.
    """
    match = QASA_URL_PATTERN.search(url)
    if match:
        return match.group(1)
    return None


def extract_kr_id(url: str) -> str | None:
    """Extract the GUID from a KEY Relocation listing URL.

    Returns the GUID string if found, or None if the URL doesn't match.
    """
    match = KR_URL_PATTERN.search(url)
    return match.group(1) if match else None
