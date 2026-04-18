export type Priority = 'must_see' | 'nice' | 'skip' | 'unranked';

export type Status = 'new' | 'contacted' | 'viewing' | 'applied' | 'rejected';

export interface Apartment {
  id: string;
  sourceUrl: string;
  addedAt: string;
  updatedAt: string;
  title: string;
  address: string;
  city: string;
  lat: number | null;
  lng: number | null;
  price: number;
  deposit: number | null;
  size: number;
  rooms: number;
  floor: string | null;
  availableFrom: string | null;
  photos: string[];
  description: string;
  priority: Priority;
  status: Status;
  notes: string;
}

export interface ListingPreview {
  title: string;
  address: string;
  city: string;
  lat: number | null;
  lng: number | null;
  price: number;
  deposit: number | null;
  size: number;
  rooms: number;
  floor: string | null;
  availableFrom: string | null;
  photos: string[];
  description: string;
  sourceUrl: string;
}

export interface SearchResult {
  title: string;
  address: string;
  city: string;
  price: number;
  size: number;
  rooms: number;
  photo: string | null;
  sourceUrl: string;
}
