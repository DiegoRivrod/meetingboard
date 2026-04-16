/**
 * MeetingsTable — Lista de reuniones con polling de estado.
 *
 * POR QUÉ polling y no Supabase Realtime en esta fase:
 * Realtime requiere configurar canales y manejar WebSockets, lo cual añade
 * complejidad. El polling cada 5 segundos es suficiente para el MVP y mucho
 * más simple de implementar correctamente. Podemos migrar a Realtime en Fase 2.
 */

import { useEffect, useRef } from 'react'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { useMeetingsStore, useFilteredMeetings } from '../../stores/meetingsStore'
import type { Meeting, MeetingStatus, MeetingPlatform } from '../../types/meeting'

// ── Configuración visual de estados ─────────────────────────────────────────

const STATUS_CONFIG: Record<MeetingStatus, { label: string; dot: string; text: string }> = {
  uploaded:     { label: 'Subido',         dot: 'bg-slate-400',              text: 'text-slate-400' },
  queued:       { label: 'En cola',        dot: 'bg-amber-400 animate-pulse', text: 'text-amber-400' },
  transcribing: { label: 'Transcribiendo', dot: 'bg-blue-400 animate-pulse',  text: 'text-blue-400' },
  transcribed:  { label: 'Transcripto',    dot: 'bg-purple-400',              text: 'text-purple-400' },
  analyzing:    { label: 'Analizando',     dot: 'bg-blue-400 animate-pulse',  text: 'text-blue-400' },
  analyzed:     { label: 'Analizado',      dot: 'bg-green-400',               text: 'text-green-400' },
  failed:       { label: 'Error',          dot: 'bg-red-400',                 text: 'text-red-400' },
  archived:     { label: 'Archivado',      dot: 'bg-slate-600',               text: 'text-slate-500' },
}

const PLATFORM_ICON: Record<MeetingPlatform, string> = {
  zoom:        '🎥',
  teams:       '💼',
  google_meet: '🟢',
  manual:      '🎙️',
}

// Estados que siguen en proceso — necesitan polling
const IN_PROGRESS_STATUSES: MeetingStatus[] = ['queued', 'transcribing', 'transcribed', 'analyzing']

function formatDuration(seconds?: number) {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

// ── Componente principal ─────────────────────────────────────────────────────

export default function MeetingsTable() {
  const { loading, error, filterStatus, filterPlatform, searchQuery,
          setFilterStatus, setFilterPlatform, setSearchQuery, fetchMeetings } = useMeetingsStore()
  const meetings = useFilteredMeetings()
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Carga inicial
  useEffect(() => {
    fetchMeetings()
  }, [fetchMeetings, filterStatus, filterPlatform])

  // Polling: se activa solo si hay reuniones en proceso
  useEffect(() => {
    const hasInProgress = meetings.some((m) => IN_PROGRESS_STATUSES.includes(m.status))

    if (hasInProgress && !pollRef.current) {
      pollRef.current = setInterval(() => fetchMeetings(), 5_000)
    } else if (!hasInProgress && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [meetings, fetchMeetings])

  return (
    <div className="space-y-4">
      {/* Toolbar ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Buscar reuniones..."
          className="input w-56 text-sm h-9"
        />

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as any)}
          className="input w-44 text-sm h-9"
        >
          <option value="all">Todos los estados</option>
          {Object.entries(STATUS_CONFIG).map(([value, cfg]) => (
            <option key={value} value={value}>
              {cfg.label}
            </option>
          ))}
        </select>

        <select
          value={filterPlatform}
          onChange={(e) => setFilterPlatform(e.target.value as any)}
          className="input w-44 text-sm h-9"
        >
          <option value="all">Todas las plataformas</option>
          <option value="zoom">Zoom</option>
          <option value="teams">Teams</option>
          <option value="google_meet">Google Meet</option>
          <option value="manual">Manual</option>
        </select>

        {loading && (
          <span className="text-xs text-slate-500 animate-pulse">Actualizando...</span>
        )}
      </div>

      {/* Error ────────────────────────────────────────────────────────────── */}
      {error && (
        <div className="card p-4 border-red-500/30 bg-red-500/5">
          <p className="text-red-400 text-sm">{error}</p>
          <button onClick={fetchMeetings} className="text-xs text-red-300 underline mt-1">
            Reintentar
          </button>
        </div>
      )}

      {/* Tabla ────────────────────────────────────────────────────────────── */}
      {!error && (
        <div className="card overflow-hidden">
          {meetings.length === 0 ? (
            <EmptyState loading={loading} hasFilters={filterStatus !== 'all' || filterPlatform !== 'all' || !!searchQuery} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/60">
                    <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase tracking-wide">
                      Reunión
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase tracking-wide">
                      Fecha
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase tracking-wide">
                      Duración
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase tracking-wide">
                      Estado
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase tracking-wide">
                      Items
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {meetings.map((meeting) => (
                    <MeetingRow key={meeting.id} meeting={meeting} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Fila individual ──────────────────────────────────────────────────────────

function MeetingRow({ meeting }: { meeting: Meeting }) {
  const status = STATUS_CONFIG[meeting.status]
  const icon = PLATFORM_ICON[meeting.platform]

  return (
    <tr className="hover:bg-slate-800/40 transition-colors">
      {/* Título + plataforma */}
      <td className="py-3 px-4">
        <div className="flex items-start gap-2.5">
          <span className="text-lg leading-none mt-0.5">{icon}</span>
          <div>
            <p className="font-medium text-slate-100 leading-tight">{meeting.title}</p>
            {meeting.description && (
              <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{meeting.description}</p>
            )}
          </div>
        </div>
      </td>

      {/* Fecha */}
      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
        {format(new Date(meeting.meeting_date), 'd MMM yyyy', { locale: es })}
      </td>

      {/* Duración */}
      <td className="py-3 px-4 text-slate-400 whitespace-nowrap tabular-nums">
        {formatDuration(meeting.duration_seconds)}
      </td>

      {/* Estado */}
      <td className="py-3 px-4">
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${status.text}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${status.dot}`} />
          {status.label}
        </span>
        {meeting.status === 'failed' && meeting.processing_error && (
          <p className="text-xs text-red-400/70 mt-0.5 line-clamp-1">{meeting.processing_error}</p>
        )}
      </td>

      {/* Action items */}
      <td className="py-3 px-4">
        {meeting.action_items_count != null && meeting.action_items_count > 0 ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-indigo-400">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
            {meeting.action_items_count} items
          </span>
        ) : meeting.status === 'analyzed' ? (
          <span className="text-xs text-slate-600">Sin items</span>
        ) : (
          <span className="text-xs text-slate-700">—</span>
        )}
      </td>
    </tr>
  )
}

// ── Estado vacío ─────────────────────────────────────────────────────────────

function EmptyState({ loading, hasFilters }: { loading: boolean; hasFilters: boolean }) {
  return (
    <div className="py-16 text-center">
      {loading ? (
        <p className="text-slate-500 text-sm">Cargando reuniones...</p>
      ) : hasFilters ? (
        <>
          <p className="text-slate-400 text-sm font-medium">Sin resultados</p>
          <p className="text-slate-600 text-xs mt-1">Prueba ajustando los filtros</p>
        </>
      ) : (
        <>
          <div className="text-4xl mb-3">🎙️</div>
          <p className="text-slate-400 text-sm font-medium">Aún no hay reuniones</p>
          <p className="text-slate-600 text-xs mt-1">
            Sube tu primera grabación con el botón "Nueva Reunión"
          </p>
        </>
      )}
    </div>
  )
}
