import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import type { AppDatabase } from '../../types';
import { DB_KEY } from '../../utils/db';

const SIZE_WARN_BYTES = 4 * 1024 * 1024;

export function ImportExport() {
  const apartments = useAppStore(state => state.apartments);
  const savedSearches = useAppStore(state => state.savedSearches);
  const importDb = useAppStore(state => state.importDb);
  const showToast = useAppStore(state => state.showToast);

  const [pendingImport, setPendingImport] = useState<AppDatabase | null>(null);

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
      <div className="import-export" style={{ marginTop: '2rem', padding: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '0.5rem' }}>
        <button onClick={handleExport} className="btn" style={{ flex: 1, background: 'var(--bg-app)', border: '1px solid var(--border-color)' }}>
          Export JSON
        </button>
        <label className="btn" style={{ flex: 1, background: 'var(--bg-app)', border: '1px solid var(--border-color)', textAlign: 'center', cursor: 'pointer' }}>
          Import JSON
          <input type="file" accept=".json" onChange={handleFileSelect} style={{ display: 'none' }} />
        </label>
      </div>

      {pendingImport && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.4)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          onClick={() => setPendingImport(null)}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              borderRadius: '0.75rem',
              padding: '1.5rem',
              maxWidth: '360px',
              width: '90%',
              boxShadow: 'var(--shadow-md)',
            }}
            onClick={e => e.stopPropagation()}
          >
            <p style={{ marginBottom: '0.5rem', fontWeight: 600 }}>Import {pendingImport.apartments.length} apartments</p>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
              Merge adds new items without removing existing ones. Replace overwrites your entire list.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="btn" style={{ flex: 1, background: 'var(--bg-app)' }} onClick={() => setPendingImport(null)}>
                Cancel
              </button>
              <button className="btn" style={{ flex: 1 }} onClick={() => handleImportMode('merge')}>
                Merge
              </button>
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => handleImportMode('replace')}>
                Replace All
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
