import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ApartmentDetail } from '../../../components/mylist/ApartmentDetail';
import type { SavedApartment } from '../../../types';

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
  it('renders apartment details', () => {
    render(<ApartmentDetail apartment={mockApt} onClose={() => {}} />);
    expect(screen.getByText('Beautiful place')).toBeDefined();
    expect(screen.getByText(/Main St, Gothenburg/)).toBeDefined();
  });

  it('renders the panel with header', () => {
    const { container } = render(<ApartmentDetail apartment={mockApt} onClose={() => {}} />);
    expect(container.querySelector('.detail-panel')).toBeDefined();
    expect(screen.getByText('Details')).toBeDefined();
  });
});
