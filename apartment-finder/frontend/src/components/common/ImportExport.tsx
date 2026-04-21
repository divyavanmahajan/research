import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import type { AppDatabase, DestinationTravelTime } from '../../types';
import { DB_KEY } from '../../utils/db';
import { getTagColor } from '../../utils/pinColor';
import { generateHtmlExport, downloadHtml } from '../../utils/htmlExport';
import { fetchTravelTimes } from '../../api/qasaApi';

const SIZE_WARN_BYTES = 4 * 1024 * 1024;

function ExportReportModal({ onClose }: { onClose: () => void }) {
  const apartments = useAppStore(state => state.apartments);
  const destinations = useAppStore(state => state.travelDestinations);

  const allTags = Array.from(new Set(apartments.flatMap(a => a.tags))).sort();
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set(allTags));
  const [fetching, setFetching] = useState(false);

  const toggleTag = (tag: string) => {
    setSelectedTags(prev => {
      const next = new Set(prev);
      next.has(tag) ? next.delete(tag) : next.add(tag);
      return next;
    });
  };

  const filtered = selectedTags.size === 0
    ? []
    : apartments.filter(a => a.tags.some(t => selectedTags.has(t)));

  const handleDownload = async () => {
    setFetching(true);
    const travelTimesMap = new Map<string, DestinationTravelTime[]>();
    if (destinations.length > 0) {
      await Promise.all(filtered.map(async apt => {
        try {
          const { lat, lon } = { lat: apt.qasaData.location.latitude, lon: apt.qasaData.location.longitude };
          const result = await fetchTravelTimes(lat, lon, destinations);
          travelTimesMap.set(apt.id, result.results);
        } catch {
          // leave entry absent — renders as no commute section
        }
      }));
    }
    setFetching(false);
    const html = generateHtmlExport(filtered, travelTimesMap);
    const date = new Date().toISOString().split('T')[0];
    downloadHtml(html, `apartments-${date}.html`);
    onClose();
  };

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={onClose}
    >
      <div
        style={{ background: 'var(--bg-card)', borderRadius: '0.75rem', padding: '1.5rem', maxWidth: '380px', width: '90%', boxShadow: 'var(--shadow-md)' }}
        onClick={e => e.stopPropagation()}
      >
        <p style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Export HTML Report</p>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
          Select tags to include. Only apartments with at least one selected tag will be exported.
        </p>

        {allTags.length === 0 ? (
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            No tags found. Tag your apartments first.
          </p>
        ) : (
          <>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
              {allTags.map(tag => {
                const active = selectedTags.has(tag);
                return (
                  <button
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    className="btn"
                    style={{
                      fontSize: '0.75rem',
                      padding: '0.25rem 0.75rem',
                      borderRadius: '9999px',
                      background: active ? getTagColor(tag) : 'transparent',
                      color: active ? 'white' : 'var(--text-muted)',
                      borderColor: getTagColor(tag),
                    }}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
              <button className="btn" style={{ fontSize: '0.75rem', background: 'var(--bg-app)' }} onClick={() => setSelectedTags(new Set(allTags))}>All</button>
              <button className="btn" style={{ fontSize: '0.75rem', background: 'var(--bg-app)' }} onClick={() => setSelectedTags(new Set())}>None</button>
              <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginLeft: 'auto', alignSelf: 'center' }}>
                {filtered.length} apartment{filtered.length !== 1 ? 's' : ''}
              </span>
            </div>
          </>
        )}

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn" style={{ flex: 1, background: 'var(--bg-app)' }} onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            style={{ flex: 1 }}
            onClick={handleDownload}
            disabled={filtered.length === 0 || fetching}
          >
            {fetching ? 'Fetching times…' : 'Download HTML'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ImportExport() {
  const apartments = useAppStore(state => state.apartments);
  const savedSearches = useAppStore(state => state.savedSearches);
  const importDb = useAppStore(state => state.importDb);
  const showToast = useAppStore(state => state.showToast);

  const [pendingImport, setPendingImport] = useState<AppDatabase | null>(null);
  const [showExportReport, setShowExportReport] = useState(false);

  const handleExport = () => {
    const db: AppDatabase = {
      version: 1,
      exportedAt: new Date().toISOString(),
      apartments,
      savedSearches,
    };
    const blob = new Blob([JSON.stringify(db, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `apartment-finder-backup-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string);
        if (!data.apartments) throw new Error('Invalid backup file');
        setPendingImport(data as AppDatabase);
      } catch {
        showToast('Failed to read file — invalid JSON or structure', 'error');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleImportMode = (mode: 'merge' | 'replace') => {
    if (!pendingImport) return;
    const { imported, existing } = importDb(pendingImport, mode);
    setPendingImport(null);
    showToast(`Imported ${imported} new items${existing > 0 ? `, ${existing} duplicates skipped` : ''}.`, 'success');

    const stored = localStorage.getItem(DB_KEY);
    if (stored && stored.length > SIZE_WARN_BYTES) {
      showToast(`Storage is ${(stored.length / 1024 / 1024).toFixed(1)} MB — consider exporting and trimming your list.`, 'error');
    }
  };

  return (
    <>
      <div className="import-export" style={{ marginTop: '2rem', padding: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
        <button onClick={handleExport} className="btn" style={{ flex: 1, background: 'var(--bg-app)', border: '1px solid var(--border-color)' }}>
          Export JSON
        </button>
        <label className="btn" style={{ flex: 1, background: 'var(--bg-app)', border: '1px solid var(--border-color)', textAlign: 'center', cursor: 'pointer' }}>
          Import JSON
          <input type="file" accept=".json" onChange={handleFileSelect} style={{ display: 'none' }} />
        </label>
        <button onClick={() => setShowExportReport(true)} className="btn" style={{ flex: '1 1 100%', background: 'var(--bg-app)', border: '1px solid var(--border-color)' }}>
          Share as HTML ✉
        </button>
      </div>

      {showExportReport && <ExportReportModal onClose={() => setShowExportReport(false)} />}

      {pendingImport && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setPendingImport(null)}
        >
          <div
            style={{ background: 'var(--bg-card)', borderRadius: '0.75rem', padding: '1.5rem', maxWidth: '360px', width: '90%', boxShadow: 'var(--shadow-md)' }}
            onClick={e => e.stopPropagation()}
          >
            <p style={{ marginBottom: '0.5rem', fontWeight: 600 }}>Import {pendingImport.apartments.length} apartments</p>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
              Merge adds new items without removing existing ones. Replace overwrites your entire list.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="btn" style={{ flex: 1, background: 'var(--bg-app)' }} onClick={() => setPendingImport(null)}>Cancel</button>
              <button className="btn" style={{ flex: 1 }} onClick={() => handleImportMode('merge')}>Merge</button>
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => handleImportMode('replace')}>Replace All</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
