"""
Tareas programadas de Celery Beat.

Estas tareas corren en horarios definidos en celery_app.py (beat_schedule).
Son el equivalente de un cron job pero integrado con el sistema.
"""

from loguru import logger
from app.workers.celery_app import celery_app
from app.database import get_supabase_admin


@celery_app.task(name='app.workers.scheduled_tasks.mark_overdue_items')
def mark_overdue_items():
    """
    Marca como 'overdue' todos los action items cuyo deadline ya pasó.
    Corre a las 6am Lima todos los días.

    Por qué en el worker y no solo en el trigger de BD:
    - El trigger de BD solo corre cuando se actualiza una fila
    - Si nadie toca el sistema durante 1 semana, los items no se marcarían solos
    - Este task fuerza la actualización masiva a hora fija
    """
    db = get_supabase_admin()

    result = db.schema('meetingboard').rpc('update_overdue_items').execute()
    logger.info('Tarea mark_overdue_items completada')
    return {'status': 'ok'}


@celery_app.task(name='app.workers.scheduled_tasks.refresh_materialized_views')
def refresh_materialized_views():
    """
    Refresca las vistas materializadas de adherencia.
    Corre cada hora para que el Dashboard siempre tenga datos recientes.
    """
    db = get_supabase_admin()

    # Las vistas materializadas en Supabase se refrescan con REFRESH MATERIALIZED VIEW
    # Ejecutamos SQL directo via rpc
    for view in ['mv_person_adherence', 'mv_monthly_kpis']:
        try:
            db.rpc('refresh_materialized_view', {'view_name': f'meetingboard.{view}'}).execute()
            logger.info(f'Vista {view} refrescada')
        except Exception as e:
            logger.warning(f'No se pudo refrescar {view}: {e}')

    return {'status': 'ok'}


@celery_app.task(name='app.workers.scheduled_tasks.send_deadline_notifications')
def send_deadline_notifications():
    """
    Busca action items con deadline en las próximas 48h y envía emails.
    Disponible en Fase 4.
    """
    from datetime import date, timedelta

    db = get_supabase_admin()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    day_after = (date.today() + timedelta(days=2)).isoformat()

    # Buscar items próximos a vencer sin notificación enviada
    items = db.schema('meetingboard').table('action_items').select(
        '*, assignee:people(full_name, email)'
    ).in_('status', ['pending', 'in_progress']).gte('due_date', tomorrow).lte(
        'due_date', day_after
    ).execute()

    sent = 0
    for item in (items.data or []):
        assignee = item.get('assignee', {})
        if not assignee or not assignee.get('email'):
            continue

        # Verificar si ya se envió notificación para este item
        existing = db.schema('meetingboard').table('notifications').select('id').eq(
            'action_item_id', item['id']
        ).eq('notification_type', 'deadline_approaching').eq('status', 'sent').execute()

        if existing.data:
            continue

        # Encolar notificación (Fase 4: implementar envío real con Resend)
        db.schema('meetingboard').table('notifications').insert({
            'person_id': item.get('assignee_id'),
            'action_item_id': item['id'],
            'notification_type': 'deadline_approaching',
            'channel': 'email',
            'status': 'pending',
        }).execute()
        sent += 1

    logger.info(f'send_deadline_notifications: {sent} notificaciones encoladas')
    return {'notifications_queued': sent}
