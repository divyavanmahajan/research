import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ApartmentCard } from '../../../components/mylist/ApartmentCard';
import { SavedApartment } from '../../../types';

const mockApt: SavedApartment = {
  id: '1',
  qasaUrl: 'url1',
  addedAt: '2026-01-01',
  tags: ['interested'],
  comments: [],
  qasaData: {
    id: '1',
    rent: 10000,
    currency: 'SEK',
    roomCount: 2,
    squareMeters: 50,
    location: { locality: 'Gothenburg', route: 'Avenyn' },
    uploads: [{ url: 'img1.jpg', metadata: { primary: true } }],
  } as any,
};

describe('ApartmentCard', () => {
  it('renders apartment info correctly', () => {
    render(<ApartmentCard apartment={mockApt} selected={false} onClick={() => {}} />);
    
    expect(screen.getByText('2 rooms · 50 m²')).toBeDefined();
    expect(screen.getByText('10,000 SEK')).toBeDefined();
    expect(screen.getByText('Gothenburg, Avenyn')).toBeDefined();
    expect(screen.getByText('interested')).toBeDefined();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<ApartmentCard apartment={mockApt} selected={false} onClick={handleClick} />);
    
    fireEvent.click(screen.getByRole('listitem'));
    expect(handleClick).toHaveBeenCalled();
  });

  it('applies selected class when selected is true', () => {
    const { container } = render(<ApartmentCard apartment={mockApt} selected={true} onClick={() => {}} />);
    expect(container.firstChild).toHaveClass('selected');
  });
});
