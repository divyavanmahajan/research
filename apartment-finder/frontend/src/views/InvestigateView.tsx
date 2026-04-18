import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { getAll, put } from '../db';
import type { Apartment, ListingPreview, SearchResult } from '../types';

const PRIORITY_BADGE: Record<string, string> = {
  must_see: 'bg-green-100 text-green-700',
  nice: 'bg-amber-100 text-amber-700',
  skip: 'bg-gray-100 text-gray-500',
  unranked: 'bg-gray-100 text-gray-400',
};

type ResultListing = ListingPreview | SearchResult;

interface ResultCardProps {
  listing: ResultListing;
  onAdd: (listing: ResultListing) => void;
  alreadyAdded: boolean;
}

function ResultCard({ listing, onAdd, alreadyAdded }: ResultCardProps) {
  const photo = 'photo' in listing ? listing.photo : (listing.photos?.[0] ?? null);
  return (
    <div className="bg-white rounded-xl shadow p-4 flex gap-4">
      <div className="w-24 h-20 flex-shrink-0 bg-gray-100 rounded-lg overflow-hidden">
        {photo ? (
          <img src={photo} alt={listing.address} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-300 text-xs">No photo</div>
        )}
      </div>
      <div className="flex-1 min-w-0 space-y-1">
        <p className="font-medium text-gray-900 text-sm truncate">{listing.title || listing.address}</p>
        <p className="text-xs text-gray-500">{listing.address}{'city' in listing && listing.city ? `, ${listing.city}` : ''}</p>
        <p className="text-sm text-gray-700">{listing.price?.toLocaleString('sv-SE')} kr/mån · {listing.size} m² · {listing.rooms} rum</p>
      </div>
      <div className="flex-shrink-0 flex items-start">
        <button
          onClick={() => onAdd(listing)}
          disabled={alreadyAdded}
          className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
            alreadyAdded
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {alreadyAdded ? 'Added' : 'Add to My List'}
        </button>
      </div>
    </div>
  );
}

function UrlTab() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<ListingPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addedUrls, setAddedUrls] = useState(new Set<string>());

  async function handleFetch() {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const res = await fetch(`/api/scrape?url=${encodeURIComponent(url)}`);
      const data = await res.json() as ListingPreview & { error?: string };
      if (!res.ok) throw new Error(data.error ?? 'Scrape failed');
      setPreview(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd(listing: ResultListing) {
    const existing = await getAll();
    const duplicate = existing.find(a => a.sourceUrl === listing.sourceUrl);
    if (duplicate) { setAddedUrls(s => new Set([...s, listing.sourceUrl])); return; }

    await put({
      ...(listing as ListingPreview),
      id: uuidv4(),
      priority: 'unranked',
      status: 'new',
      notes: '',
      addedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    } as Apartment);
    setAddedUrls(s => new Set([...s, listing.sourceUrl]));
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleFetch()}
          placeholder="Paste a qasa.se listing URL…"
          className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleFetch}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
        >
          {loading ? 'Fetching…' : 'Fetch'}
        </button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {preview && (
        <ResultCard
          listing={preview}
          onAdd={handleAdd}
          alreadyAdded={addedUrls.has(preview.sourceUrl)}
        />
      )}
    </div>
  );
}

interface SearchParams {
  city: string;
  minPrice: string;
  maxPrice: string;
  minSize: string;
  maxSize: string;
  rooms: string;
}

function SearchTab() {
  const [params, setParams] = useState<SearchParams>({ city: '', minPrice: '', maxPrice: '', minSize: '', maxSize: '', rooms: '' });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addedUrls, setAddedUrls] = useState(new Set<string>());

  function setParam(key: keyof SearchParams, value: string) {
    setParams(p => ({ ...p, [key]: value }));
  }

  async function handleSearch() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v))).toString();
      const res = await fetch(`/api/search?${qs}`);
      const data = await res.json() as { results: SearchResult[]; error?: string };
      if (!res.ok) throw new Error(data.error ?? 'Search failed');
      setResults(data.results);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd(listing: ResultListing) {
    const existing = await getAll();
    const duplicate = existing.find(a => a.sourceUrl === listing.sourceUrl);
    if (duplicate) { setAddedUrls(s => new Set([...s, listing.sourceUrl])); return; }

    const res = await fetch(`/api/scrape?url=${encodeURIComponent(listing.sourceUrl)}`);
    const full = res.ok ? await res.json() as ListingPreview : listing;

    await put({
      ...full,
      id: uuidv4(),
      priority: 'unranked',
      status: 'new',
      notes: '',
      addedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    } as Apartment);
    setAddedUrls(s => new Set([...s, listing.sourceUrl]));
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {([
          { key: 'city' as const, placeholder: 'City (e.g. Stockholm)', type: 'text' },
          { key: 'minPrice' as const, placeholder: 'Min price (kr)', type: 'number' },
          { key: 'maxPrice' as const, placeholder: 'Max price (kr)', type: 'number' },
          { key: 'minSize' as const, placeholder: 'Min size (m²)', type: 'number' },
          { key: 'maxSize' as const, placeholder: 'Max size (m²)', type: 'number' },
          { key: 'rooms' as const, placeholder: 'Rooms', type: 'number' },
        ]).map(({ key, placeholder, type }) => (
          <input
            key={key}
            type={type}
            value={params[key]}
            onChange={e => setParam(key, e.target.value)}
            placeholder={placeholder}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        ))}
      </div>
      <button
        onClick={handleSearch}
        disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
      >
        {loading ? 'Searching…' : 'Search'}
      </button>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {results !== null && (
        results.length === 0
          ? <p className="text-gray-400 text-sm">No results found.</p>
          : <div className="space-y-3">
              {results.map(r => (
                <ResultCard key={r.sourceUrl} listing={r} onAdd={handleAdd} alreadyAdded={addedUrls.has(r.sourceUrl)} />
              ))}
            </div>
      )}
    </div>
  );
}

export default function InvestigateView() {
  const [tab, setTab] = useState<'url' | 'search'>('url');

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Investigate</h1>

      <div className="flex border-b border-gray-200">
        {([{ value: 'url' as const, label: 'Paste URL' }, { value: 'search' as const, label: 'Search' }]).map(t => (
          <button
            key={t.value}
            role="tab"
            aria-selected={tab === t.value}
            onClick={() => setTab(t.value)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.value
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'url' ? <UrlTab /> : <SearchTab />}
    </div>
  );
}
