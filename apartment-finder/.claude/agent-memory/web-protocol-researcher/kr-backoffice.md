---
name: KEY Relocation Backoffice Listing Protocol
description: kr-backoffice-web-production.azurewebsites.net — server-rendered ASP.NET listing pages, no API, no auth, GUID-based URLs
type: reference
---

`kr-backoffice-web-production.azurewebsites.net` is KEY Relocation Center AB's internal backoffice, exposing individual apartment listings as public HTML pages (no login needed).

- **URL pattern:** `GET https://kr-backoffice-web-production.azurewebsites.net/{guid}` — one GUID per listing
- **No API / no XHR.** All data is server-rendered in the initial HTML response. Scraping is done with an HTML parser (BeautifulSoup), not an API client.
- **No authentication required.** ARRAffinity cookies set by Azure load balancer but not needed for reads.
- **GUID discovery:** none — GUIDs are distributed externally by KEY Relocation staff. No index or search endpoint observed on the public side.
- **Error handling:** unknown GUID → 302 redirect to `/Home/Error?message=Couldn%27t+determine+residence+by+id+({guid}).`
- **Photos:** Azure Blob Storage at `krbackofficeprod.blob.core.windows.net/residence-images/{landlord_id}/{listing_id}/{hash}[m].jpg` — public, no auth.
- **Rent field quirk:** uses non-breaking space (`\u00a0`) as thousands separator — strip before parsing to int.
- Full protocol doc: `apartment-finder/protocol/kr-backoffice-protocol.md`
