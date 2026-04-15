-- ============================================================
-- MeetingBoard — Schema completo de base de datos
-- Ejecutar en Supabase: SQL Editor → New Query → Pegar y ejecutar
--
-- Por qué un schema separado ('meetingboard'):
-- - Coexiste con las tablas de AuditBoard (schema 'public') sin conflictos
-- - Permite controlar permisos por schema
-- - Facilita el respaldo o migración independiente del módulo
-- ============================================================

CREATE SCHEMA IF NOT EXISTS meetingboard;

-- Dar acceso al rol anon y authenticated de Supabase
GRANT USAGE ON SCHEMA meetingboard TO anon, authenticated, service_role;

-- ============================================================
-- TABLA: people
-- Personas que participan en reuniones.
-- Separada de auth.users porque puede incluir personas externas
-- que no tienen cuenta en el sistema.
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.people (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       TEXT NOT NULL,
    email           TEXT UNIQUE,
    department      TEXT,
    area            TEXT,
    role            TEXT,
    avatar_url      TEXT,
    is_active       BOOLEAN DEFAULT true NOT NULL,
    -- Cache de métricas actualizado por trigger/scheduled job
    adherence_rate  NUMERIC(5,2),
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at      TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX idx_people_email    ON meetingboard.people(email) WHERE email IS NOT NULL;
CREATE INDEX idx_people_area     ON meetingboard.people(area) WHERE area IS NOT NULL;
CREATE INDEX idx_people_active   ON meetingboard.people(is_active);

-- ============================================================
-- TABLA: meetings
-- Una reunión = una grabación + su metadata + estado del pipeline
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.meetings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    description     TEXT,
    platform        TEXT NOT NULL DEFAULT 'manual'
                    CHECK (platform IN ('zoom', 'teams', 'google_meet', 'manual')),

    meeting_date    TIMESTAMPTZ NOT NULL,
    duration_seconds INTEGER,

    -- Archivo en Supabase Storage (path relativo dentro del bucket)
    recording_url        TEXT,
    recording_size_bytes BIGINT,
    recording_format     TEXT,

    -- Estado del pipeline: uploaded → queued → transcribing → transcribed
    --                       → analyzing → analyzed | failed | archived
    status          TEXT NOT NULL DEFAULT 'uploaded'
                    CHECK (status IN (
                        'uploaded', 'queued', 'transcribing', 'transcribed',
                        'analyzing', 'analyzed', 'failed', 'archived'
                    )),
    processing_error        TEXT,
    processing_started_at   TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,

    -- IDs de plataformas externas (para deduplicación en webhooks)
    zoom_meeting_id     TEXT,
    zoom_recording_id   TEXT,
    teams_meeting_id    TEXT,

    organizer_id        UUID REFERENCES meetingboard.people(id) ON DELETE SET NULL,
    participant_count   INTEGER,

    created_by          UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at          TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX idx_meetings_status       ON meetingboard.meetings(status);
CREATE INDEX idx_meetings_platform     ON meetingboard.meetings(platform);
CREATE INDEX idx_meetings_date         ON meetingboard.meetings(meeting_date DESC);
CREATE INDEX idx_meetings_zoom_id      ON meetingboard.meetings(zoom_meeting_id) WHERE zoom_meeting_id IS NOT NULL;
CREATE INDEX idx_meetings_teams_id     ON meetingboard.meetings(teams_meeting_id) WHERE teams_meeting_id IS NOT NULL;

-- ============================================================
-- TABLA: meeting_participants
-- Muchos-a-muchos: personas que asistieron a cada reunión.
-- También guarda el mapping speaker_label → person (post-diarización).
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.meeting_participants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id      UUID NOT NULL REFERENCES meetingboard.meetings(id) ON DELETE CASCADE,
    person_id       UUID NOT NULL REFERENCES meetingboard.people(id) ON DELETE CASCADE,
    -- Label del sistema de diarización: "SPEAKER_00", "SPEAKER_01", etc.
    speaker_label   TEXT,
    joined_at       TIMESTAMPTZ,
    left_at         TIMESTAMPTZ,
    participation_duration_seconds INTEGER,
    -- true cuando el usuario confirma manualmente el mapping speaker → persona
    is_confirmed    BOOLEAN DEFAULT false NOT NULL,
    UNIQUE(meeting_id, person_id)
);

CREATE INDEX idx_participants_meeting ON meetingboard.meeting_participants(meeting_id);
CREATE INDEX idx_participants_person  ON meetingboard.meeting_participants(person_id);

