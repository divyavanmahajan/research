import { useEffect, useState } from 'react'
import { api, ModelSchema, EntitySchema } from '../api'

function EntityCard({ entity, onSelect, selected }: {
  entity: EntitySchema
  onSelect: (e: EntitySchema) => void
  selected: boolean
}) {
  const fkFields = new Set(entity.relationships.map(r => r.via))
  return (
    <div
      className="card"
      style={{ cursor: 'pointer', borderColor: selected ? 'var(--color-accent)' : undefined }}
      onClick={() => onSelect(entity)}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>{entity.name}</strong>
        <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)' }}>
          {entity.attributes.length} attrs · {entity.relationships.length} rels
        </span>
      </div>
      {entity.description && (
        <div style={{ color: 'var(--color-muted)', fontSize: '0.8rem', marginTop: '0.3rem' }}>
          {entity.description}
        </div>
      )}
      {selected && (
        <table style={{ marginTop: '0.75rem' }}>
          <thead>
            <tr><th>Field</th><th>Type</th><th>Flags</th></tr>
          </thead>
          <tbody>
            {entity.attributes.map(a => (
              <tr key={a.name}>
                <td style={{ fontFamily: 'monospace' }}>{a.name}</td>
                <td style={{ color: 'var(--color-muted)' }}>{a.type}</td>
                <td>
                  {a.primary_key && <span className="badge badge-pk">PK</span>}
                  {a.nullable && <span className="badge">nullable</span>}
                  {a.enum.length > 0 && <span className="badge badge-enum">enum</span>}
                  {fkFields.has(a.name) && <span className="badge badge-fk">FK</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {selected && entity.relationships.length > 0 && (
        <div style={{ marginTop: '0.75rem', fontSize: '0.8rem' }}>
          <div style={{ color: 'var(--color-muted)', marginBottom: '0.25rem' }}>Relationships:</div>
          {entity.relationships.map((r, i) => (
            <div key={i} style={{ fontFamily: 'monospace', color: '#a78bfa' }}>
              {r.via} → {r.to} [{r.cardinality}]
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Explorer() {
  const [model, setModel] = useState<ModelSchema | null>(null)
  const [selected, setSelected] = useState<EntitySchema | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getEntities()
      .then(setModel)
      .catch(() => setError('No model loaded. Please upload a model first.'))
  }, [])

  if (error) return <div style={{ color: '#f87171' }}>{error}</div>
  if (!model) return <div style={{ color: 'var(--color-muted)' }}>Loading...</div>

  return (
    <div>
      <h1>{model.name}</h1>
      <p style={{ color: 'var(--color-muted)', marginBottom: '1.5rem' }}>
        {model.entity_count} entities · v{model.version}
        {model.description && ` · ${model.description}`}
      </p>
      <div style={{ columns: '2 400px', columnGap: '1rem' }}>
        {model.entities.map(e => (
          <div key={e.name} style={{ breakInside: 'avoid', marginBottom: '0' }}>
            <EntityCard
              entity={e}
              onSelect={(ent) => setSelected(selected?.name === ent.name ? null : ent)}
              selected={selected?.name === e.name}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
