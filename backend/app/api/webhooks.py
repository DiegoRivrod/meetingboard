"""
Router de Webhooks.

Recibe eventos de Zoom y Microsoft Teams.

Seguridad crítica:
- Zoom EXIGE verificar la firma HMAC-SHA256 del request.
  Si no verificamos, cualquier persona puede enviarnos datos falsos.
- La verificación debe hacerse ANTES de procesar el payload.
- Zoom también hace un "challenge" al configurar el webhook (verificación de URL).

Idempotencia:
- Los webhooks pueden enviarse más de una vez (Zoom reintenta si no responde en 3s)
- Guardamos cada evento en webhook_events con UNIQUE(source, event_id)
- Si ya procesamos el evento, retornamos 200 sin re-procesarlo
"""

import hashlib
import hmac
import json
import uuid
from fastapi import APIRouter, Request, HTTPException, Response
from loguru import logger

from app.config import get_settings
from app.database import get_supabase_admin

router = APIRouter()
settings = get_settings()


# ─── Zoom ─────────────────────────────────────────────────────────────────────

@router.post('/zoom')
async def zoom_webhook(request: Request):
    """
    Recibe eventos de Zoom. El evento más importante es recording.completed.

    Zoom hace una verificación inicial al configurar el webhook:
    envía {"event": "endpoint.url_validation", "payload": {"plainToken": "..."}}
    y espera que respondamos con el hash del token.
    """
    body_bytes = await request.body()
    body_text = body_bytes.decode('utf-8')

    # 1. Verificar firma HMAC (obligatorio)
    _verify_zoom_signature(request, body_bytes)

    payload = json.loads(body_text)
    event_type = payload.get('event', '')

    # 2. Manejar el challenge de validación de URL de Zoom
    if event_type == 'endpoint.url_validation':
        plain_token = payload['payload']['plainToken']
        encrypted_token = hmac.new(
            settings.zoom_webhook_secret_token.encode(),
            plain_token.encode(),
            hashlib.sha256,
        ).hexdigest()
        return {'plainToken': plain_token, 'encryptedToken': encrypted_token}

    # 3. Idempotencia: registrar evento
    event_id = payload.get('payload', {}).get('object', {}).get('uuid', str(uuid.uuid4()))
    db = get_supabase_admin()

    try:
        db.schema('meetingboard').table('webhook_events').insert({
            'source': 'zoom',
            'event_type': event_type,
            'event_id': event_id,
            'payload': payload,
            'status': 'received',
        }).execute()
    except Exception:
        # UNIQUE constraint violation = evento duplicado, ignorar
        logger.info(f'Evento Zoom duplicado ignorado: {event_id}')
        return Response(status_code=200)

    # 4. Despachar según tipo de evento
    if event_type == 'recording.completed':
        await _handle_zoom_recording_completed(payload, db)

    return Response(status_code=200)


def _verify_zoom_signature(request: Request, body: bytes) -> None:
    """
    Zoom usa HMAC-SHA256 para firmar los webhooks.
    El header x-zm-signature contiene: v0={hash}
    El header x-zm-request-timestamp contiene el timestamp Unix.

    Mensaje firmado: "v0:{timestamp}:{body}"
    """
    if not settings.zoom_webhook_secret_token:
        logger.warning('zoom_webhook_secret_token no configurado, saltando verificación')
        return

    timestamp = request.headers.get('x-zm-request-timestamp', '')
    signature = request.headers.get('x-zm-signature', '')

    message = f'v0:{timestamp}:{body.decode()}'
    expected = 'v0=' + hmac.new(
        settings.zoom_webhook_secret_token.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail='Firma Zoom inválida')


async def _handle_zoom_recording_completed(payload: dict, db) -> None:
    """
    Cuando Zoom termina de procesar una grabación:
    1. Extraer la URL de descarga del MP4
    2. Crear el registro de meeting en BD
    3. Encolar el job de descarga + transcripción
    """
    obj = payload.get('payload', {}).get('object', {})
    meeting_id_zoom = obj.get('id', '')
    topic = obj.get('topic', 'Reunión sin título')
    start_time = obj.get('start_time', '')

    # Encontrar el archivo MP4 (puede haber varios: video, audio, chat)
    recording_files = obj.get('recording_files', [])
    mp4_file = next(
        (f for f in recording_files if f.get('file_extension', '').upper() == 'MP4'),
        None
    )

    if not mp4_file:
        logger.warning(f'No se encontró MP4 en grabación Zoom {meeting_id_zoom}')
        return

    download_url = mp4_file.get('download_url', '')

    # Crear el registro de meeting
    meeting_id = str(uuid.uuid4())
    db.schema('meetingboard').table('meetings').insert({
        'id': meeting_id,
        'title': topic,
        'platform': 'zoom',
        'meeting_date': start_time,
        'zoom_meeting_id': str(meeting_id_zoom),
        'status': 'queued',
    }).execute()

    # Encolar job de descarga + transcripción
    # (Disponible en Fase 5 cuando se implemente zoom_service)
    logger.info(
        f'Grabación Zoom recibida: {topic} → meeting {meeting_id}. '
        f'Download URL disponible por 24h.'
    )
    # from app.workers.transcription_task import download_and_transcribe_zoom
    # download_and_transcribe_zoom.delay(meeting_id, download_url)


# ─── Microsoft Teams ──────────────────────────────────────────────────────────

@router.post('/teams')
async def teams_webhook(request: Request):
    """
    Recibe notificaciones de Microsoft Graph API.
    Teams no tiene webhooks nativos para grabaciones, pero sí para cambios en archivos.
    Este endpoint recibe notificaciones de cambios en OneDrive/SharePoint.

    Disponible en Fase 6.
    """
    # Microsoft requiere validar el webhook con un clientState secret
    body = await request.json()

    # Validación inicial de Microsoft Graph
    if 'value' not in body:
        # Puede ser un challenge de validación
        validation_token = request.query_params.get('validationToken')
        if validation_token:
            return Response(content=validation_token, media_type='text/plain')

    logger.info('Evento Teams recibido (Fase 6 pendiente)')
    return Response(status_code=202)
