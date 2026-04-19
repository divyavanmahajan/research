import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SearchPanel } from '../../../components/search/SearchPanel';

vi.mock('../../../store/useAppStore', () => ({
  useAppStore: (selector: Function) => selector({
    searchLoading: false,
    setSearchResults: vi.fn(),
    setSearchLoading: vi.fn(),
    saveSearch: vi.fn(),
    showToast: vi.fn(),
    setSearchCity: vi.fn(),
  }),
}));

vi.mock('../../../api/qasaApi', () => ({
  searchListings: vi.fn(),
}));

describe('SearchPanel', () => {
  it('renders the area input with default value', () => {
    render(<SearchPanel />);
    const input = screen.getByPlaceholderText('e.g. stockholm, gothenburg') as HTMLInputElement;
    expect(input).toBeDefined();
    expect(input.value).toBe('stockholm');
  });

  it('renders the Search button', () => {
    render(<SearchPanel />);
    expect(screen.getByRole('button', { name: 'Search' })).toBeDefined();
  });

  it('renders the Save button', () => {
    render(<SearchPanel />);
    expect(screen.getByRole('button', { name: 'Save' })).toBeDefined();
  });

  it('renders rent filter inputs', () => {
    render(<SearchPanel />);
    expect(screen.getByText('Min Rent')).toBeDefined();
    expect(screen.getByText('Max Rent')).toBeDefined();
  });
});
