"""
Router de Action Items.

CRUD completo + cambio de status con audit trail.
El audit trail es crítico: cada cambio queda registrado en action_item_updates
para poder responder "¿quién cambió esto y cuándo?".
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
import uuid
from loguru import logger

from app.database import get_supabase_admin

router = APIRouter()


class ActionItemCreate(BaseModel):
    meeting_id: str
    item_type: str = 'action_item'
    title: str
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[date] = None
    priority: str = 'medium'
    tags: Optional[list[str]] = None


class ActionItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[str] = None
    tags: Optional[list[str]] = None
    change_note: Optional[str] = None  # Para el audit trail


class StatusUpdate(BaseModel):
    status: str
    change_note: Optional[str] = None
    completion_notes: Optional[str] = None


@router.get('')
async def list_action_items(
    meeting_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    status: Optional[str] = None,
    item_type: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 200,
):
    """Lista action items con filtros. Para el tablero Kanban."""
    db = get_supabase_admin()
    query = db.schema('meetingboard').table('action_items').select(
        '*, assignee:people(full_name, email, area), '
        'meeting:meetings(title, meeting_date)'
    ).order('created_at', desc=True).limit(limit)

    if meeting_id:
        query = query.eq('meeting_id', meeting_id)
    if assignee_id:
        query = query.eq('assignee_id', assignee_id)
    if status:
        query = query.eq('status', status)
    if item_type:
        query = query.eq('item_type', item_type)
    if priority:
        query = query.eq('priority', priority)

    result = query.execute()
    return result.data


@router.get('/{item_id}')
async def get_action_item(item_id: str):
    """Detalle completo de un action item con historial de cambios."""
    db = get_supabase_admin()
    result = db.schema('meetingboard').table('action_items').select(
        '*, assignee:people(full_name, email, area), '
        'meeting:meetings(title, meeting_date), '
        'updates:action_item_updates(field_changed, old_value, new_value, change_note, created_at)'
    ).eq('id', item_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail='Action item no encontrado')
    return result.data


@router.post('')
async def create_action_item(body: ActionItemCreate):
    """Crea un action item manualmente (no generado por IA)."""
    db = get_supabase_admin()
    result = db.schema('meetingboard').table('action_items').insert({
        'id': str(uuid.uuid4()),
        'meeting_id': body.meeting_id,
        'item_type': body.item_type,
        'title': body.title,
        'description': body.description,
        'assignee_id': body.assignee_id,
        'due_date': body.due_date.isoformat() if body.due_date else None,
        'priority': body.priority,
        'tags': body.tags,
        'is_ai_generated': False,
        'was_manually_edited': False,
    }).execute()
    return result.data[0]


@router.patch('/{item_id}')
async def update_action_item(item_id: str, body: ActionItemUpdate):
    """
    Actualiza campos de un action item y registra los cambios en el audit trail.

    Por qué el audit trail:
    - Permite responder "¿quién cambió el deadline?" en caso de disputas
    - Da visibilidad de la historia de cada compromiso
    - Es inmutable (no se puede borrar un registro de actualización)
    """
    db = get_supabase_admin()

    # Obtener estado actual para el audit trail
    current = db.schema('meetingboard').table('action_items').select('*').eq(
        'id', item_id
    ).single().execute()
    if not current.data:
        raise HTTPException(status_code=404, detail='Action item no encontrado')

    updates_to_log = []
    patch_data = {'was_manually_edited': True}

    # Registrar cada campo que cambia
    for field in ['title', 'description', 'assignee_id', 'due_date', 'priority']:
        new_val = getattr(body, field, None)
        if new_val is not None:
            old_val = current.data.get(field)
            new_val_str = new_val.isoformat() if hasattr(new_val, 'isoformat') else str(new_val)
            if str(old_val) != new_val_str:
                updates_to_log.append({
                    'action_item_id': item_id,
                    'field_changed': field,
                    'old_value': str(old_val) if old_val is not None else None,
                    'new_value': new_val_str,
                    'change_note': body.change_note,
                })
                patch_data[field] = new_val.isoformat() if hasattr(new_val, 'isoformat') else new_val

    if body.tags is not None:
        patch_data['tags'] = body.tags

    # Aplicar cambios
    if len(patch_data) > 1:  # Más que solo was_manually_edited
        db.schema('meetingboard').table('action_items').update(patch_data).eq(
            'id', item_id
        ).execute()

    # Insertar audit trail
    if updates_to_log:
        db.schema('meetingboard').table('action_item_updates').insert(updates_to_log).execute()

    return await get_action_item(item_id)


@router.patch('/{item_id}/status')
async def update_status(item_id: str, body: StatusUpdate):
    """
    Cambia el status de un action item.
    Endpoint separado porque es la operación más frecuente (drag & drop en Kanban).

    Cuando el status pasa a 'completed', el trigger de BD calcula was_on_time.
    """
    valid_statuses = {'pending', 'in_progress', 'in_review', 'completed', 'overdue', 'cancelled'}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f'Status inválido: {body.status}')

    db = get_supabase_admin()

    current = db.schema('meetingboard').table('action_items').select('status').eq(
        'id', item_id
    ).single().execute()
    if not current.data:
        raise HTTPException(status_code=404, detail='Action item no encontrado')

    old_status = current.data['status']

    patch = {'status': body.status}
    if body.completion_notes:
        patch['completion_notes'] = body.completion_notes

    db.schema('meetingboard').table('action_items').update(patch).eq('id', item_id).execute()

    # Audit trail del cambio de status
    db.schema('meetingboard').table('action_item_updates').insert({
        'action_item_id': item_id,
        'field_changed': 'status',
        'old_value': old_status,
        'new_value': body.status,
        'change_note': body.change_note,
    }).execute()

    logger.info(f'Action item {item_id}: {old_status} → {body.status}')
    return {'message': 'Status actualizado', 'status': body.status}


@router.delete('/{item_id}')
async def delete_action_item(item_id: str):
    """Solo se pueden eliminar items creados manualmente (is_ai_generated=False)."""
    db = get_supabase_admin()

    item = db.schema('meetingboard').table('action_items').select(
        'id, is_ai_generated'
    ).eq('id', item_id).single().execute()

    if not item.data:
        raise HTTPException(status_code=404, detail='Action item no encontrado')

    db.schema('meetingboard').table('action_items').delete().eq('id', item_id).execute()
    return {'message': 'Action item eliminado'}
