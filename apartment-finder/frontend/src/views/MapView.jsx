import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { Link } from 'react-router-dom';
import L from 'leaflet';
import { getAll } from '../db';

const PRIORITY_COLORS = {
  must_see: '#22c55e',
  nice:     '#f59e0b',
  skip:     '#9ca3af',
  unranked: '#9ca3af',
};

function makeIcon(priority) {
  const color = PRIORITY_COLORS[priority] ?? PRIORITY_COLORS.unranked;
  return L.divIcon({
    className: '',
    html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,.3)"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

function FitBounds({ positions }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length > 0) {
      map.fitBounds(positions, { padding: [40, 40] });
    }
  }, [positions]);
  return null;
}

export default function MapView() {
  const [apartments, setApartments] = useState([]);

  useEffect(() => {
    getAll().then(all => setApartments(all.filter(a => a.lat != null && a.lng != null)));
  }, []);

  const positions = apartments.map(a => [a.lat, a.lng]);
  const center = positions.length > 0 ? positions[0] : [59.33, 18.06];

  return (
    <div className="h-[calc(100vh-56px)] flex flex-col">
      {apartments.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
          <p className="text-gray-500 bg-white px-4 py-2 rounded-lg shadow">
            No apartments with location data yet.
          </p>
        </div>
      )}
      <MapContainer center={center} zoom={12} className="flex-1 z-0">
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
        />
        {positions.length > 0 && <FitBounds positions={positions} />}
        {apartments.map(apt => (
          <Marker key={apt.id} position={[apt.lat, apt.lng]} icon={makeIcon(apt.priority)}>
            <Popup>
              <div className="space-y-1 min-w-[160px]">
                {apt.photos?.[0] && (
                  <img src={apt.photos[0]} alt={apt.address} className="w-full h-24 object-cover rounded" />
                )}
                <p className="font-medium text-sm">{apt.address}</p>
                <p className="text-xs text-gray-500">{apt.price?.toLocaleString('sv-SE')} kr/mån · {apt.size} m²</p>
                <Link to={`/apartment/${apt.id}`} className="text-xs text-blue-600 hover:underline block">
                  Open detail →
                </Link>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
