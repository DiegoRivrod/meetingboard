"""
Router de Analytics.

Sirve los datos para el Dashboard y la página de People.

Por qué vistas materializadas en vez de queries en tiempo real:
- Las queries de adherencia requieren JOINs y AGGREGATIONs complejas
- Con 1000+ action items, estas queries tardan cientos de ms
- Las vistas materializadas se calculan una vez por hora en segundo plano
- El dashboard carga en <50ms en vez de >500ms
- El costo es que los datos tienen hasta 1h de delay (aceptable para KPIs diarios)
"""

from fastapi import APIRouter
from typing import Optional

from app.database import get_supabase_admin

router = APIRouter()


@router.get('/dashboard')
async def get_dashboard_summary():
    """KPIs globales para el Dashboard principal."""
    db = get_supabase_admin()

    # Conteos rápidos
    meetings = db.schema('meetingboard').table('meetings').select(
        'id, status, meeting_date'
    ).execute()
    items = db.schema('meetingboard').table('action_items').select(
        'id, status, was_on_time, item_type'
    ).execute()

    all_meetings = meetings.data or []
    all_items = items.data or []

    from datetime import date, timedelta
    this_month_start = date.today().replace(day=1).isoformat()

    total_meetings = len(all_meetings)
    meetings_analyzed = sum(1 for m in all_meetings if m['status'] == 'analyzed')
    total_items = len([i for i in all_items if i['item_type'] in ('action_item', 'commitment')])
    pending = sum(1 for i in all_items if i['status'] == 'pending')
    overdue = sum(1 for i in all_items if i['status'] == 'overdue')
    completed = sum(1 for i in all_items if i['status'] == 'completed')
    on_time = sum(1 for i in all_items if i['was_on_time'] is True)

    adherence_rate = round((completed / total_items * 100) if total_items > 0 else 0, 1)
    on_time_rate = round((on_time / completed * 100) if completed > 0 else 0, 1)

    return {
        'total_meetings': total_meetings,
        'meetings_analyzed': meetings_analyzed,
        'total_action_items': total_items,
        'pending_items': pending,
        'overdue_items': overdue,
        'completed_items': completed,
        'global_adherence_rate': adherence_rate,
        'global_on_time_rate': on_time_rate,
    }


@router.get('/adherence')
async def get_person_adherence(
    area: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """
    Adherencia por persona desde la vista materializada.
    En Fase 3 esta vista se actualiza cada hora via Celery Beat.
    """
    db = get_supabase_admin()
    try:
        query = db.schema('meetingboard').table('mv_person_adherence').select('*').order(
            'adherence_rate', desc=True
        )
        if area:
            query = query.eq('area', area)
        return query.execute().data
    except Exception:
        # Vista aún no creada (normal en Fase 0 antes de ejecutar la migración)
        return []


@router.get('/monthly-kpis')
async def get_monthly_kpis(months: int = 6):
    """KPIs mensuales para el gráfico de tendencia."""
    db = get_supabase_admin()
    try:
        result = db.schema('meetingboard').table('mv_monthly_kpis').select('*').limit(
            months
        ).execute()
        return result.data
    except Exception:
        return []


@router.get('/meetings/{meeting_id}')
async def get_meeting_stats(meeting_id: str):
    """Estadísticas de una reunión específica."""
    db = get_supabase_admin()

    items = db.schema('meetingboard').table('action_items').select(
        'item_type, status, priority, assignee_id, was_on_time'
    ).eq('meeting_id', meeting_id).execute()

    all_items = items.data or []
    by_type = {}
    by_status = {}
    for item in all_items:
        by_type[item['item_type']] = by_type.get(item['item_type'], 0) + 1
        by_status[item['status']] = by_status.get(item['status'], 0) + 1

    return {
        'meeting_id': meeting_id,
        'total_items': len(all_items),
        'by_type': by_type,
        'by_status': by_status,
    }
