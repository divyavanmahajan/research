import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import PhotoGallery from '../components/PhotoGallery';
import PriorityPicker from '../components/PriorityPicker';
import StatusStepper from '../components/StatusStepper';
import { get, put, remove } from '../db';

function useDebounce(fn, delay) {
  const timer = useRef(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  return (...args) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => fnRef.current(...args), delay);
  };
}

export default function DetailView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [apt, setApt] = useState(null);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    get(id).then(a => {
      if (!a) { navigate('/'); return; }
      setApt(a);
      setNotes(a.notes ?? '');
    });
  }, [id]);

  async function update(patch) {
    const updated = { ...apt, ...patch, updatedAt: new Date().toISOString() };
    setApt(updated);
    await put(updated);
  }

  const saveNotes = useDebounce(async (text) => {
    setSaving(true);
    await update({ notes: text });
    setSaving(false);
  }, 600);

  function handleNotesChange(e) {
    setNotes(e.target.value);
    saveNotes(e.target.value);
  }

  async function handleDelete() {
    if (!window.confirm('Remove this apartment from your list?')) return;
    await remove(id);
    navigate('/');
  }

  if (!apt) return <div className="flex justify-center py-20 text-gray-400">Loading…</div>;

  const hasMap = apt.lat != null && apt.lng != null;

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      <Link to="/" className="text-sm text-blue-600 hover:underline">← My List</Link>

      <PhotoGallery photos={apt.photos ?? []} />

      <div>
        <h1 className="text-xl font-bold text-gray-900">{apt.address}</h1>
        <p className="text-gray-500 text-sm">{apt.city}</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        {[
          { label: 'Rent', value: `${apt.price?.toLocaleString('sv-SE')} kr/mån` },
          { label: 'Deposit', value: apt.deposit ? `${apt.deposit.toLocaleString('sv-SE')} kr` : '—' },
          { label: 'Size', value: apt.size ? `${apt.size} m²` : '—' },
          { label: 'Rooms', value: apt.rooms ?? '—' },
          { label: 'Floor', value: apt.floor ?? '—' },
          { label: 'Available', value: apt.availableFrom ?? '—' },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-400 uppercase mb-1">{label}</p>
            <p className="font-medium text-gray-800">{value}</p>
          </div>
        ))}
      </div>

      {hasMap && (
        <MapContainer center={[apt.lat, apt.lng]} zoom={15} className="h-56 rounded-xl z-0">
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Marker position={[apt.lat, apt.lng]}>
            <Popup>{apt.address}</Popup>
          </Marker>
        </MapContainer>
      )}

      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-gray-500 uppercase">Priority</h2>
        <PriorityPicker value={apt.priority} onChange={p => update({ priority: p })} />
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-gray-500 uppercase">Status</h2>
        <StatusStepper value={apt.status} onChange={s => update({ status: s })} />
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-gray-500 uppercase flex items-center gap-2">
          Notes {saving && <span className="text-xs text-gray-400 font-normal">Saving…</span>}
        </h2>
        <textarea
          value={notes}
          onChange={handleNotesChange}
          rows={5}
          placeholder="Your thoughts about this apartment…"
          className="w-full border border-gray-200 rounded-xl p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {apt.description && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-gray-500 uppercase">Description</h2>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{apt.description}</p>
        </div>
      )}

      <div className="flex items-center justify-between pt-4 border-t">
        <a
          href={apt.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:underline"
        >
          View on qasa.se ↗
        </a>
        <button onClick={handleDelete} className="text-sm text-red-500 hover:text-red-700">
          Remove from list
        </button>
      </div>
    </div>
  );
}
