import { useAppStore } from '../../store/useAppStore';
import { AppDatabase } from '../../types';

export function ImportExport() {
  const apartments = useAppStore(state => state.apartments);
  const savedSearches = useAppStore(state => state.savedSearches);
  const importDb = useAppStore(state => state.importDb);

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

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string);
        if (!data.apartments) throw new Error('Invalid backup file');
        
        const mode = confirm('Merge with existing data? (Cancel to Replace)') ? 'merge' : 'replace';
        const { imported, existing } = importDb(data, mode);
        alert(`Successfully imported ${imported} new items. ${existing} duplicates skipped.`);
      } catch (err) {
        alert('Failed to import: Invalid JSON or structure');
      }
    };
    reader.readAsText(file);
    e.target.value = ''; // Reset input
  };

  return (
    <div className="import-export" style={{ marginTop: '2rem', padding: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '0.5rem' }}>
      <button onClick={handleExport} className="btn" style={{ flex: 1, background: 'var(--bg-app)', border: '1px solid var(--border-color)' }}>
        Export JSON
      </button>
      <label className="btn" style={{ flex: 1, background: 'var(--bg-app)', border: '1px solid var(--border-color)', textAlign: 'center', cursor: 'pointer' }}>
        Import JSON
        <input type="file" accept=".json" onChange={handleImport} style={{ display: 'none' }} />
      </label>
    </div>
  );
}
