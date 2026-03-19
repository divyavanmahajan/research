import { useEffect, useState, useCallback, useRef } from 'react'
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
  ReactFlowInstance,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { api, ModelSchema, EntitySchema } from '../api'

// ─── Layout constants ────────────────────────────────────────────────────────
const NODE_W = 220
const NODE_H_BASE = 54
const ATTR_ROW = 22
const COLS = 4
const COL_GAP = NODE_W + 80
const ROW_GAP = 280
const GROUP_PAD = 36

const GROUP_PALETTE = [
  { border: '#3b82f6', bg: '#172554' },
  { border: '#22c55e', bg: '#14532d' },
  { border: '#f59e0b', bg: '#451a03' },
  { border: '#ec4899', bg: '#500724' },
  { border: '#06b6d4', bg: '#083344' },
  { border: '#a855f7', bg: '#3b0764' },
]

function entityH(e: EntitySchema) {
  return NODE_H_BASE + e.attributes.length * ATTR_ROW
}

// ─── Custom node: entity card ─────────────────────────────────────────────────
function EntityNode({ data }: { data: { entity: EntitySchema; isSelected: boolean; inSelMode: boolean } }) {
  const { entity, isSelected, inSelMode } = data
  const fkFields = new Set(entity.relationships.map(r => r.via))
  const border = isSelected ? '#f59e0b' : '#6d28d9'

  return (
    <div style={{
      background: '#1a1a2e',
      border: `${isSelected ? 2 : 1}px solid ${border}`,
      borderRadius: 8,
      width: NODE_W,
      fontSize: 12,
      color: 'white',
      boxShadow: isSelected ? `0 0 0 3px #f59e0b44` : 'none',
      cursor: inSelMode ? 'pointer' : 'default',
    }}>
      <div style={{
        background: '#6d28d9',
        padding: '6px 10px',
        borderRadius: '7px 7px 0 0',
        fontWeight: 700,
        fontSize: 13,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span>{entity.name}</span>
        {inSelMode && (
          <span style={{
            width: 14, height: 14, border: '2px solid white', borderRadius: 3,
            background: isSelected ? 'white' : 'transparent',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 10, color: '#6d28d9', flexShrink: 0,
          }}>
            {isSelected ? '✓' : ''}
          </span>
        )}
      </div>
      <div style={{ padding: '6px 10px' }}>
        {entity.attributes.map(a => (
          <div key={a.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, lineHeight: '20px' }}>
            <span style={{ fontFamily: 'monospace', color: a.primary_key ? '#fbbf24' : fkFields.has(a.name) ? '#a78bfa' : '#e2e8f0' }}>
              {a.name}
            </span>
            <span style={{ color: '#475569', fontSize: 10, alignSelf: 'center' }}>{a.type}</span>
          </div>
        ))}
      </div>
      {entity.tags.length > 0 && (
        <div style={{ padding: '0 10px 6px', display: 'flex', flexWrap: 'wrap', gap: 3 }}>
          {entity.tags.map(t => (
            <span key={t} style={{
              fontSize: 9, background: '#0f172a', color: '#64748b',
              padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace',
            }}>{t}</span>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Custom node: group region ────────────────────────────────────────────────
function GroupNode({ data }: { data: { label: string; color: { border: string; bg: string } } }) {
  return (
    <div style={{
      width: '100%', height: '100%',
      border: `1.5px solid ${data.color.border}44`,
      borderRadius: 14,
      background: `${data.color.bg}88`,
      position: 'relative',
      pointerEvents: 'none',
    }}>
      <div style={{
        position: 'absolute', top: -13, left: 14,
        background: data.color.border,
        color: '#fff',
        padding: '1px 10px',
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        pointerEvents: 'none',
      }}>
        {data.label}
      </div>
    </div>
  )
}

const nodeTypes = { entity: EntityNode, group: GroupNode }

// ─── Layout builder ───────────────────────────────────────────────────────────
function buildLayout(
  allEntities: EntitySchema[],
  tagFilter: string,
  levelFilter: number | null,
  selectedEntities: Set<string>,
  inSelMode: boolean,
): { nodes: Node[]; edges: Edge[] } {
  const normFilter = tagFilter.trim().toLowerCase()

  const visible = allEntities.filter(e => {
    if (normFilter) {
      if (!e.tags.some(t => t === normFilter || t.startsWith(normFilter + '-'))) return false
    }
    if (levelFilter !== null) {
      // g- tag depth: "g-foo" = depth 1, "g-foo-bar" = depth 2
      const gTags = e.tags.filter(t => t.startsWith('g-'))
      if (!gTags.some(t => t.split('-').length - 1 === levelFilter)) return false
    }
    return true
  })

  const visibleNames = new Set(visible.map(e => e.name))

  // Determine which level to draw group boxes at
  const groupLevel = levelFilter ?? 1

  // Cluster entities by their g- tag at groupLevel for non-overlapping layout
  const groupOrder: string[] = []
  const byGroup = new Map<string, EntitySchema[]>()
  for (const e of visible) {
    const gTag = e.tags.find(t => t.startsWith('g-') && t.split('-').length - 1 === groupLevel) ?? '__none__'
    if (!byGroup.has(gTag)) { byGroup.set(gTag, []); groupOrder.push(gTag) }
    byGroup.get(gTag)!.push(e)
  }

  // Assign positions group-by-group (each group's rows stacked below previous)
  const pos: Record<string, { x: number; y: number; h: number }> = {}
  let currentY = 0
  for (const gTag of groupOrder) {
    const members = byGroup.get(gTag)!
    const groupRows = Math.ceil(members.length / COLS)
    members.forEach((e, i) => {
      const col = i % COLS
      const row = Math.floor(i / COLS)
      pos[e.name] = { x: col * COL_GAP, y: currentY + row * ROW_GAP, h: entityH(e) }
    })
    const maxH = Math.max(...members.map(e => entityH(e)))
    currentY += groupRows * ROW_GAP + maxH - (ROW_GAP - maxH - 40)
  }

  // Gather groups at groupLevel for bounding boxes
  const groupMap = new Map<string, string[]>()
  let colorIdx = 0
  const groupColors: Map<string, { border: string; bg: string }> = new Map()

  for (const e of visible) {
    const gTags = e.tags.filter(t => t.startsWith('g-') && t.split('-').length - 1 === groupLevel)
    for (const tag of gTags) {
      if (!groupMap.has(tag)) {
        groupMap.set(tag, [])
        groupColors.set(tag, GROUP_PALETTE[colorIdx % GROUP_PALETTE.length])
        colorIdx++
      }
      groupMap.get(tag)!.push(e.name)
    }
  }

  // Build group nodes (rendered behind entities)
  const groupNodes: Node[] = []
  for (const [tag, names] of groupMap) {
    const members = names.map(n => pos[n]).filter(Boolean)
    if (!members.length) continue
    const x1 = Math.min(...members.map(p => p.x)) - GROUP_PAD
    const y1 = Math.min(...members.map(p => p.y)) - GROUP_PAD - 18
    const x2 = Math.max(...members.map(p => p.x)) + NODE_W + GROUP_PAD
    const y2 = Math.max(...members.map(p => p.y + p.h)) + GROUP_PAD
    const color = groupColors.get(tag)!
    const label = tag.replace(/^g-/, '').replace(/-/g, ' › ')
    groupNodes.push({
      id: `__group__${tag}`,
      type: 'group',
      position: { x: x1, y: y1 },
      style: { width: x2 - x1, height: y2 - y1, pointerEvents: 'none' },
      data: { label, color },
      selectable: false,
      draggable: false,
      zIndex: -1,
    })
  }

  // Build entity nodes
  const entityNodes: Node[] = visible.map(e => ({
    id: e.name,
    type: 'entity',
    position: { x: pos[e.name].x, y: pos[e.name].y },
    data: {
      entity: e,
      isSelected: selectedEntities.has(e.name),
      inSelMode,
    },
    zIndex: 1,
    style: { width: NODE_W },
  }))

  // Edges (only between visible entities; skip self-refs)
  const edges: Edge[] = []
  for (const e of visible) {
    for (const rel of e.relationships) {
      if (rel.to === e.name || !visibleNames.has(rel.to)) continue
      edges.push({
        id: `${e.name}-${rel.via}-${rel.to}`,
        source: e.name,
        target: rel.to,
        label: rel.via,
        labelStyle: { fontSize: 10, fill: '#94a3b8' },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.85 },
        style: { stroke: '#7c3aed', strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#7c3aed', width: 14, height: 14 },
        type: 'smoothstep',
      })
    }
  }

  return { nodes: [...groupNodes, ...entityNodes], edges }
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function Graph() {
  const [model, setModel] = useState<ModelSchema | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<EntitySchema | null>(null)

  const [tagFilter, setTagFilter] = useState('')
  const [levelFilter, setLevelFilter] = useState<number | null>(null)
  const [inSelMode, setInSelMode] = useState(false)
  const [selectedEntities, setSelectedEntities] = useState<Set<string>>(new Set())

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const rfRef = useRef<ReactFlowInstance | null>(null)

  useEffect(() => {
    api.getEntities()
      .then(data => { setModel(data) })
      .catch(() => setError('No model loaded. Please upload a model first.'))
  }, [])

  // Rebuild graph whenever filters, selection, or model change
  useEffect(() => {
    if (!model) return
    const { nodes: n, edges: e } = buildLayout(
      model.entities, tagFilter, levelFilter, selectedEntities, inSelMode,
    )
    setNodes(n)
    setEdges(e)
    setTimeout(() => rfRef.current?.fitView({ padding: 0.15, duration: 300 }), 50)
  }, [model, tagFilter, levelFilter, selectedEntities, inSelMode])

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    if (node.type === 'group') return
    if (inSelMode) {
      setSelectedEntities(prev => {
        const next = new Set(prev)
        next.has(node.id) ? next.delete(node.id) : next.add(node.id)
        return next
      })
    } else {
      if (!model) return
      const entity = model.entities.find(e => e.name === node.id) ?? null
      setSelectedDetail(prev => prev?.name === entity?.name ? null : entity)
    }
  }, [model, inSelMode])

  const handleExport = async () => {
    if (!model) return
    const names = inSelMode && selectedEntities.size > 0
      ? Array.from(selectedEntities)
      : []   // empty = all
    const blob = await api.exportModel(names)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'model_export.yaml'
    a.click()
    URL.revokeObjectURL(url)
  }

  const visibleCount = nodes.filter(n => n.type === 'entity').length
  const allTags = model
    ? [...new Set(model.entities.flatMap(e => e.tags))].sort()
    : []

  if (error) return <div style={{ color: '#f87171', padding: '1.5rem' }}>{error}</div>
  if (!model) return <div style={{ color: 'var(--color-muted)', padding: '1.5rem' }}>Loading...</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)' }}>

      {/* ── Toolbar ── */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '0.6rem', alignItems: 'center',
        padding: '0.6rem 1rem',
        background: '#1e1e2e',
        borderBottom: '1px solid #334155',
        fontSize: 13,
      }}>
        {/* Tag filter */}
        <label style={{ color: '#64748b', whiteSpace: 'nowrap' }}>Tag filter:</label>
        <input
          value={tagFilter}
          onChange={e => setTagFilter(e.target.value)}
          placeholder="e.g. g-people or hr"
          list="tag-suggestions"
          style={{
            background: '#0f172a', border: '1px solid #334155', color: 'white',
            padding: '3px 8px', borderRadius: 5, width: 180, fontSize: 12,
          }}
        />
        <datalist id="tag-suggestions">
          {allTags.map(t => <option key={t} value={t} />)}
        </datalist>
        {tagFilter && (
          <button onClick={() => setTagFilter('')} style={{ padding: '2px 8px', fontSize: 11, background: '#374151' }}>
            ✕ clear
          </button>
        )}

        <div style={{ width: 1, height: 20, background: '#334155' }} />

        {/* Level filter */}
        <label style={{ color: '#64748b', whiteSpace: 'nowrap' }}>Group level:</label>
        <select
          value={levelFilter ?? ''}
          onChange={e => setLevelFilter(e.target.value === '' ? null : Number(e.target.value))}
          style={{
            background: '#0f172a', border: '1px solid #334155', color: 'white',
            padding: '3px 8px', borderRadius: 5, fontSize: 12,
          }}
        >
          <option value="">all g- groups</option>
          <option value="1">level 1 — g-domain</option>
          <option value="2">level 2 — g-domain-subdomain</option>
          <option value="3">level 3 — g-domain-subdomain-leaf</option>
        </select>

        <div style={{ width: 1, height: 20, background: '#334155' }} />

        {/* Select mode */}
        <button
          onClick={() => {
            setInSelMode(m => !m)
            setSelectedEntities(new Set())
            setSelectedDetail(null)
          }}
          style={{
            background: inSelMode ? '#6d28d9' : '#1e293b',
            border: `1px solid ${inSelMode ? '#7c3aed' : '#334155'}`,
            color: 'white', padding: '3px 12px', borderRadius: 5, fontSize: 12, cursor: 'pointer',
          }}
        >
          {inSelMode ? `✓ ${selectedEntities.size} selected` : 'Select nodes'}
        </button>

        {inSelMode && (
          <>
            <button
              onClick={() => setSelectedEntities(new Set(nodes.filter(n => n.type === 'entity').map(n => n.id)))}
              style={{ padding: '3px 10px', fontSize: 11, background: '#1e293b', border: '1px solid #334155', color: '#94a3b8', borderRadius: 5, cursor: 'pointer' }}
            >
              Select all
            </button>
            <button
              onClick={() => setSelectedEntities(new Set())}
              style={{ padding: '3px 10px', fontSize: 11, background: '#1e293b', border: '1px solid #334155', color: '#94a3b8', borderRadius: 5, cursor: 'pointer' }}
            >
              Clear
            </button>
          </>
        )}

        {/* Export */}
        <button
          onClick={handleExport}
          style={{
            background: '#065f46', border: '1px solid #059669', color: 'white',
            padding: '3px 12px', borderRadius: 5, fontSize: 12, cursor: 'pointer',
            marginLeft: 'auto',
          }}
        >
          ↓ Export YAML{inSelMode && selectedEntities.size > 0 ? ` (${selectedEntities.size})` : ' (all)'}
        </button>
      </div>

      {/* ── Canvas + Detail panel ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          {/* Overlay badge */}
          <div style={{
            position: 'absolute', top: 10, left: 10, zIndex: 10,
            background: '#1e1e2e', border: '1px solid #334155',
            borderRadius: 8, padding: '6px 14px', fontSize: 12, color: '#94a3b8',
            pointerEvents: 'none',
          }}>
            <strong style={{ color: 'white' }}>{model.name}</strong>
            &nbsp;·&nbsp;{visibleCount} / {model.entity_count} entities
            &nbsp;·&nbsp;{edges.length} relationships
            {(tagFilter || levelFilter !== null) && (
              <span style={{ color: '#f59e0b', marginLeft: 8 }}>
                {tagFilter && `tag: ${tagFilter}`}
                {tagFilter && levelFilter !== null && ' · '}
                {levelFilter !== null && `level: ${levelFilter}`}
              </span>
            )}
          </div>

          {/* Legend */}
          <div style={{
            position: 'absolute', bottom: 10, left: 10, zIndex: 10,
            fontSize: 10, color: '#475569', pointerEvents: 'none',
          }}>
            <span style={{ color: '#fbbf24' }}>■</span> PK &nbsp;
            <span style={{ color: '#a78bfa' }}>■</span> FK &nbsp;
            <span style={{ color: '#e2e8f0' }}>■</span> field &nbsp;
            <span style={{ color: '#f59e0b' }}>□</span> selected
          </div>

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onInit={inst => { rfRef.current = inst }}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.15 }}
            minZoom={0.1}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#1e293b" />
            <Controls style={{ background: '#1e1e2e', border: '1px solid #334155' }} />
            <MiniMap
              nodeColor={n => n.type === 'group' ? 'transparent' : '#6d28d9'}
              maskColor="rgba(0,0,0,0.7)"
              style={{ background: '#0f172a', border: '1px solid #334155' }}
            />
          </ReactFlow>
        </div>

        {/* ── Detail panel ── */}
        {selectedDetail && !inSelMode && (
          <div style={{
            width: 290, background: '#1e1e2e', borderLeft: '1px solid #334155',
            padding: '1rem', overflowY: 'auto', flexShrink: 0,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <strong style={{ fontSize: 15 }}>{selectedDetail.name}</strong>
              <button
                onClick={() => setSelectedDetail(null)}
                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}
              >×</button>
            </div>
            {selectedDetail.description && (
              <p style={{ color: '#64748b', fontSize: 12, marginBottom: '0.5rem' }}>{selectedDetail.description}</p>
            )}

            {selectedDetail.tags.length > 0 && (
              <>
                <div style={{ fontSize: 10, color: '#7c3aed', marginBottom: '0.3rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Tags</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: '0.75rem' }}>
                  {selectedDetail.tags.map(t => (
                    <button
                      key={t}
                      onClick={() => setTagFilter(t)}
                      style={{
                        fontSize: 10, background: '#0f172a', color: '#94a3b8',
                        padding: '2px 8px', borderRadius: 4, fontFamily: 'monospace',
                        border: '1px solid #334155', cursor: 'pointer',
                      }}
                      title="Click to filter by this tag"
                    >{t}</button>
                  ))}
                </div>
              </>
            )}

            <div style={{ fontSize: 10, color: '#7c3aed', marginBottom: '0.3rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Attributes</div>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', marginBottom: '1rem' }}>
              <thead>
                <tr style={{ color: '#64748b' }}>
                  <th style={{ textAlign: 'left', padding: '2px 0' }}>Field</th>
                  <th style={{ textAlign: 'left', padding: '2px 6px' }}>Type</th>
                  <th style={{ textAlign: 'right', padding: '2px 0' }}>Flags</th>
                </tr>
              </thead>
              <tbody>
                {selectedDetail.attributes.map(a => (
                  <tr key={a.name} style={{ borderTop: '1px solid #1e293b' }}>
                    <td style={{ fontFamily: 'monospace', padding: '3px 0', color: a.primary_key ? '#fbbf24' : '#e2e8f0' }}>{a.name}</td>
                    <td style={{ color: '#64748b', padding: '3px 6px' }}>{a.type}</td>
                    <td style={{ textAlign: 'right' }}>
                      {a.primary_key && <span className="badge badge-pk">PK</span>}
                      {a.nullable && <span className="badge">?</span>}
                      {a.enum.length > 0 && <span className="badge badge-enum">enum</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {selectedDetail.relationships.length > 0 && (
              <>
                <div style={{ fontSize: 10, color: '#7c3aed', marginBottom: '0.3rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Relationships</div>
                {selectedDetail.relationships.map((r, i) => (
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
    </div>
  )
}
