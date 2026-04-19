import { useEffect, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAppStore } from '../../store/useAppStore';
import { fetchTravelTimes } from '../../api/qasaApi';
import type { DestinationTravelTime, TravelDestination } from '../../types';

interface Props {
  lat: number;
  lon: number;
}

function modeIcon(mode: 'walk' | 'bike' | 'transit') {
  return mode === 'walk' ? '🚶' : mode === 'bike' ? '🚲' : '🚌';
}

function MinBadge({ minutes, url }: { minutes: number | null; url: string }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="commute-badge"
      title="Open directions in Google Maps"
    >
      {minutes != null ? `${minutes} min` : '—'}
    </a>
  );
}

function DestinationRow({ result }: { result: DestinationTravelTime }) {
  return (
    <div className="commute-row">
      <span className="commute-label">{result.label}</span>
      <div className="commute-modes">
        <span className="commute-mode-group">
          {modeIcon('walk')} <MinBadge minutes={result.walk_minutes} url={result.maps_url_walk} />
        </span>
        <span className="commute-mode-group">
          {modeIcon('bike')} <MinBadge minutes={result.bike_minutes} url={result.maps_url_bike} />
        </span>
        <a
          href={result.maps_url_transit}
          target="_blank"
          rel="noopener noreferrer"
          className="commute-badge"
          title="Open transit directions in Google Maps"
        >
          {modeIcon('transit')} transit
        </a>
      </div>
    </div>
  );
}

function DestinationsEditor({ onClose }: { onClose: () => void }) {
  const destinations = useAppStore(state => state.travelDestinations);
  const setTravelDestinations = useAppStore(state => state.setTravelDestinations);
  const [local, setLocal] = useState<TravelDestination[]>(destinations);

  const update = (id: string, field: keyof TravelDestination, value: string) => {
    setLocal(prev => prev.map(d => d.id === id ? { ...d, [field]: field === 'lat' || field === 'lon' ? parseFloat(value) || 0 : value } : d));
  };

  const add = () => setLocal(prev => [...prev, { id: uuidv4(), label: '', lat: 0, lon: 0 }]);
  const remove = (id: string) => setLocal(prev => prev.filter(d => d.id !== id));
  const save = () => { setTravelDestinations(local); onClose(); };

  return (
    <div className="commute-editor">
      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
        Edit destinations — walk & bike times from OSRM, transit opens Google Maps.
      </p>
      {local.map(d => (
        <div key={d.id} className="commute-editor-row">
          <input
            className="input-field"
            placeholder="Label"
            value={d.label}
            onChange={e => update(d.id, 'label', e.target.value)}
            style={{ flex: 2 }}
          />
          <input
            className="input-field"
            placeholder="Lat"
            type="number"
            step="0.00001"
            value={d.lat || ''}
            onChange={e => update(d.id, 'lat', e.target.value)}
            style={{ flex: 1 }}
          />
          <input
            className="input-field"
            placeholder="Lon"
            type="number"
            step="0.00001"
            value={d.lon || ''}
            onChange={e => update(d.id, 'lon', e.target.value)}
            style={{ flex: 1 }}
          />
          <button
            className="btn"
            onClick={() => remove(d.id)}
            style={{ color: 'var(--tag-red)', background: 'transparent', padding: '0.25rem 0.5rem' }}
          >
            ✕
          </button>
        </div>
      ))}
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
        <button className="btn" onClick={add} style={{ background: 'var(--bg-app)' }}>+ Add</button>
        <button className="btn btn-primary" onClick={save} style={{ flex: 1 }}>Save</button>
        <button className="btn" onClick={onClose} style={{ background: 'var(--bg-app)' }}>Cancel</button>
      </div>
    </div>
  );
}

export function CommuteSection({ lat, lon }: Props) {
  const destinations = useAppStore(state => state.travelDestinations);
  const [results, setResults] = useState<DestinationTravelTime[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [fetchKey, setFetchKey] = useState(0);

  useEffect(() => {
    if (destinations.length === 0) return;
    setLoading(true);
    fetchTravelTimes(lat, lon, destinations)
      .then(data => setResults(data.results))
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [lat, lon, fetchKey]);

  const refresh = () => setFetchKey(k => k + 1);

  return (
    <div className="commute-section">
      <div className="commute-header">
        <h4 style={{ fontSize: '0.9375rem', fontWeight: 600 }}>Commute</h4>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {!editing && (
            <button
              className="btn"
              onClick={refresh}
              style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', background: 'var(--bg-app)' }}
              title="Refresh travel times"
            >
              ↺
            </button>
          )}
          <button
            className="btn"
            onClick={() => setEditing(e => !e)}
            style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', background: 'var(--bg-app)' }}
          >
            {editing ? 'Done' : 'Edit'}
          </button>
        </div>
      </div>

      {editing ? (
        <DestinationsEditor onClose={() => { setEditing(false); refresh(); }} />
      ) : loading ? (
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', padding: '0.5rem 0' }}>
          Fetching travel times…
        </p>
      ) : destinations.length === 0 ? (
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          No destinations configured. Click Edit to add some.
        </p>
      ) : (
        results.map(r => <DestinationRow key={r.label} result={r} />)
      )}
    </div>
  );
}
