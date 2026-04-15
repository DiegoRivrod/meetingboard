/**
 * Meetings — Lista de reuniones procesadas y en proceso.
 *
 * Fase 0: Estructura de UI completa con estado vacío informativo.
 * Fase 1: Se conectará a meetingsApi.list() y tendrá el modal de upload.
 */

import type { MeetingStatus } from '../types/meeting'

const STATUS_CONFIG: Record<MeetingStatus, { label: string; dot: string }> = {
  uploaded:     { label: 'Subido',         dot: 'bg-slate-400' },
  queued:       { label: 'En cola',        dot: 'bg-amber-400 animate-pulse' },
  transcribing: { label: 'Transcribiendo', dot: 'bg-blue-400 animate-pulse' },
  transcribed:  { label: 'Transcripto',    dot: 'bg-purple-400' },
  analyzing:    { label: 'Analizando',     dot: 'bg-blue-400 animate-pulse' },
  analyzed:     { label: 'Analizado',      dot: 'bg-green-400' },
  failed:       { label: 'Error',          dot: 'bg-red-400' },
  archived:     { label: 'Archivado',      dot: 'bg-slate-600' },
}

export default function Meetings() {
  return (
    <div className="space-y-5">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Buscar reuniones..."
            className="input w-64 text-sm h-9"
            disabled
          />
          <select className="input w-36 text-sm h-9 text-slate-500" disabled>
            <option>Todos los estados</option>
          </select>
        </div>
        <button
          className="btn-primary text-sm h-9 px-4 flex items-center gap-2"
          title="Disponible en Fase 1"
          disabled
        >
          <span>+</span>
          Nueva Reunión
        </button>
      </div>

      {/* Leyenda de estados del pipeline */}
      <div className="card p-4">
        <p className="text-xs text-slate-500 font-medium mb-3 uppercase tracking-wide">
          Pipeline de procesamiento
        </p>
        <div className="flex flex-wrap gap-4">
          {(Object.entries(STATUS_CONFIG) as [MeetingStatus, { label: string; dot: string }][]).map(
            ([, cfg]) => (
              <div key={cfg.label} className="flex items-center gap-1.5 text-xs text-slate-400">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
                {cfg.label}
              </div>
            )
          )}
        </div>
      </div>

      {/* Estado vacío */}
      <div className="card p-12 text-center">
        <div className="text-4xl text-slate-700 mb-4">◎</div>
        <h3 className="text-sm font-semibold text-slate-300 mb-2">
          No hay reuniones procesadas aún
        </h3>
        <p className="text-xs text-slate-600 max-w-md mx-auto mb-6">
          En la Fase 1 podrás subir grabaciones de Zoom o Microsoft Teams en formato
          MP4 o M4A. El sistema las transcribirá automáticamente y extraerá los
          compromisos con inteligencia artificial.
        </p>
        <div className="inline-flex flex-col items-start gap-2 text-left bg-surface-200
                        rounded-lg p-4 text-xs text-slate-500">
          <div className="font-medium text-slate-400 mb-1">Formatos soportados:</div>
          <div className="flex items-center gap-2">
            <span className="font-mono bg-surface-300 px-2 py-0.5 rounded text-slate-300">.mp4</span>
            <span>Grabación de Zoom o Teams</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono bg-surface-300 px-2 py-0.5 rounded text-slate-300">.m4a</span>
            <span>Solo audio de Zoom</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono bg-surface-300 px-2 py-0.5 rounded text-slate-300">.wav</span>
            <span>Audio genérico</span>
          </div>
        </div>
      </div>
    </div>
  )
}
