import { useAppStore } from '../../store/useAppStore';
import { searchListings } from '../../api/qasaApi';

export function SavedSearches() {
  const savedSearches = useAppStore(state => state.savedSearches);
  const deleteSearch = useAppStore(state => state.deleteSearch);
  const setSearchResults = useAppStore(state => state.setSearchResults);
  const setSearchLoading = useAppStore(state => state.setSearchLoading);
  const setActiveTab = useAppStore(state => state.setActiveTab);

  const handleRun = async (filters: any) => {
    setActiveTab('search');
    setSearchLoading(true);
    try {
      const results = await searchListings(filters);
      setSearchResults(results.results, results.totalCount);
    } catch (err: any) {
      alert(err.message || 'Search failed');
      setSearchLoading(false);
    }
  };

  if (savedSearches.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
        <p>No saved searches yet.</p>
        <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>Save your common filter sets in the Search tab.</p>
      </div>
    );
  }

  return (
    <div className="saved-searches-list">
      {savedSearches.map(search => (
        <div 
          key={search.id} 
          className="apartment-card" 
          style={{ flexDirection: 'column', gap: '0.5rem', cursor: 'default' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1rem' }}>{search.name}</h3>
            <button 
              onClick={() => deleteSearch(search.id)} 
              style={{ color: 'var(--tag-red)', background: 'transparent', border: 'none', cursor: 'pointer' }}
            >
              Delete
            </button>
          </div>
          
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {search.filters.areaIdentifier} · 
            {search.filters.maxRent ? `max ${search.filters.maxRent} ${search.filters.currency}` : 'any rent'}
          </p>
          
          <button 
            onClick={() => handleRun(search.filters)}
            className="btn btn-primary"
            style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}
          >
            Run Search
          </button>
        </div>
      ))}
    </div>
  );
}
