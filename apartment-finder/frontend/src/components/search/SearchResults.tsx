import { useAppStore } from '../../store/useAppStore';
import { SearchResultCard } from './SearchResultCard';
import { fetchListing } from '../../api/qasaApi';
import { useState } from 'react';

export function SearchResults() {
  const results = useAppStore(state => state.searchResults);
  const totalCount = useAppStore(state => state.totalResults);
  const apartments = useAppStore(state => state.apartments);
  const addApartment = useAppStore(state => state.addApartment);
  const selectedId = useAppStore(state => state.selectedApartmentId);
  const setSelectedId = useAppStore(state => state.setSelectedApartment);

  const [addingId, setAddingId] = useState<string | null>(null);

  const handleAdd = async (id: string) => {
    setAddingId(id);
    try {
      const fullData = await fetchListing(id);
      const url = `https://qasa.se/home/${id}`;
      addApartment(fullData, url);
    } catch (err: any) {
      alert(err.message || 'Failed to fetch full data');
    } finally {
      setAddingId(null);
    }
  };

  return (
    <div className="search-results" style={{ marginTop: '1.5rem' }}>
      <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ fontSize: '1rem' }}>Results</h4>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{totalCount} found</span>
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
        <div style={{ position: 'fixed', bottom: '1rem', left: '1rem', background: 'var(--primary)', color: 'white', padding: '0.5rem 1rem', borderRadius: '0.5rem', zIndex: 100 }}>
          Saving listing...
        </div>
      )}
    </div>
  );
}
