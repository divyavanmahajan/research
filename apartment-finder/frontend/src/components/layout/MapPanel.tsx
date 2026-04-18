import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet';
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

/**
 * Creates an SVG-based circle marker for better styling and performance.
 */
function createCircleMarker(color: string, hollow: boolean = false) {
  return L.divIcon({
    className: 'custom-pin',
    html: `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="8" fill="${hollow ? 'transparent' : color}" stroke="${color}" stroke-width="3" />
        ${!hollow ? '<circle cx="12" cy="12" r="3" fill="white" />' : ''}
      </svg>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
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
      : apartments.map(a => [a.qasaData.location.latitude, a.qasaData.location.longitude] as [number, number]);

    if (pins.length > 0) {
      const bounds = L.latLngBounds(pins);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [apartments, searchResults, activeTab, map]);

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
    
    const point = apt 
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
  const setSelectedApartment = useAppStore((state) => state.setSelectedApartment);

  const defaultPosition: [number, number] = [57.7089, 11.9746]; // Gothenburg

  return (
    <div className="map-panel">
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
        {/* Saved Apartments */}
        {apartments.map((apt) => (
          <Marker
            key={apt.id}
            position={[apt.qasaData.location.latitude, apt.qasaData.location.longitude]}
            icon={createCircleMarker(getTagColor(apt.tags[0] || ''))}
            eventHandlers={{
              click: () => {
                setSelectedApartment(apt.id);
                // Switch to mylist if not there? Spec doesn't strictly say.
              },
            }}
          />
        ))}

        {/* Search Results */}
        {activeTab === 'search' && searchResults.map((result) => (
          <Marker
            key={result.id}
            position={[result.location.point.lat, result.location.point.lon]}
            icon={createCircleMarker('#f97316', true)} // hollow orange
            eventHandlers={{
              click: () => {
                setSelectedApartment(result.id);
              },
            }}
          />
        ))}

        <MapBounds />
      </MapContainer>
    </div>
  );
}
