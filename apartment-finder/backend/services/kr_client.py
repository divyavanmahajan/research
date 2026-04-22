"""KEY Relocation listing scraper.

Fetches a listing page from kr-backoffice-web-production.azurewebsites.net and
normalises the data into the same shape as a Qasa HomeView response.

Real page structure (verified):
  - Fields: <tr><th>Label</th><td>Value</td></tr>
  - Descriptions: <div class="card-header">Title</div><div class="card-body">Text</div>
  - Images: <a href="https://krbackofficeprod.blob.core.windows.net/...">
  - HTML entities used throughout (&#xA0; &#xF6; etc.) — decoded via html.unescape()
"""

import html as html_module
import re
from datetime import datetime, timezone

import httpx

from services.geocoder import geocode

SWEDISH_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "maj": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
}


def _extract_th_value(html: str, label: str) -> str | None:
    """Return the decoded text of the <td> following a <th> with the given label."""
    pattern = re.compile(
        rf"<th[^>]*>\s*{re.escape(label)}\s*</th>\s*<td[^>]*>(.*?)</td>",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(html)
    if not m:
        return None
    text = re.sub(r"<[^>]+>", " ", m.group(1))
    text = html_module.unescape(text)
    text = text.replace("\u00a0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text if text else None


def _extract_card_body(html: str, header: str) -> str | None:
    """Return text from the card-body div following a card-header with the given text."""
    pattern = re.compile(
        rf'<div[^>]*class="[^"]*card-header[^"]*"[^>]*>\s*{re.escape(header)}\s*</div>\s*<div[^>]*class="[^"]*card-body[^"]*"[^>]*>(.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(html)
    if not m:
        return None
    text = re.sub(r"<[^>]+>", " ", m.group(1))
    text = html_module.unescape(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text if text else None


def _parse_swedish_date(text: str) -> str | None:
    """Parse a Swedish date like '1 apr 2026' or 'ons 1 apr 2026' → ISO string."""
    m = re.search(r"(\d{1,2})\s+([a-zåäö]{3})\s+(\d{4})", text.lower())
    if not m:
        return None
    day, month_str, year = int(m.group(1)), m.group(2), int(m.group(3))
    month = SWEDISH_MONTHS.get(month_str)
    if not month:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}T00:00:00Z"


def _extract_images(html: str) -> list[str]:
    """Return full-resolution Azure Blob image URLs from anchor hrefs on the page."""
    return re.findall(
        r'<a[^>]+href="(https://krbackofficeprod\.blob\.core\.windows\.net/[^"]+)"',
        html,
        re.IGNORECASE,
    )


async def fetch_kr_listing(url: str, guid: str) -> dict | None:
    """Fetch and parse a KEY Relocation listing page.

    Returns a QasaListingData-shaped dict with id='kr-{guid}', or None if the
    page redirected (listing no longer available).
    """
    async with httpx.AsyncClient(follow_redirects=False) as client:
        resp = await client.get(url, timeout=15.0)
        if resp.is_redirect:
            return None
        resp.raise_for_status()
        html = resp.text

    # Rent — "10&#xA0;000 kr" → "10 000 kr"
    rent = None
    rent_raw = _extract_th_value(html, "Hyra")
    if rent_raw:
        digits = re.sub(r"\D", "", rent_raw)
        rent = int(digits) if digits else None

    # Size — "75 kvm"
    square_meters = None
    size_raw = _extract_th_value(html, "Storlek")
    if size_raw:
        m = re.search(r"(\d+)", size_raw)
        square_meters = int(m.group(1)) if m else None

    # Rooms — "3 rok (1 sov, 1 bad)"
    room_count = None
    rok_raw = _extract_th_value(html, "RoK")
    if rok_raw:
        m = re.search(r"(\d+(?:\.\d+)?)", rok_raw)
        room_count = float(m.group(1)) if m else None

    # Street + floor — text: "Hackspettsgatan (vån 3)"
    route = None
    floor = None
    gata_raw = _extract_th_value(html, "Gata")
    if gata_raw:
        floor_m = re.search(r"v[aå]n\s*(\d+)", gata_raw, re.IGNORECASE)
        if floor_m:
            floor = int(floor_m.group(1))
        route = re.split(r"\s*[\(\,]", gata_raw)[0].strip()

    # Postal code + city — "41270 Göteborg"
    postal_code = None
    locality = None
    post_raw = _extract_th_value(html, "Post")
    if post_raw:
        m = re.match(r"(\d{3}\s?\d{2,3})\s+(.*)", post_raw)
        if m:
            postal_code = m.group(1).strip()
            locality = m.group(2).strip()

    # Duration — spans: "ons 1 apr 2026" and "Tillsvidare"
    start_optimal = None
    end_ufn = False
    tid_raw = _extract_th_value(html, "Tid")
    if tid_raw:
        parts = re.split(r"\s*[-–]\s*", tid_raw, maxsplit=1)
        start_optimal = _parse_swedish_date(parts[0])
        if len(parts) > 1 and "tillsvidare" in parts[1].lower():
            end_ufn = True

    # Descriptions — card-header/card-body divs
    desc_sv = _extract_card_body(html, "Beskrivning")
    desc_en = _extract_card_body(html, "Description in English")
    parts_desc = [d for d in [desc_sv, desc_en] if d]
    description = "\n\n".join(parts_desc) if parts_desc else None

    # Images — grab full-res href, not thumbnail src
    image_urls = _extract_images(html)
    uploads = [
        {
            "id": f"kr-img-{i}",
            "url": img_url,
            "type": "home_picture",
            "metadata": {"primary": i == 0, "order": i, "__typename": "UploadMetadata"},
            "__typename": "Upload",
        }
        for i, img_url in enumerate(image_urls)
    ]

    # Geocode via Nominatim
    lat, lon = None, None
    address_parts = [p for p in [route, postal_code, locality] if p]
    if address_parts:
        async with httpx.AsyncClient() as geo_client:
            result = await geocode(" ".join(address_parts), geo_client)
            if result:
                lat, lon = result

    return {
        "id": f"kr-{guid}",
        "title": None,
        "rent": rent,
        "squareMeters": square_meters,
        "roomCount": room_count,
        "currency": "SEK",
        "status": "normal",
        "rentalType": "long_term",
        "shared": False,
        "description": description,
        "descriptionBuilding": None,
        "descriptionContract": None,
        "descriptionFeatures": None,
        "descriptionLayout": None,
        "descriptionTransportation": None,
        "floor": floor,
        "buildingFloors": None,
        "buildYear": None,
        "bathroomRenovationYear": None,
        "kitchenRenovationYear": None,
        "energyClass": None,
        "tenureType": "rental",
        "firsthand": False,
        "seniorHome": False,
        "studentHome": False,
        "corporateHome": False,
        "publishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "insurance": None,
        "insuranceCost": None,
        "qasaGuarantee": None,
        "qasaGuaranteeCost": None,
        "tenantBaseFee": None,
        "tenantCount": None,
        "minTenantCount": None,
        "maxTenantCount": None,
        "location": {
            "id": None,
            "latitude": lat,
            "longitude": lon,
            "locality": locality,
            "route": route,
            "streetNumber": None,
            "postalCode": postal_code,
            "countryCode": "SE",
            "country": "Sverige",
            "__typename": "Location",
        },
        "uploads": uploads,
        "duration": {
            "id": None,
            "startOptimal": start_optimal,
            "endOptimal": None,
            "startAsap": start_optimal is None,
            "endUfn": end_ufn,
            "possibilityOfExtension": False,
            "__typename": "Duration",
        },
        "traits": [],
        "landlord": {
            "uid": "key-relocation",
            "firstName": "KEY Relocation",
            "companyName": "KEY Relocation Center AB",
            "professional": True,
            "premium": False,
            "proAgent": False,
            "seenAt": None,
            "createdAt": None,
            "__typename": "User",
        },
        "homeTemplates": [],
        "__typename": "Home",
    }
