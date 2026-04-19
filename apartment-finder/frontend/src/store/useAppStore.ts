import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';
import type {
  SavedApartment,
  SavedSearch,
  QasaListingCard,
  QasaListingData,
  SearchFilters,
  AppDatabase,
  TravelDestination,
} from '../types';
import { DB_KEY, CURRENT_VERSION } from '../utils/db';

export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface AppState {
  apartments: SavedApartment[];
  savedSearches: SavedSearch[];
  searchResults: QasaListingCard[];
  totalResults: number;
  searchLoading: boolean;
  selectedApartmentId: string | null;
  activeTab: 'mylist' | 'search' | 'savedSearches';

  // Actions
  addApartment: (listing: QasaListingData, url: string) => void;
  removeApartment: (id: string) => void;
  updateTags: (id: string, tags: string[]) => void;
  addComment: (id: string, text: string) => void;
  deleteComment: (apartmentId: string, commentId: string) => void;
  saveSearch: (name: string, filters: SearchFilters) => void;
  deleteSearch: (id: string) => void;
  setSearchResults: (results: QasaListingCard[], total: number) => void;
  setSearchLoading: (loading: boolean) => void;
  setSelectedApartment: (id: string | null) => void;
  setActiveTab: (tab: 'mylist' | 'search' | 'savedSearches') => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  importDb: (data: AppDatabase, mode: 'merge' | 'replace') => { imported: number, existing: number };
  toasts: Toast[];
  showToast: (message: string, type?: Toast['type']) => void;
  dismissToast: (id: string) => void;
  searchCity: string;
  setSearchCity: (city: string) => void;
  travelDestinations: TravelDestination[];
  setTravelDestinations: (destinations: TravelDestination[]) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      apartments: [],
      savedSearches: [],
      searchResults: [],
      totalResults: 0,
      searchLoading: false,
      selectedApartmentId: null,
      activeTab: 'mylist',
      toasts: [],
      searchCity: 'stockholm',
      travelDestinations: [
        { id: '1', label: 'Lindholmspiren', lat: 57.70675, lon: 11.94010 },
        { id: '2', label: 'Götaplatsen',    lat: 57.69640, lon: 11.97850 },
      ],

      addApartment: (listing, url) => {
        const { apartments } = get();
        if (apartments.some(a => a.id === listing.id)) {
          return; // Already exists
        }
        const newApartment: SavedApartment = {
          id: listing.id,
          qasaData: listing,
          qasaUrl: url,
          addedAt: new Date().toISOString(),
          tags: [],
          comments: [],
        };
        set({ apartments: [...apartments, newApartment] });
      },

      removeApartment: (id) => {
        set({
          apartments: get().apartments.filter(a => a.id !== id),
          selectedApartmentId: get().selectedApartmentId === id ? null : get().selectedApartmentId,
        });
      },

      updateTags: (id, tags) => {
        set({
          apartments: get().apartments.map(a => 
            a.id === id ? { ...a, tags } : a
          ),
        });
      },

      addComment: (id, text) => {
        const newComment = {
          id: uuidv4(),
          text,
          createdAt: new Date().toISOString(),
        };
        set({
          apartments: get().apartments.map(a => 
            a.id === id ? { ...a, comments: [newComment, ...a.comments] } : a
          ),
        });
      },

      deleteComment: (apartmentId, commentId) => {
        set({
          apartments: get().apartments.map(a => 
            a.id === apartmentId 
              ? { ...a, comments: a.comments.filter(c => c.id !== commentId) } 
              : a
          ),
        });
      },

      saveSearch: (name, filters) => {
        const newSearch: SavedSearch = {
          id: uuidv4(),
          name,
          filters,
          createdAt: new Date().toISOString(),
        };
        set({ savedSearches: [...get().savedSearches, newSearch] });
      },

      deleteSearch: (id) => {
        set({
          savedSearches: get().savedSearches.filter(s => s.id !== id),
        });
      },

      setSearchResults: (results, total) => {
        set({ searchResults: results, totalResults: total, searchLoading: false });
      },

      setSearchLoading: (loading) => {
        set({ searchLoading: loading });
      },

      setSelectedApartment: (id) => {
        set({ selectedApartmentId: id });
      },

      setActiveTab: (tab) => {
        set({ activeTab: tab });
      },

      showToast: (message, type = 'info') => {
        const id = uuidv4();
        set(state => ({ toasts: [...state.toasts, { id, message, type }] }));
        setTimeout(() => {
          set(state => ({ toasts: state.toasts.filter(t => t.id !== id) }));
        }, 4000);
      },

      dismissToast: (id) => {
        set(state => ({ toasts: state.toasts.filter(t => t.id !== id) }));
      },

      setSearchCity: (city) => {
        set({ searchCity: city });
      },

      setTravelDestinations: (destinations) => {
        set({ travelDestinations: destinations });
      },

      importDb: (data, mode) => {
        const currentApartments = get().apartments;
        const currentSearches = get().savedSearches;

        if (mode === 'replace') {
          set({ 
            apartments: data.apartments, 
            savedSearches: data.savedSearches,
            selectedApartmentId: null 
          });
          return { imported: data.apartments.length, existing: 0 };
        } else {
          // Merge logic
          const existingIds = new Set(currentApartments.map(a => a.id));
          const newApartments = data.apartments.filter(a => !existingIds.has(a.id));
          
          set({
            apartments: [...currentApartments, ...newApartments],
            savedSearches: [...currentSearches, ...data.savedSearches.filter(s => 
              !currentSearches.some(cs => cs.id === s.id)
            )],
          });
          return { 
            imported: newApartments.length, 
            existing: data.apartments.length - newApartments.length 
          };
        }
      },
    }),
    {
      name: DB_KEY,
      storage: createJSONStorage(() => localStorage),
      version: CURRENT_VERSION,
      partialize: (state) => ({
        apartments: state.apartments,
        savedSearches: state.savedSearches,
        activeTab: state.activeTab,
        selectedApartmentId: state.selectedApartmentId,
        travelDestinations: state.travelDestinations,
      }),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      migrate: (persistedState: any, version: number) => {
        if (version < CURRENT_VERSION) {
          // Future migrations logic
        }
        return persistedState as AppState;
      },
    }
  )
);
