import '@testing-library/jest-dom';

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => children,
  TileLayer: () => null,
  Marker: ({ children }: { children: React.ReactNode }) => children,
  Popup: ({ children }: { children: React.ReactNode }) => children,
  useMap: () => ({ fitBounds: vi.fn() }),
}));

vi.mock('leaflet', () => ({
  default: { icon: vi.fn(() => ({})), divIcon: vi.fn(() => ({})) },
  icon: vi.fn(() => ({})),
  divIcon: vi.fn(() => ({})),
}));
