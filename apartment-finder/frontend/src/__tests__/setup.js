import '@testing-library/jest-dom';

// Stub Leaflet — it relies on browser APIs not present in jsdom
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }) => children,
  TileLayer: () => null,
  Marker: ({ children }) => children,
  Popup: ({ children }) => children,
  useMap: () => ({ fitBounds: vi.fn() }),
}));

vi.mock('leaflet', () => ({
  default: { icon: vi.fn(() => ({})), divIcon: vi.fn(() => ({})) },
  icon: vi.fn(() => ({})),
  divIcon: vi.fn(() => ({})),
}));
