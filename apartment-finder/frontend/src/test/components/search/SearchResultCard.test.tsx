import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SearchResultCard } from '../../../components/search/SearchResultCard';
import type { QasaListingCard } from '../../../types';

const mockResult: QasaListingCard = {
  id: '100',
  rent: 12000,
  currency: 'SEK',
  squareMeters: 60,
  roomCount: 3,
  description: '',
  publishedAt: '2026-01-01',
  publishedOrBumpedAt: '2026-01-01',
  location: { id: '1', locality: 'Stockholm', route: 'Sveavägen', point: { lat: 59.3, lon: 18.0 } },
  uploads: [{ id: 'u1', url: 'img.jpg', type: 'image', metadata: { primary: true, order: 1 } }],
  furnished: false,
  firstHand: false,
};

describe('SearchResultCard', () => {
  it('renders rent and dimensions', () => {
    render(<SearchResultCard result={mockResult} selected={false} isSaved={false} onClick={() => {}} onAdd={() => {}} />);
    expect(screen.getByText('12,000 SEK')).toBeDefined();
    expect(screen.getByText('3 rooms · 60 m²')).toBeDefined();
  });

  it('shows Add button when not saved', () => {
    render(<SearchResultCard result={mockResult} selected={false} isSaved={false} onClick={() => {}} onAdd={() => {}} />);
    expect(screen.getByRole('button', { name: 'Add' })).toBeDefined();
  });

  it('shows disabled Saved button when already saved', () => {
    render(<SearchResultCard result={mockResult} selected={false} isSaved={true} onClick={() => {}} onAdd={() => {}} />);
    const btn = screen.getByRole('button', { name: 'Saved' }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('calls onAdd when Add is clicked', () => {
    const onAdd = vi.fn();
    render(<SearchResultCard result={mockResult} selected={false} isSaved={false} onClick={() => {}} onAdd={onAdd} />);
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    expect(onAdd).toHaveBeenCalledTimes(1);
  });

  it('does not call onAdd when Saved button is clicked', () => {
    const onAdd = vi.fn();
    render(<SearchResultCard result={mockResult} selected={false} isSaved={true} onClick={() => {}} onAdd={onAdd} />);
    fireEvent.click(screen.getByRole('button', { name: 'Saved' }));
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('applies selected class when selected', () => {
    const { container } = render(<SearchResultCard result={mockResult} selected={true} isSaved={false} onClick={() => {}} onAdd={() => {}} />);
    expect(container.firstChild).toHaveClass('selected');
  });
});
