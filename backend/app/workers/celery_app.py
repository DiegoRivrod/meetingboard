"""
Configuración de Celery.

Por qué Celery + Redis:
- La transcripción de una reunión de 60 min tarda 20-60 min en CPU
- No se puede hacer eso en un request HTTP (timeout en ~30s)
- Celery permite encolar el job y procesarlo en background
- El frontend usa Supabase Realtime para ver el progreso sin polling manual
- Redis es el broker: guarda la cola de jobs pendientes

Celery Beat (scheduler):
- Corre jobs en horarios específicos
- Lo usamos para: marcar items vencidos (diario), refresh de vistas (cada hora),
  enviar notificaciones de deadline (diario)
"""

from celery import Celery
from app.config import get_settings

settings = get_settings()

# El broker es Redis — recibe los jobs de la API FastAPI
# El backend también es Redis — guarda los resultados de los jobs
celery_app = Celery(
    'meetingboard',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        'app.workers.transcription_task',
        'app.workers.analysis_task',
        'app.workers.scheduled_tasks',
    ],
)

celery_app.conf.update(
    # Serialización
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='America/Lima',  # Perú GMT-5
    enable_utc=True,

    # Reintentos automáticos ante fallos transitorios (red, API rate limits)
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Límites de tiempo
    # La transcripción puede tardar 1h en CPU — necesitamos un timeout generoso
    task_soft_time_limit=7200,   # 2h soft (lanza SoftTimeLimitExceeded)
    task_time_limit=7800,        # 2h 10min hard (mata el proceso)

    # Para no saturar la API de Claude con demasiados requests paralelos
    task_routes={
        'app.workers.analysis_task.*': {'queue': 'llm'},
        'app.workers.transcription_task.*': {'queue': 'transcription'},
        'app.workers.scheduled_tasks.*': {'queue': 'scheduled'},
    },

    # Celery Beat: jobs programados
    beat_schedule={
        # Marcar items vencidos a las 6am Lima todos los días
        'mark-overdue-items': {
            'task': 'app.workers.scheduled_tasks.mark_overdue_items',
            'schedule': 21600,  # 6h en segundos (cron: 0 6 * * *)
        },
        # Refresh de vistas materializadas cada hora
        'refresh-materialized-views': {
            'task': 'app.workers.scheduled_tasks.refresh_materialized_views',
            'schedule': 3600,  # 1h
        },
        # Notificaciones de deadlines a las 8am Lima
        'send-deadline-notifications': {
            'task': 'app.workers.scheduled_tasks.send_deadline_notifications',
            'schedule': 86400,  # 24h (cron: 0 8 * * *)
        },
    },
)
