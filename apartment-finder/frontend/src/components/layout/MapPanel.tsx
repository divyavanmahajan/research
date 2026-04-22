import { useState } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useAppStore } from '../../store/useAppStore';
import { getTagColor } from '../../utils/pinColor';
import { useEffect } from 'react';

// Fix for default Leaflet icon not showing in Vite/React
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

function formatRent(rent: number): string {
  if (rent >= 1000) return `${Math.round(rent / 1000)}k`;
  return String(rent);
}

function createCircleMarker(color: string, hollow: boolean = false, selected: boolean = false) {
  const size = selected ? 32 : 24;
  const r = selected ? 10 : 8;
  const c = size / 2;

  return L.divIcon({
    className: 'custom-pin',
    html: `
      <div style="position:relative;width:${size}px;height:${size}px">
        ${selected ? `<div class="pin-pulse-ring" style="background:${color}"></div>` : ''}
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="${c}" cy="${c}" r="${r}" fill="${hollow ? 'transparent' : color}" stroke="${color}" stroke-width="3"/>
          ${!hollow ? `<circle cx="${c}" cy="${c}" r="3" fill="white"/>` : ''}
        </svg>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [c, c],
  });
}

function MapBounds() {
  const map = useMap();
  const apartments = useAppStore((state) => state.apartments);
  const searchResults = useAppStore((state) => state.searchResults);
  const activeTab = useAppStore((state) => state.activeTab);

  useEffect(() => {
    const pins = activeTab === 'search'
      ? searchResults.map(r => [r.location.point.lat, r.location.point.lon] as [number, number])
      : apartments
          .filter(a => a.qasaData.location.latitude != null && a.qasaData.location.longitude != null)
          .map(a => [a.qasaData.location.latitude, a.qasaData.location.longitude] as [number, number]);

    if (pins.length > 0) {
      const bounds = L.latLngBounds(pins);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [apartments, searchResults, activeTab, map]);

  return null;
}

const CITY_CENTERS: Record<string, [number, number]> = {
  stockholm: [59.3293, 18.0686],
  gothenburg: [57.7089, 11.9746],
  malmo: [55.6050, 13.0038],
  malmö: [55.6050, 13.0038],
  uppsala: [59.8586, 17.6389],
  västerås: [59.6099, 16.5448],
  örebro: [59.2741, 15.2066],
  linköping: [58.4108, 15.6214],
  helsingborg: [56.0467, 12.6945],
  jönköping: [57.7826, 14.1618],
};

function MapCityCenter() {
  const map = useMap();
  const searchCity = useAppStore(state => state.searchCity);
  const searchResults = useAppStore(state => state.searchResults);
  const activeTab = useAppStore(state => state.activeTab);

  useEffect(() => {
    if (activeTab === 'search' && searchResults.length === 0) {
      const key = searchCity.toLowerCase().trim();
      const center = CITY_CENTERS[key];
      if (center) map.setView(center, 12, { animate: true });
    }
  }, [searchCity]);

  return null;
}

function MapController() {
  const map = useMap();
  const selectedId = useAppStore(state => state.selectedApartmentId);
  const apartments = useAppStore(state => state.apartments);
  const searchResults = useAppStore(state => state.searchResults);

  useEffect(() => {
    if (!selectedId) return;

    const apt = apartments.find(a => a.id === selectedId);
    const result = searchResults.find(r => r.id === selectedId);

    const point = apt && apt.qasaData.location.latitude != null && apt.qasaData.location.longitude != null
      ? [apt.qasaData.location.latitude, apt.qasaData.location.longitude] as [number, number]
      : result ? [result.location.point.lat, result.location.point.lon] as [number, number] : null;

    if (point) {
      map.flyTo(point, 14, { duration: 1 });
    }
  }, [selectedId, apartments, searchResults, map]);

  return null;
}

export function MapPanel() {
  const apartments = useAppStore((state) => state.apartments);
  const searchResults = useAppStore((state) => state.searchResults);
  const activeTab = useAppStore((state) => state.activeTab);
  const selectedId = useAppStore((state) => state.selectedApartmentId);
  const setSelectedApartment = useAppStore((state) => state.setSelectedApartment);

  const [showRentLabels, setShowRentLabels] = useState(false);

  const defaultPosition: [number, number] = [57.7089, 11.9746]; // Gothenburg

  return (
    <div className="map-panel">
      <div className="map-controls">
        <button
          className={`btn map-control-btn ${showRentLabels ? 'active' : ''}`}
          onClick={() => setShowRentLabels(v => !v)}
        >
          {showRentLabels ? 'Hide rents' : 'Show rents'}
        </button>
      </div>

      <MapContainer
        center={defaultPosition}
        zoom={12}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapController />
        <MapCityCenter />

        {/* Saved Apartments */}
        {apartments.filter(apt => apt.qasaData.location.latitude != null && apt.qasaData.location.longitude != null).map((apt) => {
          const selected = apt.id === selectedId;
          const color = getTagColor(apt.tags[0] || '');
          return (
            <Marker
              key={apt.id}
              position={[apt.qasaData.location.latitude, apt.qasaData.location.longitude]}
              icon={createCircleMarker(color, false, selected)}
              zIndexOffset={selected ? 1000 : 0}
              eventHandlers={{ click: () => setSelectedApartment(apt.id) }}
            >
              {showRentLabels && (
                <Tooltip permanent direction="top" offset={[0, selected ? -16 : -12]} className="rent-pill">
                  {formatRent(apt.qasaData.rent)} {apt.qasaData.currency}
                </Tooltip>
              )}
            </Marker>
          );
        })}

        {/* Search Results */}
        {activeTab === 'search' && searchResults.map((result) => {
          const selected = result.id === selectedId;
          return (
            <Marker
              key={result.id}
              position={[result.location.point.lat, result.location.point.lon]}
              icon={createCircleMarker('#f97316', true, selected)}
              zIndexOffset={selected ? 1000 : 0}
              eventHandlers={{ click: () => setSelectedApartment(result.id) }}
            >
              {showRentLabels && (
                <Tooltip permanent direction="top" offset={[0, selected ? -16 : -12]} className="rent-pill">
                  {formatRent(result.rent)} {result.currency}
                </Tooltip>
              )}
            </Marker>
          );
        })}

        <MapBounds />
      </MapContainer>
    </div>
  );
}
