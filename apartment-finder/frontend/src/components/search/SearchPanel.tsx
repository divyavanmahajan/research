import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { searchListings } from '../../api/qasaApi';
import type { SearchFilters } from '../../types';

export function SearchPanel() {
  const setSearchResults = useAppStore(state => state.setSearchResults);
  const setSearchLoading = useAppStore(state => state.setSearchLoading);
  const loading = useAppStore(state => state.searchLoading);
  const saveSearch = useAppStore(state => state.saveSearch);
  const showToast = useAppStore(state => state.showToast);
  const setSearchCity = useAppStore(state => state.setSearchCity);

  const [filters, setFilters] = useState<SearchFilters>({
    areaIdentifier: 'se/gothenburg',
    minRent: undefined,
    maxRent: undefined,
    minRoomCount: undefined,
    maxRoomCount: undefined,
    minSquareMeters: undefined,
    maxSquareMeters: undefined,
    currency: 'SEK',
    markets: ['sweden'],
    sortBy: 'published_or_bumped_at',
    sortDirection: 'descending',
  });

  const [searchName, setSearchName] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setSearchLoading(true);
    try {
      const results = await searchListings(filters);
      setSearchResults(results.results, results.totalCount);
    } catch (err: any) {
      showToast(err.message || 'Search failed', 'error');
      setSearchLoading(false);
    }
  };

  const handleSave = () => {
    const name = searchName || filters.areaIdentifier;
    saveSearch(name, filters);
    setSearchName('');
    showToast('Search saved', 'success');
  };

  return (
    <div className="search-panel">
      <form onSubmit={handleSearch}>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.875rem', fontWeight: '500' }}>Area</label>
          <input
            type="text"
            className="input-field"
            value={filters.areaIdentifier}
            onChange={e => {
              setFilters({ ...filters, areaIdentifier: e.target.value });
              setSearchCity(e.target.value);
            }}
            placeholder="e.g. se/gothenburg, se/stockholm"
            required
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.75rem' }}>Min Rent</label>
            <input
              type="number"
              className="input-field"
              value={filters.minRent || ''}
              onChange={e => setFilters({ ...filters, minRent: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem' }}>Max Rent</label>
            <input
              type="number"
              className="input-field"
              value={filters.maxRent || ''}
              onChange={e => setFilters({ ...filters, maxRent: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.75rem' }}>Min Rooms</label>
            <input
              type="number"
              className="input-field"
              value={filters.minRoomCount || ''}
              onChange={e => setFilters({ ...filters, minRoomCount: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem' }}>Min Size (m²)</label>
            <input
              type="number"
              className="input-field"
              value={filters.minSquareMeters || ''}
              onChange={e => setFilters({ ...filters, minSquareMeters: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
          <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
        <p style={{ fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>Save this search</p>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            className="input-field"
            placeholder="Search name..."
            value={searchName}
            onChange={e => setSearchName(e.target.value)}
          />
          <button onClick={handleSave} className="btn" style={{ background: 'var(--bg-app)' }}>Save</button>
        </div>
      </div>
    </div>
  );
}
