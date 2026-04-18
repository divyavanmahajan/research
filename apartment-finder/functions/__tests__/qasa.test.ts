import { readFileSync } from 'fs';
import { join } from 'path';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { scrapeUrl, scrapeSearch } from '../_shared/qasa';

const listingHtml = readFileSync(join(__dirname, 'fixtures/qasa-listing.html'), 'utf8');
const searchHtml = readFileSync(join(__dirname, 'fixtures/qasa-search.html'), 'utf8');

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn());
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe('scrapeUrl', () => {
  it('extracts all fields from a listing page', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(listingHtml, { status: 200 })
    );
    const result = await scrapeUrl('https://qasa.se/homes/abc123');

    expect(result.title).toBe('Cozy 2-room apartment in Södermalm');
    expect(result.address).toBe('Hornsgatan 42');
    expect(result.city).toBe('Stockholm');
    expect(result.lat).toBeCloseTo(59.3175);
    expect(result.lng).toBeCloseTo(18.0507);
    expect(result.price).toBe(12500);
    expect(result.deposit).toBe(25000);
    expect(result.size).toBe(52);
    expect(result.rooms).toBe(2);
    expect(result.floor).toBe('3');
    expect(result.availableFrom).toBe('2026-06-01');
    expect(result.photos).toHaveLength(2);
    expect(result.photos[0]).toBe('https://cdn.qasa.se/images/photo1.jpg');
    expect(result.description).toContain('Södermalm');
    expect(result.sourceUrl).toBe('https://qasa.se/homes/abc123');
  });

  it('returns null lat/lng when location coordinates are missing', async () => {
    const noCoordData = {
      props: {
        pageProps: {
          home: {
            id: 'noloc',
            title: 'No Coords Apt',
            location: { streetAddress: 'Gatan 1', city: 'Stockholm', country: 'Sweden' },
            rent: 10000,
            deposit: null,
            squareMeters: 40,
            numberOfRooms: 2,
            floor: null,
            tenancy: null,
            uploads: [],
            description: '',
          },
        },
      },
      page: '/homes/[id]',
    };
    const html = `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(noCoordData)}</script></body></html>`;
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(html, { status: 200 })
    );
    const result = await scrapeUrl('https://qasa.se/homes/noloc');

    expect(result.lat).toBeNull();
    expect(result.lng).toBeNull();
  });

  it('returns empty photos array when no uploads present', async () => {
    const noPhotoData = {
      props: {
        pageProps: {
          home: {
            id: 'nophotos',
            title: 'No Photos Apt',
            location: { streetAddress: 'Gatan 2', city: 'Stockholm', latitude: 59.33, longitude: 18.06 },
            rent: 10000,
            deposit: null,
            squareMeters: 40,
            numberOfRooms: 2,
            floor: null,
            tenancy: null,
            uploads: [],
            description: '',
          },
        },
      },
      page: '/homes/[id]',
    };
    const html = `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(noPhotoData)}</script></body></html>`;
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(html, { status: 200 })
    );
    const result = await scrapeUrl('https://qasa.se/homes/nophotos');

    expect(result.photos).toEqual([]);
  });

  it('throws when __NEXT_DATA__ is absent', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('<html><body>No data here</body></html>', { status: 200 })
    );

    await expect(scrapeUrl('https://qasa.se/homes/broken')).rejects.toThrow('__NEXT_DATA__');
  });

  it('throws when home data is missing from pageProps', async () => {
    const noHomeData = { props: { pageProps: { notHome: {} } }, page: '/homes/[id]' };
    const html = `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(noHomeData)}</script></body></html>`;
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(html, { status: 200 })
    );

    await expect(scrapeUrl('https://qasa.se/homes/nohome')).rejects.toThrow();
  });

  it('throws on non-200 HTTP status', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('Not Found', { status: 404 })
    );

    await expect(scrapeUrl('https://qasa.se/homes/missing')).rejects.toThrow();
  });
});

describe('scrapeSearch', () => {
  it('returns array of listing summaries', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(searchHtml, { status: 200 })
    );
    const results = await scrapeSearch({ city: 'Stockholm' });

    expect(results).toHaveLength(2);
    expect(results[0].title).toBe('Cozy 2-room apartment in Södermalm');
    expect(results[0].address).toBe('Hornsgatan 42');
    expect(results[0].price).toBe(12500);
    expect(results[0].size).toBe(52);
    expect(results[0].rooms).toBe(2);
    expect(results[0].photo).toBe('https://cdn.qasa.se/images/photo1.jpg');
    expect(results[0].sourceUrl).toContain('abc123');
  });

  it('returns empty array when no homes in results', async () => {
    const emptyHtml = '<html><body><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"homes":[]}},"page":"/homes"}</script></body></html>';
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(emptyHtml, { status: 200 })
    );
    const results = await scrapeSearch({ city: 'Nowhere' });

    expect(results).toEqual([]);
  });

  it('includes only image uploads as photo', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(searchHtml, { status: 200 })
    );
    const results = await scrapeSearch({});

    results.forEach(r => {
      expect(r.photo).toMatch(/^https?:\/\//);
    });
  });

  it('throws on non-200 HTTP status', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('Internal Server Error', { status: 500 })
    );

    await expect(scrapeSearch({ city: 'Stockholm' })).rejects.toThrow();
  });
});
