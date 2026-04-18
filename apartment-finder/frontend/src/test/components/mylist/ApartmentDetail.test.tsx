import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ApartmentDetail } from '../../../components/mylist/ApartmentDetail';
import { SavedApartment } from '../../../types';

const mockApt: SavedApartment = {
  id: '1',
  qasaUrl: 'url1',
  addedAt: '2026-01-01',
  tags: [],
  comments: [],
  qasaData: {
    id: '1',
    description: 'Beautiful place',
    uploads: [],
    location: { locality: 'Gothenburg', route: 'Main St' },
  } as any,
};

describe('ApartmentDetail', () => {
  it('renders nothing when apartment is null', () => {
    const { container } = render(<ApartmentDetail apartment={null} onClose={() => {}} />);
    expect(container.querySelector('.detail-drawer.open')).toBeNull();
  });

  it('renders apartment details when present', () => {
    render(<ApartmentDetail apartment={mockApt} onClose={() => {}} />);
    expect(screen.getByText('Beautiful place')).toBeDefined();
    expect(screen.getByText('Main St, Gothenburg')).toBeDefined();
  });
});
