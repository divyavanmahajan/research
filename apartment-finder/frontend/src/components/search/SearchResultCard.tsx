import { QasaListingCard } from '../../types';

interface Props {
  result: QasaListingCard;
  selected: boolean;
  onClick: () => void;
  onAdd: () => void;
  isSaved: boolean;
}

export function SearchResultCard({ result, selected, onClick, onAdd, isSaved }: Props) {
  const primaryImage = result.uploads[0]?.url;

  return (
    <div 
      className={`apartment-card ${selected ? 'selected' : ''}`}
      onClick={onClick}
      style={{ position: 'relative' }}
    >
      <img 
        src={primaryImage} 
        alt={result.location.route} 
        className="card-img"
        onError={(e) => (e.currentTarget.src = 'https://via.placeholder.com/100?text=No+Image')}
      />
      
      <div className="card-info">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <h3 style={{ fontSize: '1.125rem' }}>
            {new Intl.NumberFormat('en-US').format(result.rent)} {result.currency}
          </h3>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (!isSaved) onAdd();
            }}
            className="btn"
            style={{
              padding: '0.25rem 0.5rem',
              fontSize: '0.75rem',
              backgroundColor: isSaved ? 'var(--tag-green)' : 'var(--primary)',
              color: 'white'
            }}
            disabled={isSaved}
          >
            {isSaved ? 'Saved' : 'Add'}
          </button>
        </div>
        
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '2px' }}>
          {result.roomCount} rooms · {result.squareMeters} m²
        </p>
        
        <p style={{ fontSize: '0.875rem', marginTop: '4px' }}>
          {result.location.locality}, {result.location.route}
        </p>
      </div>
    </div>
  );
}
