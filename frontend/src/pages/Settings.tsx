/**
 * Settings — Configuración de integraciones (Zoom, Teams) y notificaciones.
 *
 * Fase 0: Estructura de secciones.
 * Fase 5/6: Se conectará con Zoom OAuth y Teams Graph API.
 */

interface IntegrationCard {
  name: string
  description: string
  phase: string
  icon: string
  status: 'pending' | 'active' | 'error'
}

const INTEGRATIONS: IntegrationCard[] = [
  {
    name: 'Zoom',
    description: 'Ingesta automática de grabaciones via webhook. Cuando termina una grabación en Zoom, MeetingBoard la descarga y procesa automáticamente.',
    phase: 'Fase 5',
    icon: '📹',
    status: 'pending',
  },
  {
    name: 'Microsoft Teams',
    description: 'Sincronización de grabaciones desde OneDrive/SharePoint via Microsoft Graph API. Polling cada 30 minutos.',
    phase: 'Fase 6',
    icon: '💼',
    status: 'pending',
  },
  {
    name: 'Notificaciones Email',
    description: 'Alertas automáticas 48h antes de un deadline y cuando se vence. Usa Resend.com (100 emails/día gratis).',
    phase: 'Fase 4',
    icon: '📧',
    status: 'pending',
  },
]

export default function Settings() {
  return (
    <div className="space-y-6 max-w-2xl">
      {/* Integraciones */}
      <div>
        <h2 className="text-sm font-semibold text-slate-200 mb-4">
          Integraciones
        </h2>
        <div className="space-y-3">
          {INTEGRATIONS.map((integration) => (
            <div key={integration.name} className="card p-5">
              <div className="flex items-start gap-4">
                <span className="text-2xl">{integration.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-200">
                      {integration.name}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-600 font-mono bg-surface-200
                                       px-2 py-0.5 rounded">
                        {integration.phase}
                      </span>
                      <span className="flex items-center gap-1 text-xs text-slate-500">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                        No configurado
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    {integration.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sobre el sistema */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-slate-200 mb-4">
          Acerca del sistema
        </h2>
        <dl className="space-y-2 text-xs">
          {[
            ['Versión',          '0.1.0 — Fase 0 (Infraestructura)'],
            ['Transcripción',    'faster-whisper large-v3 (local, privado)'],
            ['Diarización',      'pyannote/speaker-diarization-3.1'],
            ['Análisis LLM',     'Claude claude-sonnet-4-6 via API'],
            ['Base de datos',    'Supabase PostgreSQL — schema meetingboard'],
            ['Job queue',        'Celery 5 + Redis'],
            ['Notificaciones',   'Resend.com'],
          ].map(([key, val]) => (
            <div key={key} className="flex gap-3">
              <dt className="text-slate-500 w-36 flex-shrink-0">{key}</dt>
              <dd className="text-slate-300 font-mono">{val}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  )
}
