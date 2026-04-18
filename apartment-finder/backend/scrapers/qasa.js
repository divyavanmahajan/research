const axios = require('axios');
const cheerio = require('cheerio');

const HEADERS = {
  'User-Agent': 'ApartmentFinder/1.0 (personal use)',
  'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
};

async function fetchHtml(url) {
  const res = await axios.get(url, { headers: HEADERS, timeout: 15000 });
  return res.data;
}

function parseNextData(html) {
  const $ = cheerio.load(html);
  const raw = $('#__NEXT_DATA__').text();
  if (!raw) throw new Error('__NEXT_DATA__ not found — qasa.se page structure may have changed');
  return JSON.parse(raw);
}

function extractPhotos(uploads) {
  if (!Array.isArray(uploads)) return [];
  return uploads
    .filter(u => u.type === 'image' || !u.type)
    .map(u => u.url)
    .filter(Boolean);
}

async function scrapeUrl(url) {
  const html = await fetchHtml(url);
  const data = parseNextData(html);
  const home = data?.props?.pageProps?.home;
  if (!home) throw new Error('No home data found in __NEXT_DATA__ pageProps');

  const loc = home.location ?? {};
  const lat = typeof loc.latitude === 'number' ? loc.latitude : null;
  const lng = typeof loc.longitude === 'number' ? loc.longitude : null;

  return {
    title: home.title ?? '',
    address: loc.streetAddress ?? '',
    city: loc.city ?? '',
    lat,
    lng,
    price: home.rent ?? 0,
    deposit: home.deposit ?? null,
    size: home.squareMeters ?? 0,
    rooms: home.numberOfRooms ?? 0,
    floor: home.floor != null ? String(home.floor) : null,
    availableFrom: home.tenancy?.startOptimal ?? null,
    photos: extractPhotos(home.uploads),
    description: home.description ?? '',
    sourceUrl: url,
  };
}

function buildSearchUrl(params) {
  const url = new URL('https://qasa.se/homes');
  if (params.city) url.searchParams.set('city', params.city);
  if (params.minPrice) url.searchParams.set('rentMin', params.minPrice);
  if (params.maxPrice) url.searchParams.set('rentMax', params.maxPrice);
  if (params.minSize) url.searchParams.set('squareMetersMin', params.minSize);
  if (params.maxSize) url.searchParams.set('squareMetersMax', params.maxSize);
  if (params.rooms) url.searchParams.set('numberOfRooms', params.rooms);
  return url.toString();
}

async function scrapeSearch(params) {
  const searchUrl = buildSearchUrl(params);
  const html = await fetchHtml(searchUrl);
  const data = parseNextData(html);
  const homes = data?.props?.pageProps?.homes ?? [];

  return homes.map(home => {
    const loc = home.location ?? {};
    const photo = extractPhotos(home.uploads)[0] ?? null;
    return {
      title: home.title ?? '',
      address: loc.streetAddress ?? '',
      city: loc.city ?? '',
      price: home.rent ?? 0,
      size: home.squareMeters ?? 0,
      rooms: home.numberOfRooms ?? 0,
      photo,
      sourceUrl: `https://qasa.se/homes/${home.id}`,
    };
  });
}

module.exports = { scrapeUrl, scrapeSearch };
