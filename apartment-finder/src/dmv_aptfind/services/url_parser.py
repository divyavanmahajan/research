"""URL parser for extracting Qasa home IDs from listing URLs."""

import re

# Matches URLs like:
#   https://qasa.com/se/en/home/1348599
#   https://www.qasa.com/se/en/home/1348599
#   https://qasa.se/home/1348599
#   https://qasa.com/home/1348599/anything-else
QASA_URL_PATTERN = re.compile(r"https?://(?:www\.)?qasa\.(?:com|se)/.*/home/(\d+)")


def extract_home_id(url: str) -> str | None:
    """Extract the numeric home ID from a Qasa listing URL.

    Returns the ID string if found, or None if the URL doesn't match.
    """
    match = QASA_URL_PATTERN.search(url)
    if match:
        return match.group(1)
    return None
