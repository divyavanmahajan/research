import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ApartmentCard from '../components/ApartmentCard';
import ExportImport from '../components/ExportImport';
import { getAll } from '../db';

const PRIORITY_FILTERS = [
  { value: 'all',      label: 'All' },
  { value: 'must_see', label: 'Must see' },
  { value: 'nice',     label: 'Nice' },
  { value: 'skip',     label: 'Skip' },
];

const SORT_OPTIONS = [
  { value: 'addedAt_desc', label: 'Newest first' },
  { value: 'price_asc',    label: 'Price ↑' },
  { value: 'price_desc',   label: 'Price ↓' },
  { value: 'size_desc',    label: 'Size ↓' },
];

function sortApartments(apts, sortKey) {
  return [...apts].sort((a, b) => {
    switch (sortKey) {
      case 'price_asc':    return a.price - b.price;
      case 'price_desc':   return b.price - a.price;
      case 'size_desc':    return b.size - a.size;
      case 'addedAt_desc':
      default:             return new Date(b.addedAt) - new Date(a.addedAt);
    }
  });
}

export default function ListView() {
  const [apartments, setApartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [sort, setSort] = useState('addedAt_desc');

  async function load() {
    setLoading(true);
    const all = await getAll();
    setApartments(all);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  const visible = sortApartments(
    filter === 'all' ? apartments : apartments.filter(a => a.priority === filter),
    sort
  );

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-900">My Apartments</h1>
        <Link
          to="/investigate"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium text-center"
        >
          + Find Apartments
        </Link>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        {PRIORITY_FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filter === f.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f.label}
          </button>
        ))}
        <div className="ml-auto">
          <select
            value={sort}
            onChange={e => setSort(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-2 py-1 text-gray-600"
          >
            {SORT_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
        </div>
      ) : apartments.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-lg">No apartments in your list yet.</p>
          <Link to="/investigate" className="mt-3 inline-block text-blue-600 hover:underline">
            Start investigating →
          </Link>
        </div>
      ) : visible.length === 0 ? (
        <p className="text-gray-400 text-center py-10">No apartments match this filter.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {visible.map(apt => <ApartmentCard key={apt.id} apartment={apt} />)}
        </div>
      )}

      {apartments.length > 0 && (
        <div className="border-t pt-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-3">Backup</h2>
          <ExportImport onImport={load} />
        </div>
      )}
    </div>
  );
}
