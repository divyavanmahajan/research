const request = require('supertest');
const app = require('../server');

jest.mock('../scrapers/qasa', () => ({
  scrapeUrl: jest.fn(),
  scrapeSearch: jest.fn(),
}));

const { scrapeUrl, scrapeSearch } = require('../scrapers/qasa');

const mockListing = {
  title: 'Test Apartment',
  address: 'Testgatan 1',
  city: 'Stockholm',
  lat: 59.33,
  lng: 18.06,
  price: 10000,
  deposit: 20000,
  size: 40,
  rooms: 2,
  floor: '2',
  availableFrom: '2026-05-01',
  photos: ['https://cdn.qasa.se/photo1.jpg'],
  description: 'A test apartment',
  sourceUrl: 'https://qasa.se/homes/test123',
};

const mockResults = [
  {
    title: 'Test Apartment',
    address: 'Testgatan 1',
    price: 10000,
    size: 40,
    rooms: 2,
    photo: 'https://cdn.qasa.se/photo1.jpg',
    sourceUrl: 'https://qasa.se/homes/test123',
  },
];

beforeEach(() => {
  jest.clearAllMocks();
});

describe('GET /api/health', () => {
  it('returns 200 with status ok', async () => {
    const res = await request(app).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
  });
});

describe('GET /api/scrape', () => {
  it('returns scraped listing data for a valid qasa URL', async () => {
    scrapeUrl.mockResolvedValue(mockListing);

    const res = await request(app)
      .get('/api/scrape')
      .query({ url: 'https://qasa.se/homes/test123' });

    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Test Apartment');
    expect(res.body.price).toBe(10000);
    expect(scrapeUrl).toHaveBeenCalledWith('https://qasa.se/homes/test123');
  });

  it('returns 400 when url param is missing', async () => {
    const res = await request(app).get('/api/scrape');
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/url/i);
  });

  it('returns 400 when url is not a qasa.se URL', async () => {
    const res = await request(app)
      .get('/api/scrape')
      .query({ url: 'https://evil.com/malicious' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/qasa\.se/i);
  });

  it('returns 502 when scraper throws', async () => {
    scrapeUrl.mockRejectedValue(new Error('Network error'));

    const res = await request(app)
      .get('/api/scrape')
      .query({ url: 'https://qasa.se/homes/test123' });

    expect(res.status).toBe(502);
    expect(res.body.error).toBeDefined();
  });
});

describe('GET /api/search', () => {
  it('returns search results', async () => {
    scrapeSearch.mockResolvedValue(mockResults);

    const res = await request(app)
      .get('/api/search')
      .query({ city: 'Stockholm', minPrice: '8000', maxPrice: '15000' });

    expect(res.status).toBe(200);
    expect(res.body.results).toHaveLength(1);
    expect(res.body.results[0].title).toBe('Test Apartment');
    expect(scrapeSearch).toHaveBeenCalledWith({
      city: 'Stockholm',
      minPrice: '8000',
      maxPrice: '15000',
      minSize: undefined,
      maxSize: undefined,
      rooms: undefined,
    });
  });

  it('returns empty results array when nothing found', async () => {
    scrapeSearch.mockResolvedValue([]);

    const res = await request(app).get('/api/search').query({ city: 'Nowhere' });

    expect(res.status).toBe(200);
    expect(res.body.results).toEqual([]);
  });

  it('returns 502 when scraper throws', async () => {
    scrapeSearch.mockRejectedValue(new Error('Scrape failed'));

    const res = await request(app).get('/api/search').query({ city: 'Stockholm' });

    expect(res.status).toBe(502);
    expect(res.body.error).toBeDefined();
  });
});
