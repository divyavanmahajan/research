import { useAppStore } from '../../store/useAppStore';
import { SearchResultCard } from './SearchResultCard';
import { fetchListing } from '../../api/qasaApi';
import { useState, useEffect } from 'react';

export function SearchResults() {
  const results = useAppStore(state => state.searchResults);
  const totalCount = useAppStore(state => state.totalResults);
  const apartments = useAppStore(state => state.apartments);
  const addApartment = useAppStore(state => state.addApartment);
  const selectedId = useAppStore(state => state.selectedApartmentId);
  const setSelectedId = useAppStore(state => state.setSelectedApartment);

  const showToast = useAppStore(state => state.showToast);
  const [addingId, setAddingId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId) return;
    document.querySelector(`[data-search-id="${selectedId}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [selectedId]);

  const handleAdd = async (id: string) => {
    setAddingId(id);
    try {
      const fullData = await fetchListing(id);
      const url = `https://qasa.se/home/${id}`;
      addApartment(fullData, url);
      showToast('Apartment saved to your list', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to fetch full data', 'error');
    } finally {
      setAddingId(null);
    }
  };

  return (
    <div className="search-results" style={{ marginTop: '1.5rem' }}>
      <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ fontSize: '1rem' }}>Results</h4>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {results.length < totalCount
            ? `Showing ${results.length} of ${totalCount.toLocaleString()}`
            : `${totalCount} found`}
        </span>
      </div>

      <div className="results-list">
        {results.map(result => (
          <SearchResultCard
            key={result.id}
            result={result}
            selected={selectedId === result.id}
            isSaved={apartments.some(a => a.id === result.id)}
            onClick={() => setSelectedId(result.id)}
            onAdd={() => handleAdd(result.id)}
          />
        ))}
      </div>
      
      {addingId && (
        <div style={{ textAlign: 'center', padding: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Fetching listing data…
        </div>
      )}
    </div>
  );
}
