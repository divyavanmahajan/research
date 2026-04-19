import { useState } from 'react';
import type { ApartmentComment } from '../../types';

interface Props {
  comments: ApartmentComment[];
  onAdd: (text: string) => void;
  onDelete: (id: string) => void;
}

export function CommentThread({ comments, onAdd, onDelete }: Props) {
  const [text, setText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    onAdd(text.trim());
    setText('');
  };

  return (
    <div className="comment-thread" style={{ marginTop: '1.5rem' }}>
      <h4 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>Comments</h4>
      
      <form role="form" onSubmit={handleSubmit} style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            className="input-field"
            placeholder="Add a comment..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button type="submit" className="btn btn-primary">Add</button>
        </div>
      </form>

      <div className="comments-list">
        {comments.map(comment => (
          <div 
            key={comment.id} 
            className="comment-item" 
            style={{ 
              padding: '0.75rem', 
              background: 'var(--bg-app)', 
              borderRadius: '0.5rem',
              marginBottom: '0.5rem',
              position: 'relative'
            }}
          >
            <p style={{ fontSize: '0.875rem', paddingRight: '2rem' }}>{comment.text}</p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              {new Date(comment.createdAt).toLocaleString()}
            </p>
            <button
              aria-label="delete"
              onClick={() => onDelete(comment.id)}
              style={{
                position: 'absolute',
                top: '0.5rem',
                right: '0.5rem',
                border: 'none',
                background: 'transparent',
                color: 'var(--tag-red)',
                cursor: 'pointer',
                fontSize: '1rem'
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