-- ============================================================
-- TABLA: transcriptions
-- Metadata de la transcripción de cada reunión.
-- Los segmentos (el texto real) van en transcription_segments.
-- Separado para poder consultar metadata sin cargar miles de segmentos.
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.transcriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id      UUID NOT NULL REFERENCES meetingboard.meetings(id) ON DELETE CASCADE,
    whisper_model   TEXT NOT NULL DEFAULT 'large-v3',
    language        TEXT NOT NULL DEFAULT 'es',
    transcription_engine TEXT NOT NULL DEFAULT 'faster-whisper',
    word_count      INTEGER,
    duration_seconds INTEGER,
    confidence_avg  NUMERIC(4,3),
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(meeting_id)
);

-- ============================================================
-- TABLA: transcription_segments
-- El texto real de la transcripción, segmentado por hablante y tiempo.
-- Esta es la tabla más grande del sistema.
-- El índice GIN permite búsqueda full-text en español ("buscar 'presupuesto'").
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.transcription_segments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcription_id UUID NOT NULL REFERENCES meetingboard.transcriptions(id) ON DELETE CASCADE,
    meeting_id      UUID NOT NULL REFERENCES meetingboard.meetings(id) ON DELETE CASCADE,
    segment_index   INTEGER NOT NULL,
    speaker_label   TEXT,
    person_id       UUID REFERENCES meetingboard.people(id) ON DELETE SET NULL,
    start_time      NUMERIC(10,3) NOT NULL,
    end_time        NUMERIC(10,3) NOT NULL,
    text            TEXT NOT NULL,
    confidence      NUMERIC(4,3),
    -- Columna generada para búsqueda full-text en español
    text_search TSVECTOR GENERATED ALWAYS AS (to_tsvector('spanish', text)) STORED
);

CREATE INDEX idx_segments_transcription ON meetingboard.transcription_segments(transcription_id);
CREATE INDEX idx_segments_meeting       ON meetingboard.transcription_segments(meeting_id);
CREATE INDEX idx_segments_speaker       ON meetingboard.transcription_segments(speaker_label);
CREATE INDEX idx_segments_time          ON meetingboard.transcription_segments(start_time, end_time);
CREATE INDEX idx_segments_fts           ON meetingboard.transcription_segments USING GIN(text_search);

-- ============================================================
-- TABLA: ai_analyses
-- Resultado del análisis LLM de cada reunión.
-- Separado de meetings para no hinchar la tabla principal.
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.ai_analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id      UUID NOT NULL REFERENCES meetingboard.meetings(id) ON DELETE CASCADE,
    llm_model       TEXT NOT NULL DEFAULT 'claude-sonnet-4-6',
    llm_version     TEXT,
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
    executive_summary TEXT,
    meeting_sentiment TEXT CHECK (meeting_sentiment IN ('positive', 'neutral', 'tense', 'unproductive')),
    topics_discussed  TEXT[],
    raw_llm_response  JSONB,
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(meeting_id)
);

-- ============================================================
-- TABLA: action_items
-- El corazón del sistema. Cada compromiso/tarea/decisión extraído.
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.action_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id      UUID NOT NULL REFERENCES meetingboard.meetings(id) ON DELETE CASCADE,
    analysis_id     UUID REFERENCES meetingboard.ai_analyses(id) ON DELETE SET NULL,

    item_type       TEXT NOT NULL DEFAULT 'action_item'
                    CHECK (item_type IN ('action_item', 'decision', 'commitment', 'risk', 'information')),

    title           TEXT NOT NULL,
    description     TEXT,
    -- Cita textual de la transcripción que originó este item
    context_quote   TEXT,
    -- Segundo en la grabación donde se dijo (para enlazar al video)
    context_timestamp NUMERIC(10,3),

    assignee_id     UUID REFERENCES meetingboard.people(id) ON DELETE SET NULL,
    -- Nombre tal como lo extrajo el LLM (antes de resolver a person_id)
    assignee_name_raw TEXT,
    due_date        DATE,
    due_date_raw    TEXT,       -- Texto original: "el próximo viernes"

    -- Estado del Kanban
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN (
                        'pending', 'in_progress', 'in_review',
                        'completed', 'overdue', 'cancelled'
                    )),

    completed_at        TIMESTAMPTZ,
    completed_by        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    completion_notes    TEXT,

    -- Métricas de adherencia (calculadas automáticamente)
    was_on_time         BOOLEAN,
    days_overdue        INTEGER,

    -- Metadata de IA
    ai_confidence       NUMERIC(4,3),
    is_ai_generated     BOOLEAN NOT NULL DEFAULT true,
    was_manually_edited BOOLEAN NOT NULL DEFAULT false,

    priority    TEXT NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    tags        TEXT[],

    created_at  TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX idx_action_items_meeting   ON meetingboard.action_items(meeting_id);
