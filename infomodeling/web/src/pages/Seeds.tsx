import { useState } from 'react'
import { api, SeedPreviewRow } from '../api'

export default function Seeds() {
  const [previews, setPreviews] = useState<SeedPreviewRow[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState(50)
  const [seed, setSeed] = useState(42)

  const generate = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.seedPreview({ seed_rows: rows, seed })
      setPreviews(data)
      if (data.length > 0) setSelected(data[0].entity_name)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed. Make sure a model is loaded.')
    } finally {
      setLoading(false)
    }
  }

  const current = previews.find(p => p.entity_name === selected)

  return (
    <div>
      <h1>Seed Data Preview</h1>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', marginBottom: '1.5rem' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--color-muted)', marginBottom: '0.25rem' }}>
            Rows per entity
          </label>
          <input type="number" value={rows} onChange={e => setRows(Number(e.target.value))}
            min={1} max={500}
            style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', color: 'white', padding: '0.4rem 0.75rem', borderRadius: '5px', width: 80 }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--color-muted)', marginBottom: '0.25rem' }}>
            Random seed
          </label>
          <input type="number" value={seed} onChange={e => setSeed(Number(e.target.value))}
            style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', color: 'white', padding: '0.4rem 0.75rem', borderRadius: '5px', width: 100 }}
          />
        </div>
        <button onClick={generate} disabled={loading}>
          {loading ? 'Generating...' : 'Preview Seeds'}
        </button>
      </div>

      {error && <div style={{ color: '#f87171', marginBottom: '1rem' }}>{error}</div>}

      {previews.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: '1rem' }}>
          <div className="card" style={{ padding: '0.5rem' }}>
            {previews.map(p => (
              <div
                key={p.entity_name}
                onClick={() => setSelected(p.entity_name)}
                style={{
                  padding: '0.35rem 0.75rem',
                  cursor: 'pointer',
                  borderRadius: '4px',
                  fontSize: '0.85rem',
                  fontFamily: 'monospace',
                  background: selected === p.entity_name ? 'var(--color-accent)22' : 'transparent',
                  color: selected === p.entity_name ? 'white' : 'var(--color-muted)',
                }}
              >
                {p.entity_name}
              </div>
            ))}
          </div>

          <div className="card" style={{ overflow: 'auto' }}>
            {current && (
              <>
                <div style={{ marginBottom: '0.75rem', fontSize: '0.85rem', color: 'var(--color-muted)' }}>
                  Showing first {current.rows.length} rows of {rows} total
                </div>
                <table>
                  <thead>
                    <tr>
                      {current.columns.map(c => <th key={c}>{c}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {current.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((cell, j) => (
                          <td key={j} style={{
                            fontFamily: 'monospace',
                            fontSize: '0.78rem',
                            maxWidth: 180,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            color: cell === null ? 'var(--color-muted)' : undefined,
                          }}>
                            {cell ?? 'null'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
