import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CommentThread } from '../../../components/comments/CommentThread';
import type { ApartmentComment } from '../../../types';

const mockComments: ApartmentComment[] = [
  { id: 'c1', text: 'Nice place', createdAt: '2026-01-01T10:00:00Z' },
  { id: 'c2', text: 'Too expensive', createdAt: '2026-01-01T11:00:00Z' },
];

describe('CommentThread', () => {
  it('renders comments list', () => {
    render(<CommentThread comments={mockComments} onAdd={() => {}} onDelete={() => {}} />);
    expect(screen.getByText('Nice place')).toBeDefined();
    expect(screen.getByText('Too expensive')).toBeDefined();
  });

  it('calls onAdd when form submitted', () => {
    const handleAdd = vi.fn();
    render(<CommentThread comments={[]} onAdd={handleAdd} onDelete={() => {}} />);
    
    const input = screen.getByPlaceholderText('Add a comment...');
    fireEvent.change(input, { target: { value: 'New comment' } });
    fireEvent.submit(screen.getByRole('form'));
    
    expect(handleAdd).toHaveBeenCalledWith('New comment');
  });

  it('calls onDelete when delete button clicked', () => {
    const handleDelete = vi.fn();
    render(<CommentThread comments={mockComments} onAdd={() => {}} onDelete={handleDelete} />);
    
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    fireEvent.click(deleteButtons[0]);
    
    expect(handleDelete).toHaveBeenCalledWith('c1');
  });
});