CREATE INDEX idx_action_items_assignee  ON meetingboard.action_items(assignee_id) WHERE assignee_id IS NOT NULL;
CREATE INDEX idx_action_items_status    ON meetingboard.action_items(status);
CREATE INDEX idx_action_items_due_date  ON meetingboard.action_items(due_date) WHERE due_date IS NOT NULL;
CREATE INDEX idx_action_items_type      ON meetingboard.action_items(item_type);
CREATE INDEX idx_action_items_priority  ON meetingboard.action_items(priority);

-- ============================================================
-- TABLA: action_item_updates
-- Audit trail inmutable. Cada cambio en un action item se registra aquí.
-- NO tiene CASCADE DELETE — es un registro permanente de la historia.
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.action_item_updates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_item_id  UUID NOT NULL REFERENCES meetingboard.action_items(id) ON DELETE CASCADE,
    updated_by      UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    field_changed   TEXT NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    change_note     TEXT,
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX idx_updates_action_item ON meetingboard.action_item_updates(action_item_id);

-- ============================================================
-- TABLA: notifications
-- Cola de notificaciones pendientes de enviar por email.
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       UUID REFERENCES meetingboard.people(id) ON DELETE CASCADE,
    action_item_id  UUID REFERENCES meetingboard.action_items(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL
                    CHECK (notification_type IN (
                        'deadline_approaching', 'overdue', 'assigned',
                        'status_changed', 'meeting_analyzed'
                    )),
    channel         TEXT NOT NULL DEFAULT 'email'
                    CHECK (channel IN ('email', 'in_app', 'webhook')),
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'sent', 'failed', 'skipped')),
    sent_at         TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX idx_notifications_person      ON meetingboard.notifications(person_id);
CREATE INDEX idx_notifications_status      ON meetingboard.notifications(status);
CREATE INDEX idx_notifications_action_item ON meetingboard.notifications(action_item_id);

-- ============================================================
-- TABLA: webhook_events
-- Log de eventos recibidos de Zoom/Teams para idempotencia.
-- UNIQUE(source, event_id) previene procesar el mismo evento dos veces.
-- ============================================================
CREATE TABLE IF NOT EXISTS meetingboard.webhook_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source      TEXT NOT NULL CHECK (source IN ('zoom', 'teams', 'github')),
    event_type  TEXT NOT NULL,
    event_id    TEXT,
    payload     JSONB NOT NULL,
    status      TEXT NOT NULL DEFAULT 'received'
                CHECK (status IN ('received', 'processed', 'failed', 'ignored')),
    processed_at    TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(source, event_id)
);

CREATE INDEX idx_webhook_events_source ON meetingboard.webhook_events(source);
CREATE INDEX idx_webhook_events_status ON meetingboard.webhook_events(status);

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Trigger: actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION meetingboard.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_meetings_updated_at
    BEFORE UPDATE ON meetingboard.meetings
    FOR EACH ROW EXECUTE FUNCTION meetingboard.set_updated_at();

CREATE TRIGGER trg_action_items_updated_at
    BEFORE UPDATE ON meetingboard.action_items
    FOR EACH ROW EXECUTE FUNCTION meetingboard.set_updated_at();

CREATE TRIGGER trg_people_updated_at
    BEFORE UPDATE ON meetingboard.people
    FOR EACH ROW EXECUTE FUNCTION meetingboard.set_updated_at();

-- Trigger: calcular was_on_time y days_overdue al completar un action item
CREATE OR REPLACE FUNCTION meetingboard.on_action_item_completed()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Solo actuar cuando el status cambia a 'completed'
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.completed_at = now();
        -- was_on_time: se completó antes o en la fecha límite
        NEW.was_on_time = (
            NEW.due_date IS NULL OR
            CURRENT_DATE <= NEW.due_date
        );
        -- days_overdue: 0 si fue a tiempo, días de retraso si fue tarde
        NEW.days_overdue = GREATEST(
            0,
            CURRENT_DATE - COALESCE(NEW.due_date, CURRENT_DATE)
        );
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_action_item_completed
    BEFORE UPDATE ON meetingboard.action_items
    FOR EACH ROW EXECUTE FUNCTION meetingboard.on_action_item_completed();

-- Función: marcar items vencidos (llamada por Celery Beat diario)
CREATE OR REPLACE FUNCTION meetingboard.update_overdue_items()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    UPDATE meetingboard.action_items
    SET
        status = 'overdue',
        days_overdue = CURRENT_DATE - due_date,
        updated_at = now()
    WHERE
        status IN ('pending', 'in_progress', 'in_review')
        AND due_date IS NOT NULL
        AND due_date < CURRENT_DATE;
END;
$$;

-- ============================================================
-- VISTAS MATERIALIZADAS
-- Se refrescan cada hora via Celery Beat.
-- Permiten que el Dashboard cargue en <50ms.
-- ============================================================

