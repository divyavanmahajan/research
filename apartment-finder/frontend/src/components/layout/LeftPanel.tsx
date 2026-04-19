import { useAppStore } from '../../store/useAppStore';
import { useState } from 'react';
import { parseUrl } from '../../api/qasaApi';

import { MyList } from '../mylist/MyList';
import { SearchTab } from '../search/SearchTab';
import { SavedSearches } from '../savedSearches/SavedSearches';

export function LeftPanel() {
  const activeTab = useAppStore((state) => state.activeTab);
  const setActiveTab = useAppStore((state) => state.setActiveTab);
  const addApartment = useAppStore((state) => state.addApartment);
  const apartments = useAppStore((state) => state.apartments);
  const showToast = useAppStore((state) => state.showToast);
  
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAddUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    
    setLoading(true);
    try {
      const data = await parseUrl(url);
      if (apartments.some(a => a.id === data.id)) {
        showToast('Already in your list', 'info');
      } else {
        addApartment(data, url);
        setUrl('');
        setActiveTab('mylist');
        showToast('Apartment added to your list', 'success');
      }
    } catch (err: any) {
      showToast(err.message || 'Failed to add apartment', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="left-panel">
      <header className="left-panel-header">
        <h1>Apartment Finder</h1>
        
        <form onSubmit={handleAddUrl} style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              className="input-field"
              placeholder="Paste Qasa URL..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={loading}
            />
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? '...' : 'Add'}
            </button>
          </div>
        </form>

        <nav className="left-panel-tabs">
          <button
            className={`tab-btn ${activeTab === 'mylist' ? 'active' : ''}`}
            onClick={() => setActiveTab('mylist')}
          >
            My List
          </button>
          <button
            className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            Search
          </button>
          <button
            className={`tab-btn ${activeTab === 'savedSearches' ? 'active' : ''}`}
            onClick={() => setActiveTab('savedSearches')}
          >
            Saved
          </button>
        </nav>
      </header>

      <main className="left-panel-content">
        {activeTab === 'mylist' && <MyList />}
        {activeTab === 'search' && <SearchTab />}
        {activeTab === 'savedSearches' && <SavedSearches />}
      </main>
    </aside>
  );
}
