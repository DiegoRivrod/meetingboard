# MeetingBoard

Herramienta de inteligencia de reuniones virtuales — detecta automáticamente compromisos,
decisiones y riesgos en grabaciones de Zoom y Microsoft Teams, los gestiona en un
tablero Kanban y genera KPIs de adherencia por persona y área.

## Stack Tecnológico

| Capa | Tecnología | Por qué |
|------|------------|---------|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS | Mismo stack que AuditBoard |
| Backend | Python 3.11 + FastAPI | Ecosistema ML (Whisper, pyannote) |
| Transcripción | faster-whisper large-v3 | Local, privado, $0 costo |
| Diarización | pyannote/speaker-diarization-3.1 | Identifica quién habló |
| LLM | Claude claude-sonnet-4-6 (Anthropic) | Mejor extracción en español |
| Job Queue | Celery 5 + Redis | Transcripción async (20-60 min) |
| Base de datos | Supabase PostgreSQL | Auth + Realtime + Storage integrados |
| CI/CD | GitHub Actions + Vercel + Railway | Deploy automático por branch |

## Fases de Implementación

- [x] **Fase 0** — Infraestructura base (este estado)
- [ ] **Fase 1** — Upload manual + transcripción
- [ ] **Fase 2** — Análisis LLM + Kanban Action Log
- [ ] **Fase 3** — Dashboard + Métricas de adherencia
- [ ] **Fase 4** — Notificaciones email
- [ ] **Fase 5** — Integración Zoom API
- [ ] **Fase 6** — Integración Microsoft Teams
- [ ] **Fase 7** — Producción + Observabilidad

## Setup Local (Desarrollo)

### Pre-requisitos
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado
- [Node.js 20+](https://nodejs.org/) instalado
- Cuenta en [Supabase](https://supabase.com) (gratis)
- API Key de [Anthropic](https://console.anthropic.com) (Claude)

### 1. Base de datos

1. Ir a [supabase.com](https://supabase.com) → Crear nuevo proyecto
2. Ir a **SQL Editor** → **New Query**
3. Copiar y ejecutar el contenido de `supabase/migrations/001_meetingboard_schema.sql`
4. Crear bucket de Storage: **Storage** → **New bucket** → Nombre: `meeting-recordings` → **Private**

### 2. Backend

```bash
cd backend
cp .env.example .env
# Editar .env con tus credenciales de Supabase y Anthropic

# Levantar API + Redis + Worker con Docker
docker compose up
```

La API estará disponible en: http://localhost:8000
Documentación: http://localhost:8000/docs (solo en modo DEBUG=true)

### 3. Frontend

```bash
cd frontend
cp .env.example .env.local
# Editar .env.local con tu Supabase URL y anon key

npm install
npm run dev
```

La app estará en: http://localhost:5173

## Variables de Entorno

Ver `.env.example` en `backend/` y `frontend/` para la lista completa.

## Estructura del Proyecto

```
meetingboard/
├── .github/workflows/     # CI/CD
├── frontend/              # React 19 + TypeScript
│   └── src/
│       ├── pages/         # Dashboard, Meetings, ActionLog, People, Settings
│       ├── components/    # UI, meetings, action-items, dashboard, layout
│       ├── hooks/         # useRealtimeUpdates, useMeetings, etc.
│       ├── lib/           # supabase.ts, api.ts
│       └── types/         # meeting.ts, actionItem.ts, analytics.ts
└── backend/               # Python FastAPI
    └── app/
        ├── api/           # meetings, action_items, people, analytics, webhooks
        ├── services/      # transcription, llm_analysis, zoom, teams, storage
        ├── workers/       # celery_app, transcription_task, analysis_task
        └── models/        # Pydantic schemas
```

## Decisiones Clave de Arquitectura

**¿Por qué transcripción local y no API de OpenAI Whisper?**
Las grabaciones de reuniones contienen información sensible de negocio. Procesarlas en
servidores externos viola la privacidad corporativa. Con `faster-whisper` local el costo
es $0 y los datos nunca salen de tu infraestructura.

**¿Por qué Celery + Redis?**
La transcripción de una reunión de 60 minutos puede tardar entre 20 y 60 minutos en CPU.
Un request HTTP tiene timeout de ~30s. Celery permite hacer el procesamiento en background
y Supabase Realtime notifica al frontend cuando termina, sin polling.

**¿Por qué Supabase Realtime?**
El pipeline de procesamiento es asíncrono. El frontend necesita saber cuándo la
transcripción terminó para mostrarla. Con Supabase Realtime, el frontend se suscribe
a cambios en `meetings.status` y actualiza la UI automáticamente sin necesidad de
hacer polling periódico.
