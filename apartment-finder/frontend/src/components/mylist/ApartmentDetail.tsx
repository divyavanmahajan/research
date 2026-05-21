import { useState } from 'react';
import type { SavedApartment } from '../../types';
import { TagInput } from '../tags/TagInput';
import { CommentThread } from '../comments/CommentThread';
import { CommuteSection } from './CommuteSection';
import { useAppStore } from '../../store/useAppStore';
import { ConfirmDialog } from '../common/ConfirmDialog';
import { generateHtmlExport, downloadHtml } from '../../utils/htmlExport';
import { fetchTravelTimes } from '../../api/qasaApi';

interface Props {
  apartment: SavedApartment;
  onClose: () => void;
}

export function ApartmentDetail({ apartment, onClose }: Props) {
  const updateTags = useAppStore(state => state.updateTags);
  const addComment = useAppStore(state => state.addComment);
  const deleteComment = useAppStore(state => state.deleteComment);
  const removeApartment = useAppStore(state => state.removeApartment);

  const [confirmDelete, setConfirmDelete] = useState(false);
  const [sharingHtml, setSharingHtml] = useState(false);
  const travelDestinations = useAppStore(state => state.travelDestinations);

  const { qasaData } = apartment;

  return (
    <div className="detail-panel">
      <div className="detail-panel-header">
        <h2 style={{ fontSize: '1.25rem' }}>Details</h2>
        <button onClick={onClose} className="btn" style={{ fontSize: '1.25rem', background: 'transparent', lineHeight: 1 }}>×</button>
      </div>

      <div className="detail-scroll">
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.25rem', color: 'var(--primary)' }}>
            {new Intl.NumberFormat('en-US').format(qasaData.rent)} {qasaData.currency}
          </h3>
          <p style={{ color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {qasaData.roomCount} rooms · {qasaData.squareMeters} m² · {qasaData.location.route}, {qasaData.location.locality}
          </p>
          {apartment.qasaUrl && (
            <a
              href={apartment.qasaUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--primary)', fontSize: '0.875rem', textDecoration: 'none', display: 'block', marginTop: '0.5rem' }}
            >
              {apartment.qasaUrl.includes('qasa') ? 'Open in Qasa ↗' : 'View listing ↗'}
            </a>
          )}
        </div>

        <div style={{ fontSize: '0.875rem', lineHeight: '1.5', whiteSpace: 'pre-wrap', marginBottom: '1.5rem' }}>
          {qasaData.description}
        </div>

        <TagInput
          tags={apartment.tags}
          onChange={(newTags) => updateTags(apartment.id, newTags)}
        />

        <CommentThread
          comments={apartment.comments}
          onAdd={(text) => addComment(apartment.id, text)}
          onDelete={(cid) => deleteComment(apartment.id, cid)}
        />

        <CommuteSection
          lat={qasaData.location.latitude}
          lon={qasaData.location.longitude}
        />

        {(qasaData.uploads ?? []).length > 0 && (
          <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
            <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, marginBottom: '0.75rem' }}>Photos</h4>
            <div className="photos-grid">
              {(qasaData.uploads ?? []).filter(u => u.url).map(u => (
                <a key={u.id} href={u.url} target="_blank" rel="noopener noreferrer">
                  <img src={u.url} alt="" className="photo-thumb" />
                </a>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: '3rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <button
            className="btn"
            style={{ background: 'var(--bg-app)', border: '1px solid var(--border-color)', width: '100%' }}
            disabled={sharingHtml}
            onClick={async () => {
              setSharingHtml(true);
              const travelTimesMap = new Map();
              if (travelDestinations.length > 0) {
                try {
                  const result = await fetchTravelTimes(
                    qasaData.location.latitude,
                    qasaData.location.longitude,
                    travelDestinations,
                  );
                  travelTimesMap.set(apartment.id, result.results);
                } catch { /* omit commute if fetch fails */ }
              }
              setSharingHtml(false);
              const html = generateHtmlExport([apartment], travelTimesMap);
              const id = qasaData.location.locality.toLowerCase().replace(/\s+/g, '-');
              downloadHtml(html, `apartment-${id}-${apartment.id}.html`);
            }}
          >
            {sharingHtml ? 'Fetching times…' : 'Share as HTML ✉'}
          </button>
          <button
            className="btn"
            style={{ color: 'var(--tag-red)', background: 'transparent', borderColor: 'var(--tag-red)', width: '100%' }}
            onClick={() => setConfirmDelete(true)}
          >
            Remove from List
          </button>
          {confirmDelete && (
            <ConfirmDialog
              message="Remove this apartment from your list? This cannot be undone."
              confirmLabel="Remove"
              onConfirm={() => { removeApartment(apartment.id); onClose(); }}
              onCancel={() => setConfirmDelete(false)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
