import type { SavedApartment, DestinationTravelTime } from '../types';
import { getTagColor } from './pinColor';

// ─── Helpers ────────────────────────────────────────────────────────────────

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-SE', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatRent(rent: number, currency: string): string {
  return `${new Intl.NumberFormat('en-US').format(rent)} ${currency}`;
}

function availableFrom(apt: SavedApartment): string {
  const d = apt.qasaData.duration;
  if (d.startAsap) return 'ASAP';
  if (d.startOptimal) return formatDate(d.startOptimal);
  return '—';
}

// ─── Sort ───────────────────────────────────────────────────────────────────

const TAG_PRIORITY: Record<string, number> = { favourite: 0, interested: 1 };

function tagGroupKey(apt: SavedApartment): string {
  // first tag that isn't favourite/interested, for grouping the "others"
  return apt.tags.find(t => TAG_PRIORITY[t] === undefined) ?? apt.tags[0] ?? '';
}

function sortApartments(apartments: SavedApartment[]): SavedApartment[] {
  return [...apartments].sort((a, b) => {
    const pa = Math.min(...(a.tags.map(t => TAG_PRIORITY[t] ?? 2)));
    const pb = Math.min(...(b.tags.map(t => TAG_PRIORITY[t] ?? 2)));
    if (pa !== pb) return pa - pb;
    // Within same priority tier, group by tag name then by rent
    const ga = tagGroupKey(a);
    const gb = tagGroupKey(b);
    if (ga !== gb) return ga.localeCompare(gb);
    return a.qasaData.rent - b.qasaData.rent;
  });
}

// ─── Summary table ──────────────────────────────────────────────────────────

function renderMin(minutes: number | null, url: string): string {
  const label = minutes != null ? `${minutes}m` : '—';
  return `<a href="${url}" target="_blank" class="tt-link">${label}</a>`;
}

function renderTravelCell(times: DestinationTravelTime[]): string {
  if (times.length === 0) return '—';
  return times.map(t =>
    `<span class="tr-dest">${esc(t.label)}:</span> ` +
    `🚗${renderMin(t.drive_minutes, t.maps_url_drive)} ` +
    `🚌${renderMin(t.transit_minutes, t.maps_url_transit)} ` +
    `🚲${renderMin(t.bike_minutes, t.maps_url_bike)}`
  ).join('<br>');
}

