import { getTagColor } from '../../utils/pinColor';

interface Props {
  tags: string[];
  onChange: (tags: string[]) => void;
}

const QUICK_TAGS = ['favourite', 'interested', 'applied', 'visited', 'rejected'];

export function TagInput({ tags, onChange }: Props) {
  const toggleTag = (tag: string) => {
    if (tags.includes(tag)) {
      onChange(tags.filter(t => t !== tag));
    } else {
      onChange([...tags, tag]);
    }
  };

  return (
    <div className="tag-input" style={{ marginTop: '1rem' }}>
      <h4 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>Tags</h4>
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
        {QUICK_TAGS.map(tag => {
          const isActive = tags.includes(tag);
          return (
            <button
              key={tag}
              onClick={() => toggleTag(tag)}
              className="btn"
              style={{
                fontSize: '0.75rem',
                backgroundColor: isActive ? getTagColor(tag) : 'transparent',
                color: isActive ? 'white' : 'var(--text-muted)',
                borderColor: getTagColor(tag),
                padding: '0.25rem 0.75rem',
                borderRadius: '9999px'
              }}
            >
              {tag}
            </button>
          );
        })}
      </div>

      {tags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', width: '100%' }}>Active:</p>
          {tags.map(tag => (
            <span
              key={tag}
              className="tag"
              onClick={() => toggleTag(tag)}
              style={{ backgroundColor: getTagColor(tag), cursor: 'pointer' }}
            >
              {tag} ×
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
