import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { api, ModelSchema, EntitySchema } from '../api'

const NODE_WIDTH = 220
const NODE_HEIGHT_BASE = 56
const ROW_HEIGHT = 22

function buildLayout(entities: EntitySchema[]): { nodes: Node[]; edges: Edge[] } {
  // Simple grid layout: ~4 columns
  const cols = 4
  const xGap = NODE_WIDTH + 60
  const yGap = 200

  const nodes: Node[] = entities.map((entity, idx) => {
    const col = idx % cols
    const row = Math.floor(idx / cols)
    const height = NODE_HEIGHT_BASE + entity.attributes.length * ROW_HEIGHT
    const fkFields = new Set(entity.relationships.map(r => r.via))

    return {
      id: entity.name,
      position: { x: col * xGap, y: row * yGap },
      style: {
        background: '#1a1a2e',
        border: '1px solid #6d28d9',
        borderRadius: 8,
        padding: 0,
        width: NODE_WIDTH,
        fontSize: 12,
        color: 'white',
      },
      data: {
        label: (
          <div>
            <div style={{
              background: '#6d28d9',
              padding: '6px 10px',
              borderRadius: '7px 7px 0 0',
              fontWeight: 700,
              fontSize: 13,
              letterSpacing: '0.02em',
            }}>
              {entity.name}
            </div>
            <div style={{ padding: '6px 10px' }}>
              {entity.attributes.map(a => (
                <div key={a.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, lineHeight: '20px' }}>
                  <span style={{ fontFamily: 'monospace', color: a.primary_key ? '#fbbf24' : fkFields.has(a.name) ? '#a78bfa' : '#e2e8f0' }}>
                    {a.name}
                  </span>
                  <span style={{ color: '#64748b', fontSize: 10, alignSelf: 'center' }}>{a.type}</span>
                </div>
              ))}
            </div>
          </div>
        ),
      },
    }
  })

  const edgeIndex: Record<string, number> = {}
  const edges: Edge[] = []

  for (const entity of entities) {
    for (const rel of entity.relationships) {
      if (rel.to === entity.name) continue // skip self-refs
      const key = `${entity.name}→${rel.to}`
      const idx = (edgeIndex[key] = (edgeIndex[key] ?? -1) + 1)
      edges.push({
        id: `${entity.name}-${rel.via}-${rel.to}`,
        source: entity.name,
        target: rel.to,
        label: rel.via,
        labelStyle: { fontSize: 10, fill: '#94a3b8' },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.8 },
        style: { stroke: '#7c3aed', strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#7c3aed', width: 14, height: 14 },
        type: 'smoothstep',
        animated: false,
      })
    }
  }

  return { nodes, edges }
}

export default function Graph() {
  const [model, setModel] = useState<ModelSchema | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedEntity, setSelectedEntity] = useState<EntitySchema | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  useEffect(() => {
    api.getEntities()
      .then(data => {
        setModel(data)
        const { nodes: n, edges: e } = buildLayout(data.entities)
        setNodes(n)
        setEdges(e)
      })
      .catch(() => setError('No model loaded. Please upload a model first.'))
  }, [])

  const onNodeClick = useCallback((_: any, node: Node) => {
    if (!model) return
    const entity = model.entities.find(e => e.name === node.id) ?? null
    setSelectedEntity(prev => prev?.name === entity?.name ? null : entity)
  }, [model])

  if (error) return <div style={{ color: '#f87171', padding: '1.5rem' }}>{error}</div>
  if (!model) return <div style={{ color: 'var(--color-muted)', padding: '1.5rem' }}>Loading...</div>

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 64px)', gap: 0 }}>
      {/* Graph canvas */}
      <div style={{ flex: 1, position: 'relative' }}>
        <div style={{
          position: 'absolute', top: 12, left: 12, zIndex: 10,
          background: '#1e1e2e', border: '1px solid #334155',
          borderRadius: 8, padding: '8px 14px', fontSize: 13, color: '#94a3b8',
        }}>
          <strong style={{ color: 'white' }}>{model.name}</strong>
          &nbsp;·&nbsp;{model.entity_count} entities
          &nbsp;·&nbsp;{edges.length} relationships
        </div>
        <div style={{
          position: 'absolute', bottom: 12, left: 12, zIndex: 10,
          fontSize: 11, color: '#475569',
        }}>
          <span style={{ color: '#fbbf24' }}>■</span> PK &nbsp;
          <span style={{ color: '#a78bfa' }}>■</span> FK &nbsp;
          <span style={{ color: '#e2e8f0' }}>■</span> field
        </div>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#1e293b" />
          <Controls style={{ background: '#1e1e2e', border: '1px solid #334155' }} />
          <MiniMap
            nodeColor="#6d28d9"
            maskColor="rgba(0,0,0,0.7)"
            style={{ background: '#0f172a', border: '1px solid #334155' }}
          />
        </ReactFlow>
      </div>

      {/* Detail panel */}
      {selectedEntity && (
        <div style={{
          width: 280, background: '#1e1e2e', borderLeft: '1px solid #334155',
          padding: '1rem', overflowY: 'auto', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <strong style={{ fontSize: 15 }}>{selectedEntity.name}</strong>
            <button
              onClick={() => setSelectedEntity(null)}
              style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}
            >×</button>
          </div>
          {selectedEntity.description && (
            <p style={{ color: '#64748b', fontSize: 12, marginBottom: '0.75rem' }}>{selectedEntity.description}</p>
          )}

          <div style={{ fontSize: 11, color: '#7c3aed', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Attributes
          </div>
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', marginBottom: '1rem' }}>
            <thead>
              <tr style={{ color: '#64748b' }}>
                <th style={{ textAlign: 'left', padding: '2px 0' }}>Field</th>
                <th style={{ textAlign: 'left', padding: '2px 6px' }}>Type</th>
                <th style={{ textAlign: 'right', padding: '2px 0' }}>Flags</th>
              </tr>
            </thead>
            <tbody>
              {selectedEntity.attributes.map(a => (
                <tr key={a.name} style={{ borderTop: '1px solid #1e293b' }}>
                  <td style={{ fontFamily: 'monospace', padding: '3px 0', color: a.primary_key ? '#fbbf24' : '#e2e8f0' }}>
                    {a.name}
                  </td>
                  <td style={{ color: '#64748b', padding: '3px 6px' }}>{a.type}</td>
                  <td style={{ textAlign: 'right', padding: '3px 0' }}>
                    {a.primary_key && <span className="badge badge-pk">PK</span>}
                    {a.nullable && <span className="badge">?</span>}
                    {a.enum.length > 0 && <span className="badge badge-enum">enum</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {selectedEntity.relationships.length > 0 && (
            <>
              <div style={{ fontSize: 11, color: '#7c3aed', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Relationships
              </div>
              {selectedEntity.relationships.map((r, i) => (
                <div key={i} style={{
                  background: '#0f172a', borderRadius: 6, padding: '6px 10px', marginBottom: '0.4rem',
                  fontSize: 12, display: 'flex', flexDirection: 'column', gap: 2,
                }}>
                  <div style={{ color: '#a78bfa', fontFamily: 'monospace' }}>{r.via}</div>
                  <div style={{ color: '#64748b' }}>
                    → <span style={{ color: '#e2e8f0' }}>{r.to}</span>
                    &nbsp;<span style={{ color: '#475569' }}>[{r.cardinality}]</span>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}
