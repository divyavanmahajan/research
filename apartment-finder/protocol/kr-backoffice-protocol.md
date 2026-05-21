# KEY Relocation Backoffice — Listing Page Protocol

## Overview

`kr-backoffice-web-production.azurewebsites.net` is an ASP.NET MVC application
operated by KEY Relocation Center AB (keyrelocation.se), a Swedish relocation
agency. Each listing is identified by a GUID and is exposed as a **public,
unauthenticated, server-rendered HTML page**. There are no XHR or fetch API
calls — the entire listing payload is delivered in the initial HTML response.

The page title is the street name (e.g., "Hackspettsgatan - KEY Relocation").
All textual content is in Swedish except for an optional English description
block.

---

## Prerequisites

None. The endpoint is fully public. No account, cookie, API key, or token is
required.

The server does set `ARRAffinity` / `ARRAffinitySameSite` cookies (Azure
Application Request Routing), but these are for sticky-session load balancing
only — they are not required for the first request to succeed.

---

## Page Load Sequence

1. **GET `/{guid}`** — returns the full HTML page with all listing data embedded.
2. Static assets (CSS, JS, images from Bootstrap/jQuery) — irrelevant for data
   extraction.
3. Listing photos served from Azure Blob Storage at
   `krbackofficeprod.blob.core.windows.net/residence-images/` — public, no auth.

No deferred/lazy requests. No WebSockets. No JavaScript-driven data fetching.

---

## Request Reference

### Fetch a Single Listing

- **URL:** `https://kr-backoffice-web-production.azurewebsites.net/{guid}`
- **Method:** GET
- **Required Headers:** none — a bare GET with no headers returns HTTP 200 with
  full data.
- **Optional Headers** (send for politeness/accuracy):
  ```
  Accept: text/html
  User-Agent: <your agent string>
  ```
- **Request Body:** none
- **Response Status:** `200 OK` for a valid GUID, `302` redirect to
  `/Home/Error?message=...` for an unknown GUID.
- **Response Content-Type:** `text/html; charset=utf-8`

#### Observed response headers

```
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Server: Microsoft-IIS/10.0
Set-Cookie: ARRAffinity=<hash>;Path=/;HttpOnly;Secure;Domain=kr-backoffice-web-production.azurewebsites.net
Set-Cookie: ARRAffinitySameSite=<hash>;Path=/;HttpOnly;SameSite=None;Secure;Domain=kr-backoffice-web-production.azurewebsites.net
Strict-Transport-Security: max-age=2592000
x-ms-middleware-request-id: <uuid>
Request-Context: appId=cid-v1:c91acbac-522a-4ac8-a9e1-82346ad4d2de
X-Powered-By: ASP.NET
```

---

## Data Fields Embedded in the HTML

The response HTML is structured with Bootstrap cards. All listing data is
contained within `<table class="table ...">` elements. The following fields were
observed for the sample listing (`FEA64C9F-F2B2-4CA4-AB40-5A755038247C`):

### Card: Objekt (Object / Reference)

| Swedish label | English meaning | Example value |
|---|---|---|
| Löpnummer | Serial / listing ID | `84534` |
| Direktlänk | Direct link (canonical URL) | `https://kr-backoffice-web-production.azurewebsites.net/FEA64C9F-F2B2-4CA4-AB40-5A755038247C` |

### Card: Lägenhet (Apartment)

| Swedish label | English meaning | Example value |
|---|---|---|
| RoK | Rooms (format: N rok (X sov, Y bad)) | `3 rok (1 sov, 1 bad)` — 3 rooms incl. 1 bedroom, 1 bathroom |
| Storlek | Size | `75 kvm` (square metres) |
| Möblering | Furnishing | `Möblerad` (Furnished) / `Omöblerad` (Unfurnished) |

### Card: Adress (Address)

| Swedish label | English meaning | Example value |
|---|---|---|
| Gata | Street (+ floor in parentheses) | `Hackspettsgatan (vån 3)` — street name, floor 3 |
| Post | Postal code + city | `41270 Göteborg` |
| Område | District / neighbourhood | `Skår intill St Sigfridsgatan` |

The street name links to Eniro maps:
`https://kartor.eniro.se/query?what=map_adr&partner=itbostad3&geo_area={street},{city}&mop=aq`

