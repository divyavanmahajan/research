import { SavedApartment } from '../../types';
import { TagInput } from '../tags/TagInput';
import { CommentThread } from '../comments/CommentThread';
import { useAppStore } from '../../store/useAppStore';

interface Props {
  apartment: SavedApartment | null;
  onClose: () => void;
}

export function ApartmentDetail({ apartment, onClose }: Props) {
  const updateTags = useAppStore(state => state.updateTags);
  const addComment = useAppStore(state => state.addComment);
  const deleteComment = useAppStore(state => state.deleteComment);
  const removeApartment = useAppStore(state => state.removeApartment);

  if (!apartment) return <div className="detail-drawer" />;

  const { qasaData } = apartment;

  return (
    <div className={`detail-drawer ${apartment ? 'open' : ''}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.5rem' }}>Details</h2>
        <button onClick={onClose} className="btn" style={{ fontSize: '1.5rem', background: 'transparent' }}>×</button>
      </div>

      <div className="detail-scroll">
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.25rem', color: 'var(--primary)' }}>
            {new Intl.NumberFormat('en-US').format(qasaData.rent)} {qasaData.currency}
          </h3>
          <p style={{ color: 'var(--text-muted)' }}>
            {qasaData.roomCount} rooms · {qasaData.squareMeters} m² · {qasaData.location.route}, {qasaData.location.locality}
          </p>
          <a 
            href={apartment.qasaUrl} 
            target="_blank" 
            rel="noopener noreferrer"
            style={{ color: 'var(--primary)', fontSize: '0.875rem', textDecoration: 'none', display: 'block', marginTop: '0.5rem' }}
          >
            Open in Qasa ↗
          </a>
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

        <div style={{ marginTop: '3rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
          <button 
            className="btn" 
            style={{ color: 'var(--tag-red)', background: 'transparent', borderColor: 'var(--tag-red)', width: '100%' }}
            onClick={() => {
              if (confirm('Delete this apartment from your list?')) {
                removeApartment(apartment.id);
                onClose();
              }
            }}
          >
            Remove from List
          </button>
        </div>
      </div>
    </div>
  );
}
