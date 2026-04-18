import { useRef, useState } from 'react';
import { exportAll, importAll } from '../db';
import type { Apartment } from '../types';

interface Props {
  onImport?: () => void;
}

interface StatusMsg {
  type: 'success' | 'error';
  msg: string;
}

export default function ExportImport({ onImport }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<'merge' | 'replace'>('merge');
  const [status, setStatus] = useState<StatusMsg | null>(null);

  async function handleExport() {
    const json = await exportAll();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `apartments-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const apartments = JSON.parse(text) as Apartment[];
      if (!Array.isArray(apartments)) throw new Error('JSON must be an array');
      await importAll(apartments, mode);
      setStatus({ type: 'success', msg: `Imported ${apartments.length} apartments (${mode} mode)` });
      onImport?.();
    } catch (err) {
      setStatus({ type: 'error', msg: (err as Error).message });
    }
    e.target.value = '';
  }

  return (
    <div className="flex flex-col gap-3">
      <button
        onClick={handleExport}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
      >
        Export JSON
      </button>
      <div className="flex items-center gap-2">
        <label className="text-sm text-gray-600">Import mode:</label>
        <select
          value={mode}
          onChange={e => setMode(e.target.value as 'merge' | 'replace')}
          className="text-sm border rounded px-2 py-1"
        >
          <option value="merge">Merge</option>
          <option value="replace">Replace all</option>
        </select>
      </div>
      <button
        onClick={() => fileRef.current?.click()}
        className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium"
      >
        Import JSON
      </button>
      <input ref={fileRef} type="file" accept=".json" className="hidden" onChange={handleImport} />
      {status && (
        <p className={`text-sm ${status.type === 'error' ? 'text-red-600' : 'text-green-600'}`}>
          {status.msg}
        </p>
      )}
    </div>
  );
}
