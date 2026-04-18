import { QasaListingData, SearchFilters, SearchResult } from '../types';

/**
 * Health check endpoint wrapper.
 */
export async function fetchHealth(): Promise<{ status: string }> {
  const response = await fetch('/api/health');
  if (!response.ok) throw new Error('Health check failed');
  return response.json();
}

/**
 * Fetches a single listing by ID.
 */
export async function fetchListing(homeId: string): Promise<QasaListingData> {
  const response = await fetch(`/api/listing/${homeId}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch listing');
  }
  return response.json();
}

/**
 * Runs a search with filters.
 */
export async function searchListings(filters: SearchFilters): Promise<SearchResult> {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Search failed');
  }
  return response.json();
}

/**
 * Parses a Qasa URL and returns the listing data.
 */
export async function parseUrl(url: string): Promise<QasaListingData> {
  const response = await fetch('/api/parse-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to parse URL');
  }
  return response.json();
}