### Card: Uthyrning (Rental terms)

| Swedish label | English meaning | Example value |
|---|---|---|
| Hyra | Monthly rent | `10 000 kr` |
| Tid | Rental period (start - end) | `ons 1 apr 2026 - Tillsvidare` ("until further notice" = open-ended) |

### Card: Specifikationer (Specifications)

| Swedish label | English meaning | Example value |
|---|---|---|
| Ingår | What is included in rent | `Värme, El, Bredband, Vatten, Sophämtning, Hemförsäkring, Parkering` |
| Krav | Tenant requirements | `Ej barn, Ej rökare, Ej husdjur` (No children, No smokers, No pets) |
| Renoveringar | Renovations | `badrummet (2010), köket (2010)` |
| Utrustning | Equipment / amenities | `Tvättstuga, Dusch, Mikro, TV, Kabel-TV / Parabol, Bredband, Parkering, Förråd` |

### Card: Beskrivning / Description

- Swedish free-text description of the apartment.
- Optional English description in a second card ("Description in English").

### Photos

Photo URLs follow a consistent pattern from Azure Blob Storage:

```
# Thumbnail (smaller, suffix "m" before extension)
https://krbackofficeprod.blob.core.windows.net/residence-images/{landlord_id}/{listing_id}/{hash}m.jpg

# Full-size
https://krbackofficeprod.blob.core.windows.net/residence-images/{landlord_id}/{listing_id}/{hash}.jpg
```

Example from listing 84534, landlord 84:
```
https://krbackofficeprod.blob.core.windows.net/residence-images/84/84534/58b3b05f05b34556a33dfee43f079461m.jpg
https://krbackofficeprod.blob.core.windows.net/residence-images/84/84534/58b3b05f05b34556a33dfee43f079461.jpg
```

Photos are publicly accessible with no authentication.

---

## How to Replicate Without a Browser

### Single curl fetch

```bash
curl -s "https://kr-backoffice-web-production.azurewebsites.net/FEA64C9F-F2B2-4CA4-AB40-5A755038247C"
```

No headers required. Returns the full HTML page with all listing data.

### Python — extract key fields with BeautifulSoup

```python
import re
import httpx
from bs4 import BeautifulSoup

GUID = "FEA64C9F-F2B2-4CA4-AB40-5A755038247C"
BASE = "https://kr-backoffice-web-production.azurewebsites.net"

def fetch_listing(guid: str) -> dict:
    url = f"{BASE}/{guid}"
    resp = httpx.get(url, follow_redirects=False, timeout=15)
    if resp.status_code != 200:
        raise ValueError(f"Listing not found or invalid GUID: {guid}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract all table rows as key-value pairs
    data = {}
    for tr in soup.select("table tr"):
        th = tr.find("th")
        td = tr.find("td")
        if th and td:
            key = th.get_text(strip=True)
            val = td.get_text(" ", strip=True)
            data[key] = val

    # Extract photos (thumbnail URLs from img tags inside the left column)
    photos_col = soup.select_one(".col-4")
    photos = []
    if photos_col:
        for a in photos_col.find_all("a", href=True):
            photos.append(a["href"])  # full-size URL

    # Extract descriptions
    desc_cards = soup.find_all("div", class_="card")
    descriptions = {}
    for card in desc_cards:
        header = card.find("div", class_="card-header")
        body = card.find("div", class_="card-body")
        if header and body and not body.find("table"):
            descriptions[header.get_text(strip=True)] = body.get_text(strip=True)

    return {
        "guid": guid,
        "url": url,
        "fields": data,
        "photos": photos,
        "descriptions": descriptions,
    }

listing = fetch_listing(GUID)
import json
print(json.dumps(listing, ensure_ascii=False, indent=2))
```

#### Example output structure

