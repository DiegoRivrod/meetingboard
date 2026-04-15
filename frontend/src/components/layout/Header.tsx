import { useLocation } from 'react-router-dom'
import { supabase } from '../../lib/supabase'
import toast from 'react-hot-toast'

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/dashboard':   { title: 'Dashboard',    subtitle: 'KPIs de adherencia y cumplimiento' },
  '/meetings':    { title: 'Reuniones',     subtitle: 'Grabaciones procesadas y en proceso' },
  '/action-log':  { title: 'Action Log',    subtitle: 'Tablero Kanban de compromisos' },
  '/people':      { title: 'Personas',      subtitle: 'Ranking y métricas individuales de cumplimiento' },
  '/settings':    { title: 'Configuración', subtitle: 'Integraciones y preferencias' },
}

export default function Header() {
  const location = useLocation()
  const meta = PAGE_TITLES[location.pathname] ?? { title: 'MeetingBoard', subtitle: '' }

  async function handleLogout() {
    await supabase.auth.signOut()
    toast.success('Sesión cerrada')
  }

  return (
    <header className="h-14 bg-surface-50/80 backdrop-blur border-b border-white/5 px-6
                       flex items-center justify-between sticky top-0 z-10">
      <div>
        <h1 className="text-sm font-semibold text-white">{meta.title}</h1>
        <p className="text-xs text-slate-500">{meta.subtitle}</p>
      </div>

      <div className="flex items-center gap-3">
        {/* Indicador de procesamiento global */}
        <div className="text-xs text-slate-500 font-mono hidden sm:block">
          {new Date().toLocaleDateString('es-PE', { weekday: 'short', day: '2-digit', month: 'short' })}
        </div>

        <button
          onClick={handleLogout}
          className="text-xs text-slate-400 hover:text-slate-200 transition-colors px-2 py-1
                     rounded border border-white/10 hover:border-white/20"
        >
          Salir
        </button>
      </div>
    </header>
  )
}
