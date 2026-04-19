import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SavedSearches } from '../../../components/savedSearches/SavedSearches';

vi.mock('../../../store/useAppStore', () => ({
  useAppStore: (selector: Function) => selector({
    savedSearches: [],
    deleteSearch: vi.fn(),
    setSearchResults: vi.fn(),
    setSearchLoading: vi.fn(),
    setActiveTab: vi.fn(),
    showToast: vi.fn(),
  }),
}));

vi.mock('../../../api/qasaApi', () => ({
  searchListings: vi.fn(),
}));

describe('SavedSearches', () => {
  it('shows empty state when no searches are saved', () => {
    render(<SavedSearches />);
    expect(screen.getByText(/No saved searches yet/)).toBeDefined();
  });
});
