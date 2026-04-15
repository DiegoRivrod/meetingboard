/**
 * People — Ranking de adherencia por persona.
 *
 * Fase 0: Tabla vacía con estructura.
 * Fase 3: Se conectará a analyticsApi.personAdherence()
 */

export default function People() {
  const columns = [
    'Persona', 'Área', 'Total Items', 'Completados', 'Vencidos',
    'Adherencia', 'A Tiempo', '',
  ]

  return (
    <div className="space-y-5">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Buscar personas..."
          className="input w-56 text-sm h-9"
          disabled
        />
        <select className="input w-36 text-sm h-9 text-slate-500" disabled>
          <option>Todas las áreas</option>
        </select>
        <div className="ml-auto">
          <button className="btn-primary text-sm h-9 px-4" disabled>
            + Nueva Persona
          </button>
        </div>
      </div>

      {/* Tabla */}
      <div className="card overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/5">
              {columns.map((col) => (
                <th
                  key={col}
                  className="text-left px-4 py-3 text-slate-500 font-medium uppercase tracking-wide"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center">
                <div className="text-2xl text-slate-700 mb-3">◉</div>
                <p className="text-slate-600 text-xs">
                  Las métricas de adherencia se calcularán automáticamente al
                  procesar las primeras reuniones.
                </p>
                <p className="text-slate-700 text-xs mt-2">
                  Disponible en Fase 3 — Dashboard + Adherencia
                </p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
