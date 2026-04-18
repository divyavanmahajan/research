import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as qasaApi from '../../api/qasaApi';

// Mock fetch globally
global.fetch = vi.fn();

describe('qasaApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetchHealth returns status ok', async () => {
    (fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' }),
    });

    const result = await qasaApi.fetchHealth();
    expect(result).toEqual({ status: 'ok' });
    expect(fetch).toHaveBeenCalledWith('/api/health');
  });

  it('fetchListing returns listing data', async () => {
    const mockListing = { id: '1348599', rent: 11250 };
    (fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockListing),
    });

    const result = await qasaApi.fetchListing('1348599');
    expect(result).toEqual(mockListing);
    expect(fetch).toHaveBeenCalledWith('/api/listing/1348599');
  });

  it('searchListings returns search results', async () => {
    const mockResults = { totalCount: 1, pagesCount: 1, results: [] };
    (fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResults),
    });

    const filters = { areaIdentifier: 'gothenburg', markets: [], sortBy: 'rent' as const, sortDirection: 'ascending' as const, currency: 'SEK' };
    const result = await qasaApi.searchListings(filters);
    expect(result).toEqual(mockResults);
    expect(fetch).toHaveBeenCalledWith('/api/search', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify(filters),
    }));
  });

  it('parseUrl returns listing data from URL', async () => {
    const mockListing = { id: '1348599', rent: 11250 };
    (fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockListing),
    });

    const url = 'https://qasa.com/home/1348599';
    const result = await qasaApi.parseUrl(url);
    expect(result).toEqual(mockListing);
    expect(fetch).toHaveBeenCalledWith('/api/parse-url', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ url }),
    }));
  });
});
