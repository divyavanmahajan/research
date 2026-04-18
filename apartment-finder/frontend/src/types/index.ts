/**
 * Core Data Models for Apartment Finder.
 * Based on Spec v1.0 (§3)
 */

export interface SavedApartment {
  id: string;                  // Qasa home ID (numeric string)
  qasaData: QasaListingData;   // Full HomeView response, cached
  qasaUrl: string;             // Canonical Qasa URL
  addedAt: string;             // ISO 8601 timestamp
  tags: string[];              // freeform, ordered by insertion
  comments: ApartmentComment[];
}

export interface ApartmentComment {
  id: string;       // uuid v4
  text: string;
  createdAt: string; // ISO 8601
}

export interface QasaListingData {
  id: string;
  rent: number;
  currency: string;
  squareMeters: number;
  roomCount: number;
  floor: number | null;
  buildingFloors: number | null;
  tenureType: string;         // "condominium" | "rental"
  rentalType: string;         // "long_term" | "short_term" | "vacation"
  shared: boolean;
  description: string;
  publishedAt: string;
  status: string;
  location: QasaLocation;
  uploads: QasaUpload[];
  duration: QasaDuration;
  traits: QasaTrait[];
  landlord: QasaLandlord;
  homeTemplates: QasaHomeTemplate[];
}

export interface QasaLocation {
  id: string;
  latitude: number;
  longitude: number;
  locality: string;
  route: string;
  streetNumber: string | null;
  postalCode: string;
  countryCode: string;
  country: string;
  point?: {
    lat: number;
    lon: number;
  };
}

export interface QasaUpload {
  id: string;
  url: string;
  type: string;
  metadata: { primary: boolean; order: number };
}

export interface QasaDuration {
  startOptimal: string | null;
  endOptimal: string | null;
  startAsap: boolean;
  endUfn: boolean;
  possibilityOfExtension: boolean;
}

export interface QasaTrait {
  type: string;
  detail: string | null;
}

export interface QasaLandlord {
  uid: string;
  firstName: string;
  professional: boolean;
  premium: boolean;
}

export interface QasaHomeTemplate {
  id: string;
  squareMeters: number;
  roomCount: number;
  rent: number;
  type: string;
  description: string;
}

export interface SavedSearch {
  id: string;        // uuid v4
  name: string;
  filters: SearchFilters;
  createdAt: string;
}

export interface SearchFilters {
  areaIdentifier: string;
  minRoomCount?: number;
  maxRoomCount?: number;
  minRent?: number;
  maxRent?: number;
  minSquareMeters?: number;
  maxSquareMeters?: number;
  currency: string;
  markets: string[];
  furnished?: boolean;
  petsAllowed?: boolean;
  homeType?: string;
  firstHand?: boolean;
  studentHome?: boolean;
  seniorHome?: boolean;
  corporateHome?: boolean;
  sortBy: "published_or_bumped_at" | "rent";
  sortDirection: "ascending" | "descending";
}

export interface AppDatabase {
  version: 1;
  exportedAt: string | null;
  apartments: SavedApartment[];
  savedSearches: SavedSearch[];
}

export interface SearchResult {
  totalCount: number;
  pagesCount: number;
  results: QasaListingCard[];
}

/**
 * Partial listing data returned by the /api/search endpoint (HomeSearch nodes)
 */
export interface QasaListingCard {
  id: string;
  rent: number;
  currency: string;
  squareMeters: number;
  roomCount: number;
  description: string;
  publishedAt: string;
  publishedOrBumpedAt: string;
  location: {
    id: string | number;
    locality: string;
    route: string;
    point: { lat: number; lon: number };
  };
  uploads: QasaUpload[];
  furnished: boolean;
  firstHand: boolean;
  // ... other fields as needed
}
