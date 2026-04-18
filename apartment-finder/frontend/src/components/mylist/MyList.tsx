import { useAppStore } from '../../store/useAppStore';
import { ApartmentCard } from './ApartmentCard';
import { ApartmentDetail } from './ApartmentDetail';
import { ImportExport } from '../common/ImportExport';

export function MyList() {
  const apartments = useAppStore(state => state.apartments);
  const selectedId = useAppStore(state => state.selectedApartmentId);
  const setSelectedId = useAppStore(state => state.setSelectedApartment);

  const selectedApt = apartments.find(a => a.id === selectedId) || null;

  if (apartments.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
        <p>Your list is empty.</p>
        <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>Paste a Qasa URL above to save an apartment.</p>
      </div>
    );
  }

  return (
    <div className="mylist-container">
      <div className="mylist-header" style={{ marginBottom: '1rem' }}>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          {apartments.length} apartment{apartments.length === 1 ? '' : 's'} saved
        </p>
      </div>

      <div className="mylist-scroller">
        {apartments.map(apt => (
          <ApartmentCard
            key={apt.id}
            apartment={apt}
            selected={selectedId === apt.id}
            onClick={() => setSelectedId(apt.id)}
          />
        ))}
      </div>

      <ImportExport />

      <ApartmentDetail 
        apartment={selectedApt} 
        onClose={() => setSelectedId(null)} 
      />
    </div>
  );
}
