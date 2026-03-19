import { useState } from 'react'
import { api } from '../api'

export default function Download() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState(50)
  const [seed, setSeed] = useState<number | ''>(42)
  const [sourceName, setSourceName] = useState('raw')

  const download = async () => {
    setLoading(true)
    setError(null)
    try {
      const blob = await api.downloadProject({
        source_name: sourceName,
        seed_rows: rows,
        seed: seed === '' ? null : seed,
        include_seeds: true,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'dbt_project.zip'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Download failed. Make sure a model is loaded.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <h1>Download DBT Project</h1>
      <p style={{ color: 'var(--color-muted)', marginBottom: '1.5rem' }}>
        Generate and download the complete DBT project as a zip file.
      </p>

      <div className="card">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--color-muted)', marginBottom: '0.25rem' }}>
              Source name
            </label>
            <input type="text" value={sourceName} onChange={e => setSourceName(e.target.value)}
              style={{ width: '100%', background: 'var(--color-bg)', border: '1px solid var(--color-border)', color: 'white', padding: '0.4rem 0.75rem', borderRadius: '5px' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--color-muted)', marginBottom: '0.25rem' }}>
              Seed rows per entity
            </label>
            <input type="number" value={rows} onChange={e => setRows(Number(e.target.value))}
              min={1} max={5000}
              style={{ width: '100%', background: 'var(--color-bg)', border: '1px solid var(--color-border)', color: 'white', padding: '0.4rem 0.75rem', borderRadius: '5px' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--color-muted)', marginBottom: '0.25rem' }}>
              Random seed (optional)
            </label>
            <input type="number" value={seed}
              onChange={e => setSeed(e.target.value === '' ? '' : Number(e.target.value))}
              placeholder="leave blank for random"
              style={{ width: '100%', background: 'var(--color-bg)', border: '1px solid var(--color-border)', color: 'white', padding: '0.4rem 0.75rem', borderRadius: '5px' }}
            />
          </div>
        </div>

        <button onClick={download} disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Generating...' : '⬇ Download ZIP'}
        </button>
      </div>

      {error && <div style={{ color: '#f87171', marginTop: '1rem' }}>{error}</div>}

      <div className="card" style={{ marginTop: '1rem', fontSize: '0.85rem', color: 'var(--color-muted)' }}>
        <strong style={{ color: 'var(--color-text)' }}>What's in the zip:</strong>
        <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem', lineHeight: '1.8' }}>
          <li><code>dbt_project.yml</code> + <code>profiles.yml</code> (DuckDB configured)</li>
          <li><code>sources.yml</code> — all entities as raw sources</li>
          <li><code>models/staging/stg_*.sql</code> — one per entity</li>
          <li><code>models/marts/dim_*.sql</code> — for entities with relationships</li>
          <li><code>tests/schema.yml</code> — auto-generated data quality tests</li>
          <li><code>seeds/*.csv</code> — relational test data (FK-consistent)</li>
        </ul>
        <div style={{ marginTop: '0.75rem' }}>
          After unzipping: <code>dbt seed && dbt run && dbt test</code>
        </div>
      </div>
    </div>
  )
}
