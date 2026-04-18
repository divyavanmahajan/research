import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from '../../store/useAppStore';

describe('useAppStore', () => {
  beforeEach(() => {
    // Reset state manually if needed, though Zustand store is persistent
    // For testing, we can use the setState method to clear it
    useAppStore.setState({
      apartments: [],
      savedSearches: [],
      searchResults: [],
      totalResults: 0,
      searchLoading: false,
      selectedApartmentId: null,
      activeTab: 'mylist',
    });
  });

  it('addApartment adds a new listing', () => {
    const mockListing = { id: '1', rent: 1000 } as any;
    useAppStore.getState().addApartment(mockListing, 'url1');
    
    const state = useAppStore.getState();
    expect(state.apartments).toHaveLength(1);
    expect(state.apartments[0].id).toBe('1');
    expect(state.apartments[0].qasaUrl).toBe('url1');
  });

  it('addApartment ignores duplicates', () => {
    const mockListing = { id: '1', rent: 1000 } as any;
    useAppStore.getState().addApartment(mockListing, 'url1');
    useAppStore.getState().addApartment(mockListing, 'url1');
    
    expect(useAppStore.getState().apartments).toHaveLength(1);
  });

  it('removeApartment removes listing by id', () => {
    const mockListing = { id: '1', rent: 1000 } as any;
    useAppStore.getState().addApartment(mockListing, 'url1');
    useAppStore.getState().removeApartment('1');
    
    expect(useAppStore.getState().apartments).toHaveLength(0);
  });

  it('addComment adds a comment to the correct apartment', () => {
    const mockListing = { id: '1', rent: 1000 } as any;
    useAppStore.getState().addApartment(mockListing, 'url1');
    useAppStore.getState().addComment('1', 'Cool place');
    
    const apartment = useAppStore.getState().apartments[0];
    expect(apartment.comments).toHaveLength(1);
    expect(apartment.comments[0].text).toBe('Cool place');
  });

  it('updateTags changes tags for an apartment', () => {
    const mockListing = { id: '1', rent: 1000 } as any;
    useAppStore.getState().addApartment(mockListing, 'url1');
    useAppStore.getState().updateTags('1', ['tag1', 'tag2']);
    
    expect(useAppStore.getState().apartments[0].tags).toEqual(['tag1', 'tag2']);
  });

  it('saveSearch adds to saved searches', () => {
    const filters = { areaIdentifier: 'test' } as any;
    useAppStore.getState().saveSearch('My Search', filters);
    
    expect(useAppStore.getState().savedSearches).toHaveLength(1);
    expect(useAppStore.getState().savedSearches[0].name).toBe('My Search');
  });
});
