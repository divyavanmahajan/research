import { NavLink } from 'react-router-dom'

const links = [
  { to: '/upload', label: 'Upload Model' },
  { to: '/explorer', label: 'Explorer' },
  { to: '/graph', label: 'Graph' },
  { to: '/preview', label: 'Preview' },
  { to: '/seeds', label: 'Seeds' },
  { to: '/download', label: 'Download' },
]

export default function Nav() {
  return (
    <nav style={{
      display: 'flex', alignItems: 'center', gap: '0.25rem',
      padding: '0.75rem 1.5rem',
      borderBottom: '1px solid var(--color-border)',
      background: 'var(--color-surface)',
    }}>
      <span style={{ fontWeight: 700, marginRight: '1.5rem', color: 'var(--color-accent)' }}>
        InfoModel → DBT
      </span>
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          style={({ isActive }) => ({
            padding: '0.35rem 0.85rem',
            borderRadius: '5px',
            textDecoration: 'none',
            fontSize: '0.875rem',
            color: isActive ? 'white' : 'var(--color-muted)',
            background: isActive ? 'var(--color-accent)' : 'transparent',
          })}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
