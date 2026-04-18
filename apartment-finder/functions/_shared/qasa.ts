export interface ListingPreview {
  title: string;
  address: string;
  city: string;
  lat: number | null;
  lng: number | null;
  price: number;
  deposit: number | null;
  size: number;
  rooms: number;
  floor: string | null;
  availableFrom: string | null;
  photos: string[];
  description: string;
  sourceUrl: string;
}

export interface SearchResult {
  title: string;
  address: string;
  city: string;
  price: number;
  size: number;
  rooms: number;
  photo: string | null;
  sourceUrl: string;
}

export interface SearchParams {
  city?: string;
  minPrice?: string;
  maxPrice?: string;
  minSize?: string;
  maxSize?: string;
  rooms?: string;
}

const HEADERS = {
  'User-Agent': 'ApartmentFinder/1.0 (personal use)',
  'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
};

function parseNextData(html: string): unknown {
  const match = html.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
  if (!match || !match[1]) throw new Error('__NEXT_DATA__ not found — qasa.se page structure may have changed');
  return JSON.parse(match[1]);
}

function extractPhotos(uploads: unknown): string[] {
  if (!Array.isArray(uploads)) return [];
  return uploads
    .filter((u: unknown) => {
      const upload = u as Record<string, unknown>;
      return upload.type === 'image' || !upload.type;
    })
    .map((u: unknown) => (u as Record<string, unknown>).url as string)
    .filter(Boolean);
}

async function fetchHtml(url: string): Promise<string> {
  const res = await fetch(url, { headers: HEADERS });
  if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${url}`);
  return res.text();
}

export async function scrapeUrl(url: string): Promise<ListingPreview> {
  const html = await fetchHtml(url);
  const data = parseNextData(html) as { props?: { pageProps?: { home?: Record<string, unknown> } } };
  const home = data?.props?.pageProps?.home;
  if (!home) throw new Error('No home data found in __NEXT_DATA__ pageProps');

  const loc = (home.location ?? {}) as Record<string, unknown>;
  const lat = typeof loc.latitude === 'number' ? loc.latitude : null;
  const lng = typeof loc.longitude === 'number' ? loc.longitude : null;
  const tenancy = home.tenancy as Record<string, unknown> | null | undefined;

  return {
    title: (home.title as string) ?? '',
    address: (loc.streetAddress as string) ?? '',
    city: (loc.city as string) ?? '',
    lat,
    lng,
    price: (home.rent as number) ?? 0,
    deposit: (home.deposit as number | null) ?? null,
    size: (home.squareMeters as number) ?? 0,
    rooms: (home.numberOfRooms as number) ?? 0,
    floor: home.floor != null ? String(home.floor) : null,
    availableFrom: tenancy?.startOptimal as string ?? null,
    photos: extractPhotos(home.uploads),
    description: (home.description as string) ?? '',
    sourceUrl: url,
  };
}

function buildSearchUrl(params: SearchParams): string {
  const url = new URL('https://qasa.se/homes');
  if (params.city) url.searchParams.set('city', params.city);
  if (params.minPrice) url.searchParams.set('rentMin', params.minPrice);
  if (params.maxPrice) url.searchParams.set('rentMax', params.maxPrice);
  if (params.minSize) url.searchParams.set('squareMetersMin', params.minSize);
  if (params.maxSize) url.searchParams.set('squareMetersMax', params.maxSize);
  if (params.rooms) url.searchParams.set('numberOfRooms', params.rooms);
  return url.toString();
}

export async function scrapeSearch(params: SearchParams): Promise<SearchResult[]> {
  const searchUrl = buildSearchUrl(params);
  const html = await fetchHtml(searchUrl);
  const data = parseNextData(html) as { props?: { pageProps?: { homes?: Record<string, unknown>[] } } };
  const homes = data?.props?.pageProps?.homes ?? [];

  return homes.map(home => {
    const loc = (home.location ?? {}) as Record<string, unknown>;
    const photo = extractPhotos(home.uploads)[0] ?? null;
    return {
      title: (home.title as string) ?? '',
      address: (loc.streetAddress as string) ?? '',
      city: (loc.city as string) ?? '',
      price: (home.rent as number) ?? 0,
      size: (home.squareMeters as number) ?? 0,
      rooms: (home.numberOfRooms as number) ?? 0,
      photo,
      sourceUrl: `https://qasa.se/homes/${home.id as string}`,
    };
  });
}