function renderSummaryTable(
  apartments: SavedApartment[],
  travelTimesMap: Map<string, DestinationTravelTime[]>,
): string {
  const rows = apartments.map((apt, i) => {
    const q = apt.qasaData;
    const addr = `${q.location.route}${q.location.streetNumber ? ' ' + q.location.streetNumber : ''}, ${q.location.locality}`;
    const size = `${q.squareMeters} m² · ${q.roomCount} rm`;
    const tagsHtml = apt.tags.length
      ? apt.tags.map(t => `<span class="tag" style="background:${getTagColor(t)}">${esc(t)}</span>`).join(' ')
      : '—';
    const notesHtml = apt.comments.length
      ? `<span class="note-count">${apt.comments.length}</span> ${esc(apt.comments[0].text.slice(0, 60))}${apt.comments[0].text.length > 60 ? '…' : ''}`
      : '—';
    const travelHtml = renderTravelCell(travelTimesMap.get(apt.id) ?? []);
    const avail = availableFrom(apt);

    return `
    <tr>
      <td class="td-num"><a href="#apt-${esc(apt.id)}" class="sec-link">${i + 1}</a></td>
      <td><a href="${esc(apt.qasaUrl)}" target="_blank" class="tt-link">Qasa ↗</a></td>
      <td class="td-addr">${esc(addr)}</td>
      <td class="td-size">${size}</td>
      <td class="td-rent">${formatRent(q.rent, q.currency)}</td>
      <td class="td-tags">${tagsHtml}</td>
      <td class="td-notes">${notesHtml}</td>
      <td class="td-travel">${travelHtml}</td>
      <td class="td-avail">${avail}</td>
    </tr>`;
  }).join('');

  return `
  <div class="summary-wrap">
    <table class="summary">
      <thead>
        <tr>
          <th>#</th>
          <th>Qasa</th>
          <th>Address</th>
          <th>Size</th>
          <th>Rent</th>
          <th>Tags</th>
          <th>Notes</th>
          <th>Travel</th>
          <th>Available</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}

// ─── Individual apartment card ───────────────────────────────────────────────

function renderCommuteFull(times: DestinationTravelTime[]): string {
  if (times.length === 0) return '';
  const rows = times.map(t => `
    <tr>
      <td class="tt-dest">${esc(t.label)}</td>
      <td class="tt-cell">🚗 ${renderMin(t.drive_minutes, t.maps_url_drive)}</td>
      <td class="tt-cell">🚌 ${renderMin(t.transit_minutes, t.maps_url_transit)}</td>
      <td class="tt-cell">🚶 ${renderMin(t.walk_minutes, t.maps_url_walk)}</td>
      <td class="tt-cell">🚲 ${renderMin(t.bike_minutes, t.maps_url_bike)}</td>
    </tr>`).join('');
  return `
    <div class="commute">
      <div class="section-label">Commute</div>
      <table class="tt-table"><tbody>${rows}</tbody></table>
    </div>`;
}

function renderApartment(apt: SavedApartment, travelTimes: DestinationTravelTime[], index: number): string {
  const { qasaData, tags, comments, qasaUrl } = apt;
  const uploads = qasaData.uploads ?? [];
  const photos = uploads.filter(u => u.url).slice(0, 9);

  const tagsHtml = tags.length
    ? `<div class="tags">${tags.map(t => `<span class="tag" style="background:${getTagColor(t)}">${esc(t)}</span>`).join('')}</div>`
    : '';

  const commentsHtml = comments.length
    ? `<div class="comments">
        <div class="section-label">Notes</div>
        ${comments.map(c => `
          <div class="comment">
            <div class="comment-text">${esc(c.text).replace(/\n/g, '<br>')}</div>
            <div class="comment-date">${formatDate(c.createdAt)}</div>
          </div>`).join('')}
      </div>`
    : '';

  const commuteHtml = renderCommuteFull(travelTimes);

  const photosHtml = photos.length
    ? `<div class="photos">${photos.map(p =>
        `<a href="${p.url}" target="_blank"><img src="${p.url}" alt="" loading="lazy"></a>`
      ).join('')}</div>`
    : '';

  const floor = qasaData.floor != null
    ? ` · Floor ${qasaData.floor}${qasaData.buildingFloors ? `/${qasaData.buildingFloors}` : ''}`
    : '';

  const description = qasaData.description
    ? `<div class="description">${esc(qasaData.description).replace(/\n/g, '<br>')}</div>`
    : '';

  const avail = availableFrom(apt);

  return `
  <div class="apt" id="apt-${esc(apt.id)}">
    <div class="apt-num">${index + 1}</div>
    <div class="apt-header">
      <div class="apt-rent">${formatRent(qasaData.rent, qasaData.currency)} / month</div>
      <div class="apt-meta">
        ${qasaData.roomCount} rooms · ${qasaData.squareMeters} m²${floor} ·
        ${esc(qasaData.location.route)}${qasaData.location.streetNumber ? ' ' + esc(qasaData.location.streetNumber) : ''},
        ${esc(qasaData.location.locality)}
        · Available: ${avail}
      </div>
      <a class="apt-link" href="${esc(qasaUrl)}" target="_blank">View on Qasa ↗</a>
    </div>
    ${tagsHtml}
    ${commentsHtml}
    ${commuteHtml}
    ${description}
    ${photosHtml}
  </div>`;
}

// ─── CSS ────────────────────────────────────────────────────────────────────

const CSS = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f9fafb; color: #111827; padding: 32px 16px; }
  .page { max-width: 900px; margin: 0 auto; }
  h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
  .subtitle { color: #6b7280; font-size: 0.875rem; margin-bottom: 28px; }

  /* Summary table */
  .summary-wrap { overflow-x: auto; margin-bottom: 40px; border: 1px solid #e5e7eb; border-radius: 10px; }
  .summary { border-collapse: collapse; width: 100%; font-size: 0.8125rem; }
  .summary thead th { background: #f3f4f6; padding: 10px 12px; text-align: left; font-weight: 600; color: #374151; border-bottom: 1px solid #e5e7eb; white-space: nowrap; }
  .summary tbody tr:hover { background: #fafafa; }
  .summary td { padding: 9px 12px; border-bottom: 1px solid #f3f4f6; vertical-align: top; }
  .summary tbody tr:last-child td { border-bottom: none; }
  .td-num { text-align: center; width: 32px; }
  .td-addr { min-width: 160px; }
  .td-size { white-space: nowrap; }
  .td-rent { white-space: nowrap; font-weight: 600; color: #6366f1; }
  .td-tags { min-width: 100px; }
  .td-notes { max-width: 200px; font-size: 0.75rem; color: #6b7280; line-height: 1.4; }
  .td-travel { min-width: 160px; font-size: 0.75rem; line-height: 1.8; }
  .td-avail { white-space: nowrap; }
  .sec-link { color: #6366f1; font-weight: 700; text-decoration: none; }
  .sec-link:hover { text-decoration: underline; }
  .note-count { display: inline-block; background: #e0e7ff; color: #3730a3; border-radius: 9999px; padding: 0 6px; font-size: 0.7rem; font-weight: 700; margin-right: 4px; }
  .tr-dest { font-weight: 500; color: #374151; }

  /* Apartment cards */
  .apt { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 24px; margin-bottom: 24px; position: relative; scroll-margin-top: 24px; }
  .apt-num { position: absolute; top: 16px; right: 20px; font-size: 1.5rem; font-weight: 700; color: #e5e7eb; }
  .apt-header { margin-bottom: 12px; }
  .apt-rent { font-size: 1.25rem; font-weight: 700; color: #6366f1; }
  .apt-meta { color: #6b7280; font-size: 0.875rem; margin-top: 4px; line-height: 1.5; }
  .apt-link { color: #6366f1; text-decoration: none; font-size: 0.8125rem; display: inline-block; margin-top: 6px; }
  .apt-link:hover { text-decoration: underline; }
  .tags { display: flex; gap: 6px; flex-wrap: wrap; margin: 12px 0; }
  .tag { padding: 3px 10px; border-radius: 9999px; font-size: 0.75rem; color: white; font-weight: 500; }
  .section-label { font-size: 0.75rem; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
  .comments { background: #f9fafb; border-left: 3px solid #d1d5db; padding: 12px 16px; margin: 12px 0; border-radius: 0 6px 6px 0; }
  .comment { margin-bottom: 10px; }
  .comment:last-child { margin-bottom: 0; }
  .comment-text { font-size: 0.875rem; line-height: 1.5; color: #374151; }
  .comment-date { font-size: 0.75rem; color: #9ca3af; margin-top: 3px; }
  .commute { background: #f9fafb; border-left: 3px solid #d1d5db; padding: 12px 16px; margin: 12px 0; border-radius: 0 6px 6px 0; }
  .tt-table { border-collapse: collapse; font-size: 0.8125rem; }
  .tt-dest { color: #374151; font-weight: 500; padding: 3px 16px 3px 0; white-space: nowrap; }
  .tt-cell { color: #6b7280; padding: 3px 12px 3px 0; white-space: nowrap; }
  .tt-link { color: #6366f1; text-decoration: none; }
  .tt-link:hover { text-decoration: underline; }
  .description { font-size: 0.875rem; line-height: 1.6; color: #374151; margin: 12px 0; }
  .photos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 16px; }
  .photos img { width: 100%; aspect-ratio: 4/3; object-fit: cover; border-radius: 6px; display: block; }
  @media (max-width: 600px) { .photos { grid-template-columns: repeat(2, 1fr); } }
`;

// ─── Public API ──────────────────────────────────────────────────────────────

export function generateHtmlExport(
  apartments: SavedApartment[],
  travelTimesMap: Map<string, DestinationTravelTime[]> = new Map(),
): string {
  const sorted = sortApartments(apartments);
  const date = new Date().toLocaleDateString('en-SE', { year: 'numeric', month: 'long', day: 'numeric' });
  const count = sorted.length;

  const summaryTable = renderSummaryTable(sorted, travelTimesMap);
  const cards = sorted.map((apt, i) =>
    renderApartment(apt, travelTimesMap.get(apt.id) ?? [], i)
  ).join('\n');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Apartment Shortlist — ${date}</title>
  <style>${CSS}</style>
</head>
<body>
  <div class="page">
    <h1>Apartment Shortlist</h1>
    <p class="subtitle">${count} apartment${count === 1 ? '' : 's'} · Exported ${date}</p>
    ${summaryTable}
    ${cards}
  </div>
</body>
</html>`;
}

export function downloadHtml(html: string, filename: string): void {
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