```json
{
  "guid": "FEA64C9F-F2B2-4CA4-AB40-5A755038247C",
  "url": "https://kr-backoffice-web-production.azurewebsites.net/FEA64C9F-F2B2-4CA4-AB40-5A755038247C",
  "fields": {
    "Löpnummer": "84534",
    "Direktlänk": "https://kr-backoffice-web-production.azurewebsites.net/FEA64C9F-F2B2-4CA4-AB40-5A755038247C",
    "RoK": "3 rok (1 sov, 1 bad)",
    "Storlek": "75 kvm",
    "Möblering": "Möblerad",
    "Gata": "Hackspettsgatan (vån 3)",
    "Post": "41270 Göteborg",
    "Område": "Skår intill St Sigfridsgatan",
    "Hyra": "10 000 kr",
    "Tid": "ons 1 apr 2026 - Tillsvidare",
    "Ingår": "Värme, El, Bredband, Vatten, Sophämtning, Hemförsäkring, Parkering",
    "Krav": "Ej barn, Ej rökare, Ej husdjur",
    "Renoveringar": "badrummet (2010), köket (2010)",
    "Utrustning": "Tvättstuga, Dusch, Mikro, TV, Kabel-TV / Parabol, Bredband, Parkering, Förråd"
  },
  "photos": [
    "https://krbackofficeprod.blob.core.windows.net/residence-images/84/84534/58b3b05f05b34556a33dfee43f079461.jpg",
    "https://krbackofficeprod.blob.core.windows.net/residence-images/84/84534/4fd1e878f19a44939843e60e4f98c3bb.jpg",
    "https://krbackofficeprod.blob.core.windows.net/residence-images/84/84534/b413e179a44e4d47b748ae2f2dffdd82.jpg",
    "https://krbackofficeprod.blob.core.windows.net/residence-images/84/84534/f579ff7bffe1442b9f7f38621bac62a8.jpg",
    "https://krbackofficeprod.blob.core.windows.net/residence-images/84/84534/ae9d71f4995d4694b1181919c2f4241c.jpg"
  ],
  "descriptions": {
    "Beskrivning": "Lägenheten utgör renoverad vind. Allrummet har pentry ...",
    "Description in English": "The flat is located in the attic of a house for two families ..."
  }
}
```

---

## Dynamic Values

| Value | Where it comes from | Notes |
|---|---|---|
| `{guid}` | Supplied externally (e.g., shared link, KEY Relocation staff) | Format: standard UUID v4 uppercase. No discovery endpoint observed — GUIDs must be known in advance. |
| `{listing_id}` (e.g., 84534) | Embedded in HTML as "Löpnummer" | Used in photo blob storage paths. |
| `{landlord_id}` (e.g., 84) | Embedded in photo URLs | The blob path segment before the listing ID. |
| `ARRAffinity` cookie | Set by the server on first response | Not required for reads — ignore it. |

---

## URL Pattern Summary

```
Listing page:
  GET https://kr-backoffice-web-production.azurewebsites.net/{guid}

  Valid GUID   → 200 HTML with listing data
  Unknown GUID → 302 redirect to /Home/Error?message=Couldn%27t+determine+residence+by+id+({guid}).

Photo (full-size):
  GET https://krbackofficeprod.blob.core.windows.net/residence-images/{landlord_id}/{listing_id}/{hash}.jpg

Photo (thumbnail):
  GET https://krbackofficeprod.blob.core.windows.net/residence-images/{landlord_id}/{listing_id}/{hash}m.jpg
```

---

## Notes and Caveats

- **No API / no JSON endpoint observed.** The backend database is never directly
  queried by the browser — all rendering happens server-side in ASP.NET MVC.
  There is no REST or GraphQL API surface to call; the only interface is the HTML
  page itself.

- **GUID discovery.** There is no listing index or search endpoint visible from
  the public side. GUIDs are presumably distributed by KEY Relocation staff to
  prospective tenants. Enumeration is not feasible.

- **Rate limiting.** No `x-ratelimit-*` headers or 429 responses observed. The
  server is Microsoft IIS / Azure App Service; standard Azure front-door rate
  limits may apply at scale.

- **Landlord portal.** A `/Landlord` path exists (returns 200) but was not
  investigated — it likely requires authentication.

- **Language.** All field labels are in Swedish. The values for Möblering, Krav,
  Ingår, and Utrustning appear to be comma-separated enumerations from a fixed
  vocabulary; worth normalising when importing.

- **Rent parsing.** The Hyra value uses a non-breaking space as thousands
  separator (`10\u00a0000 kr`). Strip non-breaking spaces and `kr` before
  parsing to integer.
