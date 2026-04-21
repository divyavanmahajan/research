import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { fetchListing } from '../../api/qasaApi';
import { CommuteSection } from '../mylist/CommuteSection';
import type { QasaListingCard } from '../../types';

interface Props {
  result: QasaListingCard;
  onClose: () => void;
}

export function SearchDetail({ result, onClose }: Props) {
  const apartments = useAppStore(state => state.apartments);
  const addApartment = useAppStore(state => state.addApartment);
  const removeApartment = useAppStore(state => state.removeApartment);
  const showToast = useAppStore(state => state.showToast);
  const [adding, setAdding] = useState(false);

  const isSaved = apartments.some(a => a.id === result.id);

  const handleAdd = async () => {
    setAdding(true);
    try {
      const fullData = await fetchListing(result.id);
      addApartment(fullData, `https://qasa.se/home/${result.id}`);
      showToast('Apartment saved to your list', 'success');
    } catch {
      showToast('Failed to fetch listing data', 'error');
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = () => {
    removeApartment(result.id);
    showToast('Removed from list', 'info');
  };

  const photos = (result.uploads ?? []).filter(u => u.url);

  return (
    <div className="detail-panel">
      <div className="detail-panel-header">
        <h2 style={{ fontSize: '1.25rem' }}>Details</h2>
        <button onClick={onClose} className="btn" style={{ fontSize: '1.25rem', background: 'transparent', lineHeight: 1 }}>×</button>
      </div>

      <div className="detail-scroll">
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.25rem', color: 'var(--primary)' }}>
            {new Intl.NumberFormat('en-US').format(result.rent)} {result.currency}
          </h3>
          <p style={{ color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {result.roomCount} rooms · {result.squareMeters} m² · {result.location.route}, {result.location.locality}
          </p>
          <a
            href={`https://qasa.se/home/${result.id}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--primary)', fontSize: '0.875rem', textDecoration: 'none', display: 'block', marginTop: '0.5rem' }}
          >
            Open in Qasa ↗
          </a>
        </div>

        {result.description && (
          <div style={{ fontSize: '0.875rem', lineHeight: '1.5', whiteSpace: 'pre-wrap', marginBottom: '1.5rem' }}>
            {result.description}
          </div>
        )}

        <CommuteSection lat={result.location.point.lat} lon={result.location.point.lon} />

        {photos.length > 0 && (
          <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
            <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, marginBottom: '0.75rem' }}>Photos</h4>
            <div className="photos-grid">
              {photos.map(p => (
                <a key={p.id} href={p.url} target="_blank" rel="noopener noreferrer">
                  <img src={p.url} alt="" className="photo-thumb" />
                </a>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
          {isSaved ? (
            <button
              className="btn"
              style={{ color: 'var(--tag-red)', background: 'transparent', borderColor: 'var(--tag-red)', width: '100%' }}
              onClick={handleRemove}
            >
              Remove from List
            </button>
          ) : (
            <button
              className="btn btn-primary"
              style={{ width: '100%' }}
              onClick={handleAdd}
              disabled={adding}
            >
              {adding ? 'Adding…' : 'Add to List'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