-- Vista: adherencia por persona
CREATE MATERIALIZED VIEW IF NOT EXISTS meetingboard.mv_person_adherence AS
SELECT
    p.id                AS person_id,
    p.full_name,
    p.department,
    p.area,
    COUNT(ai.id)        AS total_items,
    COUNT(ai.id) FILTER (WHERE ai.status = 'completed')                     AS completed_items,
    COUNT(ai.id) FILTER (WHERE ai.status = 'overdue')                       AS overdue_items,
    COUNT(ai.id) FILTER (WHERE ai.was_on_time = true)                       AS on_time_items,
    COUNT(ai.id) FILTER (WHERE ai.was_on_time = false AND ai.status = 'completed') AS late_items,
    ROUND(
        COUNT(ai.id) FILTER (WHERE ai.status = 'completed')::NUMERIC /
        NULLIF(COUNT(ai.id), 0) * 100, 2
    )                   AS adherence_rate,
    ROUND(
        COUNT(ai.id) FILTER (WHERE ai.was_on_time = true)::NUMERIC /
        NULLIF(COUNT(ai.id) FILTER (WHERE ai.status = 'completed'), 0) * 100, 2
    )                   AS on_time_rate
FROM meetingboard.people p
LEFT JOIN meetingboard.action_items ai
    ON ai.assignee_id = p.id
    AND ai.item_type IN ('action_item', 'commitment')
GROUP BY p.id, p.full_name, p.department, p.area;

CREATE UNIQUE INDEX ON meetingboard.mv_person_adherence(person_id);

-- Vista: KPIs globales por mes
CREATE MATERIALIZED VIEW IF NOT EXISTS meetingboard.mv_monthly_kpis AS
SELECT
    DATE_TRUNC('month', m.meeting_date)     AS month,
    COUNT(DISTINCT m.id)                    AS meetings_processed,
    COUNT(ai.id)                            AS total_action_items,
    COUNT(ai.id) FILTER (WHERE ai.status = 'completed')  AS completed_items,
    COUNT(ai.id) FILTER (WHERE ai.status = 'overdue')    AS overdue_items,
    ROUND(AVG(ai.days_overdue) FILTER (WHERE ai.days_overdue > 0), 1) AS avg_days_overdue,
    ROUND(
        COUNT(ai.id) FILTER (WHERE ai.was_on_time = true)::NUMERIC /
        NULLIF(COUNT(ai.id) FILTER (WHERE ai.status = 'completed'), 0) * 100, 2
    )                                       AS global_on_time_rate
FROM meetingboard.meetings m
LEFT JOIN meetingboard.action_items ai ON ai.meeting_id = m.id
WHERE m.status = 'analyzed'
GROUP BY DATE_TRUNC('month', m.meeting_date)
ORDER BY month DESC;

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- Habilitar RLS en todas las tablas para que Supabase enforce permisos.
-- La lógica de permisos actual: cualquier usuario autenticado puede ver todo.
-- Se puede refinar en fases futuras para separar por empresa/equipo.
-- ============================================================

ALTER TABLE meetingboard.people              ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetingboard.meetings            ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetingboard.meeting_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetingboard.transcriptions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetingboard.transcription_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetingboard.ai_analyses         ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetingboard.action_items        ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetingboard.action_item_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetingboard.notifications       ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetingboard.webhook_events      ENABLE ROW LEVEL SECURITY;

-- Políticas: usuarios autenticados tienen acceso completo
-- El backend usa service_role (bypass RLS) para operaciones de workers

CREATE POLICY "authenticated users can read" ON meetingboard.people
    FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated users can write" ON meetingboard.people
    FOR ALL TO authenticated USING (true);

CREATE POLICY "authenticated users can read meetings" ON meetingboard.meetings
    FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated users can write meetings" ON meetingboard.meetings
    FOR ALL TO authenticated USING (true);

CREATE POLICY "authenticated users can read action_items" ON meetingboard.action_items
    FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated users can write action_items" ON meetingboard.action_items
    FOR ALL TO authenticated USING (true);

CREATE POLICY "authenticated users can read action_item_updates" ON meetingboard.action_item_updates
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated users can read analytics" ON meetingboard.transcriptions
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated users can read segments" ON meetingboard.transcription_segments
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated users can read analyses" ON meetingboard.ai_analyses
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated users can read participants" ON meetingboard.meeting_participants
    FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated users can write participants" ON meetingboard.meeting_participants
    FOR ALL TO authenticated USING (true);

-- ============================================================
-- GRANTS — dar permisos al schema a los roles de Supabase
-- ============================================================

GRANT ALL ON ALL TABLES    IN SCHEMA meetingboard TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA meetingboard TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA meetingboard TO authenticated;
GRANT INSERT, UPDATE, DELETE ON
    meetingboard.people,
    meetingboard.meetings,
    meetingboard.meeting_participants,
    meetingboard.action_items,
    meetingboard.action_item_updates,
    meetingboard.notifications
TO authenticated;
