import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import InvestigateView from '../views/InvestigateView';

vi.mock('../db', () => ({
  getAll: vi.fn().mockResolvedValue([]),
  put: vi.fn().mockResolvedValue(undefined),
}));

const mockListing = {
  title: 'Scraped Apartment',
  address: 'Testgatan 5',
  city: 'Stockholm',
  lat: 59.33,
  lng: 18.06,
  price: 11000,
  deposit: null,
  size: 45,
  rooms: 2,
  floor: null,
  availableFrom: null,
  photos: [],
  description: 'Test',
  sourceUrl: 'https://qasa.se/homes/abc',
};

const mockSearchResults = {
  results: [
    { title: 'Result 1', address: 'Addr 1', price: 9000, size: 35, rooms: 1, photo: null, sourceUrl: 'https://qasa.se/homes/r1' },
  ],
};

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn());
});

function renderView() {
  return render(<MemoryRouter><InvestigateView /></MemoryRouter>);
}

describe('InvestigateView — URL tab', () => {
  it('renders the URL input tab by default', () => {
    renderView();
    expect(screen.getByPlaceholderText(/qasa\.se/i)).toBeInTheDocument();
  });

  it('shows scraped preview after submitting a URL', async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => mockListing });
    renderView();
    await userEvent.type(screen.getByPlaceholderText(/qasa\.se/i), 'https://qasa.se/homes/abc');
    await userEvent.click(screen.getByRole('button', { name: /fetch/i }));
    expect(await screen.findByText(/Scraped Apartment/i)).toBeInTheDocument();
  });

  it('shows error message when scrape fails', async () => {
    fetch.mockResolvedValueOnce({ ok: false, json: async () => ({ error: 'Not found' }) });
    renderView();
    await userEvent.type(screen.getByPlaceholderText(/qasa\.se/i), 'https://qasa.se/homes/bad');
    await userEvent.click(screen.getByRole('button', { name: /fetch/i }));
    expect(await screen.findByText(/not found/i)).toBeInTheDocument();
  });

  it('adds listing to db when Add to My List is clicked', async () => {
    const { put } = await import('../db');
    fetch.mockResolvedValueOnce({ ok: true, json: async () => mockListing });
    renderView();
    await userEvent.type(screen.getByPlaceholderText(/qasa\.se/i), 'https://qasa.se/homes/abc');
    await userEvent.click(screen.getByRole('button', { name: /fetch/i }));
    await screen.findByText(/Scraped Apartment/i);
    await userEvent.click(screen.getByRole('button', { name: /add to my list/i }));
    expect(put).toHaveBeenCalled();
  });
});

describe('InvestigateView — Search tab', () => {
  it('switches to search tab', async () => {
    renderView();
    await userEvent.click(screen.getByRole('tab', { name: /search/i }));
    expect(screen.getByPlaceholderText(/city/i)).toBeInTheDocument();
  });

  it('shows search results', async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => mockSearchResults });
    renderView();
    await userEvent.click(screen.getByRole('tab', { name: /search/i }));
    await userEvent.type(screen.getByPlaceholderText(/city/i), 'Stockholm');
    await userEvent.click(screen.getByRole('button', { name: /search/i }));
    expect(await screen.findByText(/Result 1/i)).toBeInTheDocument();
  });
});
