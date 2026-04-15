"""
Router de Meetings.

Maneja:
- CRUD básico de reuniones
- Upload de archivos de grabación
- Consulta de transcripciones
- Mapeo de speaker labels a personas reales

La lógica de negocio (transcripción, análisis) vive en app/services/.
Los endpoints solo validan y delegan.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime
from loguru import logger

from app.config import get_settings
from app.database import get_supabase_admin

router = APIRouter()
settings = get_settings()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class MeetingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    platform: str = 'manual'
    meeting_date: datetime


class SpeakerMapping(BaseModel):
    speaker_label: str  # "SPEAKER_00"
    person_id: str      # UUID de la persona


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get('')
async def list_meetings(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50,
):
    """Lista reuniones, opcionalmente filtradas por estado o plataforma."""
    db = get_supabase_admin()
    query = db.schema('meetingboard').table('meetings').select(
        '*, organizer:people(full_name, area)'
    ).order('meeting_date', desc=True).limit(limit)

    if status:
        query = query.eq('status', status)
    if platform:
        query = query.eq('platform', platform)

    result = query.execute()
    return result.data


@router.get('/{meeting_id}')
async def get_meeting(meeting_id: str):
    """Detalle de una reunión con conteo de action items."""
    db = get_supabase_admin()
    result = db.schema('meetingboard').table('meetings').select(
        '*, organizer:people(full_name, area, email), '
        'participants:meeting_participants(*, person:people(full_name, email, area))'
    ).eq('id', meeting_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail='Reunión no encontrada')
    return result.data


@router.post('')
async def create_meeting(body: MeetingCreate):
    """Crea el registro de una reunión antes de subir el archivo."""
    db = get_supabase_admin()
    result = db.schema('meetingboard').table('meetings').insert({
        'id': str(uuid.uuid4()),
        'title': body.title,
        'description': body.description,
        'platform': body.platform,
        'meeting_date': body.meeting_date.isoformat(),
        'status': 'uploaded',
    }).execute()
    return result.data[0]


@router.post('/{meeting_id}/upload')
async def upload_recording(
    meeting_id: str,
    file: UploadFile = File(...),
):
    """
    Sube el archivo de grabación a Supabase Storage y encola el job de transcripción.

    Flujo:
    1. Valida tipo y tamaño del archivo
    2. Sube a Supabase Storage (bucket privado)
    3. Actualiza meeting.recording_url y status → 'queued'
    4. Encola transcription_task en Celery
    5. Retorna inmediatamente (el procesamiento es asíncrono)
    """
    # Validación de tipo
    allowed_types = {'video/mp4', 'audio/mp4', 'audio/m4a', 'audio/wav', 'audio/mpeg'}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f'Tipo de archivo no soportado: {file.content_type}. '
                   f'Formatos permitidos: MP4, M4A, WAV'
        )

    # Validación de tamaño (leer primero para saber el tamaño)
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f'Archivo demasiado grande: {size_mb:.1f} MB. '
                   f'Máximo: {settings.max_upload_size_mb} MB'
        )

    db = get_supabase_admin()

    # Verificar que la reunión existe
    meeting = db.schema('meetingboard').table('meetings').select('id, status').eq(
        'id', meeting_id
    ).single().execute()
    if not meeting.data:
        raise HTTPException(status_code=404, detail='Reunión no encontrada')

    # Subir a Supabase Storage
    # Ruta: recordings/{meeting_id}/{filename}
    ext = file.filename.rsplit('.', 1)[-1] if file.filename else 'mp4'
    storage_path = f'recordings/{meeting_id}/recording.{ext}'

    try:
        db.storage.from_(settings.storage_bucket).upload(
            path=storage_path,
            file=content,
            file_options={'content-type': file.content_type or 'video/mp4'},
        )
    except Exception as e:
        logger.error(f'Error subiendo archivo a Storage: {e}')
        raise HTTPException(status_code=500, detail='Error al guardar el archivo')

    # Actualizar la reunión
    db.schema('meetingboard').table('meetings').update({
        'recording_url': storage_path,
        'recording_size_bytes': len(content),
        'recording_format': ext,
        'status': 'queued',
    }).eq('id', meeting_id).execute()

    # Encolar job de transcripción en Celery
    # (disponible en Fase 1 cuando se implemente el worker)
    try:
        from app.workers.transcription_task import transcribe_meeting
        transcribe_meeting.delay(meeting_id)
        logger.info(f'Meeting {meeting_id} encolado para transcripción')
    except ImportError:
        logger.warning('Worker de Celery no disponible aún (Fase 1)')
        # Por ahora solo dejamos el status en 'queued'

    return {
        'message': 'Archivo subido correctamente. Procesamiento iniciado.',
        'meeting_id': meeting_id,
        'file_size_mb': round(size_mb, 2),
        'storage_path': storage_path,
    }


@router.get('/{meeting_id}/transcription')
async def get_transcription(meeting_id: str):
    """Devuelve la transcripción completa con segmentos por hablante."""
    db = get_supabase_admin()

    transcription = db.schema('meetingboard').table('transcriptions').select(
        '*, segments:transcription_segments('
        'segment_index, speaker_label, start_time, end_time, text, confidence, '
        'person:people(full_name)'
        ')'
    ).eq('meeting_id', meeting_id).single().execute()

    if not transcription.data:
        raise HTTPException(
            status_code=404,
            detail='Transcripción no disponible. La reunión puede estar procesándose.'
        )
    return transcription.data


@router.post('/{meeting_id}/speakers')
async def map_speaker(meeting_id: str, body: SpeakerMapping):
    """
    Mapea un speaker label (SPEAKER_00) a una persona real.
    Esto actualiza todos los segmentos de la transcripción con ese speaker label
    y crea/actualiza la entrada en meeting_participants.
    """
    db = get_supabase_admin()

    # Actualizar segmentos de transcripción
    transcription = db.schema('meetingboard').table('transcriptions').select('id').eq(
        'meeting_id', meeting_id
    ).single().execute()

    if transcription.data:
        db.schema('meetingboard').table('transcription_segments').update({
            'person_id': body.person_id,
        }).eq('transcription_id', transcription.data['id']).eq(
            'speaker_label', body.speaker_label
        ).execute()

    # Actualizar o crear participante
    existing = db.schema('meetingboard').table('meeting_participants').select('id').eq(
        'meeting_id', meeting_id
    ).eq('speaker_label', body.speaker_label).execute()

    if existing.data:
        db.schema('meetingboard').table('meeting_participants').update({
            'person_id': body.person_id,
            'is_confirmed': True,
        }).eq('id', existing.data[0]['id']).execute()
    else:
        db.schema('meetingboard').table('meeting_participants').insert({
            'meeting_id': meeting_id,
            'person_id': body.person_id,
            'speaker_label': body.speaker_label,
            'is_confirmed': True,
        }).execute()

    return {'message': 'Speaker mapeado correctamente'}


@router.delete('/{meeting_id}')
async def delete_meeting(meeting_id: str):
    """Elimina una reunión y todos sus datos relacionados (cascade en BD)."""
    db = get_supabase_admin()

    # Verificar que existe
    meeting = db.schema('meetingboard').table('meetings').select(
        'id, recording_url'
    ).eq('id', meeting_id).single().execute()

    if not meeting.data:
        raise HTTPException(status_code=404, detail='Reunión no encontrada')

    # Eliminar archivo de Storage si existe
    if meeting.data.get('recording_url'):
        try:
            db.storage.from_(settings.storage_bucket).remove(
                [meeting.data['recording_url']]
            )
        except Exception as e:
            logger.warning(f'No se pudo eliminar archivo de storage: {e}')

    # Eliminar de BD (el CASCADE se encarga del resto)
    db.schema('meetingboard').table('meetings').delete().eq(
        'id', meeting_id
    ).execute()

    return {'message': 'Reunión eliminada'}
