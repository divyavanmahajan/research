import { useState } from 'react'
import { api, GeneratePreviewResult } from '../api'

export default function Preview() {
  const [result, setResult] = useState<GeneratePreviewResult | null>(null)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sourceRows, setSourceRows] = useState(50)

  const generate = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.generatePreview({ seed_rows: sourceRows, seed: 42, include_seeds: true })
      setResult(data)
      const firstKey = Object.keys(data.files)[0]
      setSelectedFile(firstKey)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Generation failed. Make sure a model is loaded.')
    } finally {
      setLoading(false)
    }
  }

  const files = result ? Object.keys(result.files).sort() : []

  const fileGroups = files.reduce<Record<string, string[]>>((acc, f) => {
    const dir = f.includes('/') ? f.split('/').slice(0, -1).join('/') : '.'
    if (!acc[dir]) acc[dir] = []
    acc[dir].push(f)
    return acc
  }, {})

  return (
    <div>
      <h1>Artifact Preview</h1>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', marginBottom: '1.5rem' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--color-muted)', marginBottom: '0.25rem' }}>
            Seed rows per entity
          </label>
          <input
            type="number"
            value={sourceRows}
            onChange={e => setSourceRows(Number(e.target.value))}
            min={1} max={500}
            style={{
              background: 'var(--color-surface)', border: '1px solid var(--color-border)',
              color: 'white', padding: '0.4rem 0.75rem', borderRadius: '5px', width: 80
            }}
          />
        </div>
        <button onClick={generate} disabled={loading}>
          {loading ? 'Generating...' : 'Generate Artifacts'}
        </button>
      </div>

      {error && <div style={{ color: '#f87171', marginBottom: '1rem' }}>{error}</div>}

      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: '1rem', height: '70vh' }}>
          {/* File tree */}
          <div className="card" style={{ overflow: 'auto', padding: '0.75rem' }}>
            {Object.entries(fileGroups).map(([dir, paths]) => (
              <div key={dir} style={{ marginBottom: '0.5rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-muted)', padding: '0.2rem 0.5rem' }}>
                  {dir === '.' ? '/' : `/${dir}`}
                </div>
                {paths.map(p => (
                  <div
                    key={p}
                    onClick={() => setSelectedFile(p)}
                    style={{
                      padding: '0.25rem 0.75rem',
                      cursor: 'pointer',
                      borderRadius: '4px',
                      fontSize: '0.8rem',
                      fontFamily: 'monospace',
                      background: selectedFile === p ? 'var(--color-accent)22' : 'transparent',
                      color: selectedFile === p ? 'white' : 'var(--color-muted)',
                    }}
                  >
                    {p.split('/').pop()}
                  </div>
                ))}
              </div>
            ))}
          </div>

          {/* File content */}
          <div>
            {selectedFile && (
              <>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-muted)', marginBottom: '0.5rem', fontFamily: 'monospace' }}>
                  {selectedFile}
                </div>
                <pre style={{ height: '100%', maxHeight: 'calc(70vh - 2rem)' }}>
                  {result.files[selectedFile]}
                </pre>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
