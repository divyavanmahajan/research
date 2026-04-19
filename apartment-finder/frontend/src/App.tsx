import { useEffect } from 'react';
import { LeftPanel } from './components/layout/LeftPanel'
import { MapPanel } from './components/layout/MapPanel'
import { ApartmentDetail } from './components/mylist/ApartmentDetail'
import { Toast } from './components/common/Toast'
import { useAppStore } from './store/useAppStore'
import { DB_KEY } from './utils/db'

const SIZE_WARN_BYTES = 4 * 1024 * 1024;

function App() {
  const showToast = useAppStore(state => state.showToast);
  const selectedId = useAppStore(state => state.selectedApartmentId);
  const setSelectedId = useAppStore(state => state.setSelectedApartment);
  const apartments = useAppStore(state => state.apartments);
  const selectedApt = apartments.find(a => a.id === selectedId) ?? null;

  useEffect(() => {
    const stored = localStorage.getItem(DB_KEY);
    if (stored && stored.length > SIZE_WARN_BYTES) {
      showToast(
        `Storage is ${(stored.length / 1024 / 1024).toFixed(1)} MB — consider exporting and trimming your list.`,
        'error'
      );
    }
  }, []);

  return (
    <div className="app-container">
      <LeftPanel />
      <MapPanel />
      {selectedApt && (
        <ApartmentDetail
          apartment={selectedApt}
          onClose={() => setSelectedId(null)}
        />
      )}
      <Toast />
    </div>
  )
}

export default App
