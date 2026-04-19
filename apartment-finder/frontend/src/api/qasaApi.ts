import type { QasaListingData, SearchFilters, SearchResult, TravelDestination, DestinationTravelTime } from '../types';

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
 * Fetches walk and bike travel times from the backend (OSRM) and Google Maps links.
 */
export async function fetchTravelTimes(
  fromLat: number,
  fromLon: number,
  destinations: TravelDestination[],
): Promise<{ results: DestinationTravelTime[] }> {
  const response = await fetch('/api/travel-times', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from_lat: fromLat,
      from_lon: fromLon,
      destinations: destinations.map(d => ({ label: d.label, lat: d.lat, lon: d.lon })),
    }),
  });
  if (!response.ok) throw new Error('Failed to fetch travel times');
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
