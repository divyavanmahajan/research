import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ListView from '../views/ListView';

vi.mock('../db', () => ({
  getAll: vi.fn(),
}));

import { getAll } from '../db';

const apartments = [
  { id: '1', title: 'Apt A', address: 'Street A', city: 'Stockholm', price: 10000, size: 40, rooms: 2, photos: [], priority: 'must_see', status: 'new', addedAt: '2026-04-18T10:00:00Z' },
  { id: '2', title: 'Apt B', address: 'Street B', city: 'Stockholm', price: 8000,  size: 30, rooms: 1, photos: [], priority: 'nice',     status: 'new', addedAt: '2026-04-17T10:00:00Z' },
  { id: '3', title: 'Apt C', address: 'Street C', city: 'Göteborg',  price: 7000,  size: 25, rooms: 1, photos: [], priority: 'skip',     status: 'new', addedAt: '2026-04-16T10:00:00Z' },
];

function renderList() {
  return render(<MemoryRouter><ListView /></MemoryRouter>);
}

beforeEach(() => {
  getAll.mockResolvedValue(apartments);
});

describe('ListView', () => {
  it('renders all apartments on load', async () => {
    renderList();
    expect(await screen.findByText(/Street A/i)).toBeInTheDocument();
    expect(await screen.findByText(/Street B/i)).toBeInTheDocument();
    expect(await screen.findByText(/Street C/i)).toBeInTheDocument();
  });

  it('shows empty state when no apartments exist', async () => {
    getAll.mockResolvedValue([]);
    renderList();
    expect(await screen.findByText(/no apartments/i)).toBeInTheDocument();
  });

  it('filters to must_see when that filter is selected', async () => {
    renderList();
    await screen.findByText(/Street A/i);
    await userEvent.click(screen.getByRole('button', { name: /must see/i }));
    expect(screen.getByText(/Street A/i)).toBeInTheDocument();
    expect(screen.queryByText(/Street B/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Street C/i)).not.toBeInTheDocument();
  });

  it('filters to nice when that filter is selected', async () => {
    renderList();
    await screen.findByText(/Street B/i);
    await userEvent.click(screen.getByRole('button', { name: /^nice$/i }));
    expect(screen.queryByText(/Street A/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Street B/i)).toBeInTheDocument();
  });

  it('shows all apartments when All filter is selected', async () => {
    renderList();
    await screen.findByText(/Street A/i);
    await userEvent.click(screen.getByRole('button', { name: /must see/i }));
    await userEvent.click(screen.getByRole('button', { name: /^all$/i }));
    expect(screen.getByText(/Street A/i)).toBeInTheDocument();
    expect(screen.getByText(/Street B/i)).toBeInTheDocument();
    expect(screen.getByText(/Street C/i)).toBeInTheDocument();
  });
});
