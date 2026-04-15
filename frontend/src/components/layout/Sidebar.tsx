import { NavLink } from 'react-router-dom'

interface NavItem {
  to: string
  label: string
  icon: string
  description: string
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard',   label: 'Dashboard',    icon: '▣', description: 'KPIs y adherencia' },
  { to: '/meetings',    label: 'Reuniones',     icon: '◎', description: 'Grabaciones y transcripciones' },
  { to: '/action-log',  label: 'Action Log',    icon: '◈', description: 'Tablero de compromisos' },
  { to: '/people',      label: 'Personas',      icon: '◉', description: 'Ranking de cumplimiento' },
  { to: '/settings',    label: 'Configuración', icon: '◎', description: 'Zoom, Teams, notificaciones' },
]

export default function Sidebar() {
  return (
    <aside className="w-60 min-h-screen bg-surface-50 border-r border-white/5 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-accent rounded-lg flex items-center justify-center text-white font-bold text-sm">
            M
          </div>
          <div>
            <div className="text-sm font-semibold text-white">MeetingBoard</div>
            <div className="text-xs text-slate-500 font-mono">v0.1.0</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 group ${
                isActive
                  ? 'bg-accent/20 text-accent-light border border-accent/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-surface-200'
              }`
            }
          >
            <span className="text-base leading-none">{item.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="font-medium">{item.label}</div>
              <div className="text-xs text-slate-500 truncate">{item.description}</div>
            </div>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-white/5">
        <div className="text-xs text-slate-600 font-mono">
          Pipeline: <span className="text-green-400">●</span> activo
        </div>
      </div>
    </aside>
  )
}
