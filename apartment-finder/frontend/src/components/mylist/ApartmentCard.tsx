import type { SavedApartment } from '../../types';
import { getTagColor } from '../../utils/pinColor';

interface Props {
  apartment: SavedApartment;
  selected: boolean;
  onClick: () => void;
}

export function ApartmentCard({ apartment, selected, onClick }: Props) {
  const { qasaData, tags } = apartment;
  const primaryImage = qasaData.uploads.find(u => u.metadata.primary)?.url || qasaData.uploads[0]?.url;

  return (
    <div
      role="listitem"
      data-apt-id={apartment.id}
      className={`apartment-card ${selected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <img 
        src={primaryImage} 
        alt={qasaData.location.route} 
        className="card-img"
        onError={(e) => (e.currentTarget.src = 'https://via.placeholder.com/100?text=No+Image')}
      />
      
      <div className="card-info">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <h3 style={{ fontSize: '1.125rem' }}>
            {new Intl.NumberFormat('en-US').format(qasaData.rent)} {qasaData.currency}
          </h3>
          <div style={{ display: 'flex', gap: '4px' }}>
            {tags.map(tag => (
              <span 
                key={tag} 
                className="tag" 
                style={{ backgroundColor: getTagColor(tag) }}
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
        
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '2px' }}>
          {qasaData.roomCount} rooms · {qasaData.squareMeters} m²
        </p>
        
        <p style={{ fontSize: '0.875rem', marginTop: '4px' }}>
          {qasaData.location.locality}{qasaData.location.route ? `, ${qasaData.location.route}` : ''}
        </p>
      </div>
    </div>
  );
}
