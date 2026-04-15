/**
 * ActionLog — Tablero Kanban de compromisos detectados en reuniones.
 *
 * Fase 0: Estructura de columnas vacías con información.
 * Fase 2: Se conectará a actionItemsApi.list() con drag & drop @dnd-kit.
 */

import { KANBAN_COLUMNS, ACTION_ITEM_STATUS_LABELS } from '../types/actionItem'
import type { ActionItemStatus } from '../types/actionItem'

const COLUMN_COLORS: Record<ActionItemStatus, string> = {
  pending:     'border-slate-500/30 bg-slate-500/5',
  in_progress: 'border-blue-500/30 bg-blue-500/5',
  in_review:   'border-amber-500/30 bg-amber-500/5',
  completed:   'border-green-500/30 bg-green-500/5',
  overdue:     'border-red-500/30 bg-red-500/5',
  cancelled:   'border-slate-600/30 bg-slate-600/5',
}

const COLUMN_DOT: Record<ActionItemStatus, string> = {
  pending:     'bg-slate-400',
  in_progress: 'bg-blue-400',
  in_review:   'bg-amber-400',
  completed:   'bg-green-400',
  overdue:     'bg-red-400',
  cancelled:   'bg-slate-600',
}

export default function ActionLog() {
  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <input
          type="text"
          placeholder="Buscar action items..."
          className="input w-56 text-sm h-9"
          disabled
        />
        <select className="input w-36 text-sm h-9 text-slate-500" disabled>
          <option>Todas las reuniones</option>
        </select>
        <select className="input w-36 text-sm h-9 text-slate-500" disabled>
          <option>Todas las personas</option>
        </select>
        <select className="input w-32 text-sm h-9 text-slate-500" disabled>
          <option>Todos los tipos</option>
        </select>
        <div className="ml-auto">
          <button className="btn-primary text-sm h-9 px-4" disabled>
            + Agregar Manual
          </button>
        </div>
      </div>

      {/* Leyenda de tipos */}
      <div className="flex items-center gap-4 text-xs">
        {[
          { label: 'Tarea',      color: 'bg-indigo-400' },
          { label: 'Decisión',   color: 'bg-green-400' },
          { label: 'Compromiso', color: 'bg-amber-400' },
          { label: 'Riesgo',     color: 'bg-red-400' },
        ].map((t) => (
          <div key={t.label} className="flex items-center gap-1.5 text-slate-500">
            <span className={`w-2 h-2 rounded-sm ${t.color}`} />
            {t.label}
          </div>
        ))}
      </div>

      {/* Kanban Board */}
      <div className="flex gap-3 overflow-x-auto pb-4">
        {KANBAN_COLUMNS.map((status) => (
          <div
            key={status}
            className={`flex-shrink-0 w-64 rounded-xl border ${COLUMN_COLORS[status]} p-3`}
          >
            {/* Columna header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${COLUMN_DOT[status]}`} />
                <span className="text-xs font-semibold text-slate-300">
                  {ACTION_ITEM_STATUS_LABELS[status]}
                </span>
              </div>
              <span className="text-xs text-slate-600 font-mono bg-surface-200
                               px-1.5 py-0.5 rounded">
                0
              </span>
            </div>

            {/* Área de cards vacía */}
            <div className="min-h-32 flex items-center justify-center">
              <p className="text-xs text-slate-700 text-center">
                {status === 'pending'
                  ? 'Los action items aparecerán aquí al procesar una reunión'
                  : 'Sin items'}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
