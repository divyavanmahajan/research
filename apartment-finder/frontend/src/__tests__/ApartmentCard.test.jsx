import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import ApartmentCard from '../components/ApartmentCard';

const apt = {
  id: 'id-1',
  title: 'Cozy Studio',
  address: 'Kungsgatan 5',
  city: 'Stockholm',
  price: 9500,
  size: 30,
  rooms: 1,
  photos: ['https://cdn.qasa.se/photo1.jpg'],
  priority: 'must_see',
  status: 'new',
  addedAt: '2026-04-18T10:00:00Z',
};

function renderCard(props = {}) {
  return render(
    <MemoryRouter>
      <ApartmentCard apartment={{ ...apt, ...props }} />
    </MemoryRouter>
  );
}

describe('ApartmentCard', () => {
  it('renders address', () => {
    renderCard();
    expect(screen.getByText(/Kungsgatan 5/i)).toBeInTheDocument();
  });

  it('renders formatted price', () => {
    renderCard();
    expect(screen.getByText(/9\s*500/)).toBeInTheDocument();
  });

  it('renders size and rooms', () => {
    renderCard();
    expect(screen.getByText(/30 m²/)).toBeInTheDocument();
    expect(screen.getByText(/1 rum/)).toBeInTheDocument();
  });

  it('renders must_see priority badge', () => {
    renderCard({ priority: 'must_see' });
    expect(screen.getByText(/must see/i)).toBeInTheDocument();
  });

  it('renders nice priority badge', () => {
    renderCard({ priority: 'nice' });
    expect(screen.getByText(/nice/i)).toBeInTheDocument();
  });

  it('renders skip priority badge', () => {
    renderCard({ priority: 'skip' });
    expect(screen.getByText(/skip/i)).toBeInTheDocument();
  });

  it('renders photo thumbnail when photos present', () => {
    renderCard();
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', 'https://cdn.qasa.se/photo1.jpg');
  });

  it('renders placeholder when no photos', () => {
    renderCard({ photos: [] });
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByTestId('no-photo')).toBeInTheDocument();
  });

  it('links to detail view', () => {
    renderCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/apartment/id-1');
  });
});
