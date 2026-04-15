/**
 * Dashboard — Vista principal de KPIs y métricas de adherencia.
 *
 * Fase 0: Layout con placeholders informativos.
 * Fase 3: Se conectará a analyticsApi.dashboard() y analyticsApi.personAdherence()
 */

export default function Dashboard() {
  const kpiCards = [
    { label: 'Reuniones procesadas',      value: '—', unit: 'este mes',   color: 'text-blue-400',   icon: '◎' },
    { label: 'Action Items totales',       value: '—', unit: 'activos',    color: 'text-indigo-400', icon: '◈' },
    { label: 'Items vencidos',             value: '—', unit: 'sin completar', color: 'text-red-400', icon: '▲' },
    { label: 'Tasa de adherencia global',  value: '—', unit: '% cumplimiento', color: 'text-green-400', icon: '●' },
  ]

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiCards.map((k) => (
          <div key={k.label} className="card p-4">
            <div className="flex items-start justify-between mb-3">
              <span className="text-xs text-slate-500 uppercase tracking-wide font-medium leading-tight">
                {k.label}
              </span>
              <span className={`text-lg ${k.color}`}>{k.icon}</span>
            </div>
            <div className={`text-2xl font-bold font-mono ${k.color}`}>{k.value}</div>
            <div className="text-xs text-slate-600 mt-1">{k.unit}</div>
          </div>
        ))}
      </div>

      {/* Placeholder gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">
            Adherencia por Persona
          </h3>
          <div className="h-48 flex items-center justify-center border border-dashed border-white/10 rounded-lg">
            <div className="text-center">
              <div className="text-2xl text-slate-600 mb-2">◉</div>
              <p className="text-xs text-slate-600">
                Disponible en Fase 3
              </p>
              <p className="text-xs text-slate-700 mt-1">
                Requiere procesar al menos una reunión
              </p>
            </div>
          </div>
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">
            Tendencia Mensual de Compromisos
          </h3>
          <div className="h-48 flex items-center justify-center border border-dashed border-white/10 rounded-lg">
            <div className="text-center">
              <div className="text-2xl text-slate-600 mb-2">▣</div>
              <p className="text-xs text-slate-600">Disponible en Fase 3</p>
            </div>
          </div>
        </div>
      </div>

      {/* Estado del pipeline */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">
          Estado del Pipeline de Procesamiento
        </h3>
        <div className="space-y-2">
          {[
            { step: 'Subida de archivo',     status: 'ready',    desc: 'Acepta MP4, M4A, WAV' },
            { step: 'Transcripción (Whisper)', status: 'ready',  desc: 'faster-whisper large-v3' },
            { step: 'Diarización (pyannote)', status: 'ready',   desc: 'Identifica quién habló' },
            { step: 'Análisis LLM (Claude)',  status: 'ready',   desc: 'Extrae action items' },
            { step: 'Action Log',             status: 'ready',   desc: 'Kanban + tracking' },
          ].map((s) => (
            <div key={s.step} className="flex items-center gap-3 text-xs">
              <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
              <span className="text-slate-300 w-44 flex-shrink-0">{s.step}</span>
              <span className="text-slate-600">{s.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
