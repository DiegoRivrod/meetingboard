"""
Worker de transcripción — el componente más complejo del sistema.

Pipeline:
1. Descargar grabación de Supabase Storage
2. Extraer audio con ffmpeg (el video puede ser un MP4 de 500MB,
   el audio resultante es un WAV de ~50MB — mucho más rápido de procesar)
3. Transcribir con faster-whisper (modelo large-v3 o medium)
4. Diarizar con pyannote (identifica quién habló cuándo)
5. Mergear transcripción + diarización (asignar texto a cada speaker)
6. Guardar en BD: transcription + transcription_segments
7. Encolar analysis_task

Por qué este orden:
- Extraer audio primero reduce el uso de memoria
- Whisper procesa audio, no video
- La diarización necesita el audio completo para encontrar los hablantes
- El merge es necesario porque Whisper y pyannote producen timelines separadas
"""

import os
import tempfile
from celery import Task
from loguru import logger

from app.workers.celery_app import celery_app
from app.database import get_supabase_admin
from app.config import get_settings

settings = get_settings()


class TranscriptionTask(Task):
    """
    Clase base con lazy loading del modelo Whisper.

    Por qué lazy loading:
    - El modelo Whisper large-v3 pesa ~3GB en memoria
    - Si lo cargamos al arrancar el worker, tarda 30-60s en iniciar
    - Con lazy loading, se carga solo cuando llega el primer job
    - Se mantiene en memoria para jobs subsiguientes (no se recarga)
    """
    _whisper_model = None
    _diarization_pipeline = None

    @property
    def whisper_model(self):
        if self._whisper_model is None:
            from faster_whisper import WhisperModel
            logger.info(f'Cargando Whisper {settings.whisper_model} en {settings.whisper_device}...')
            self._whisper_model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
            logger.info('Modelo Whisper cargado')
        return self._whisper_model

    @property
    def diarization_pipeline(self):
        if self._diarization_pipeline is None and settings.huggingface_token:
            from pyannote.audio import Pipeline
            logger.info('Cargando pipeline de diarización pyannote...')
            self._diarization_pipeline = Pipeline.from_pretrained(
                'pyannote/speaker-diarization-3.1',
                use_auth_token=settings.huggingface_token,
            )
            logger.info('Pipeline de diarización cargado')
        return self._diarization_pipeline


@celery_app.task(
    base=TranscriptionTask,
    bind=True,
    name='app.workers.transcription_task.transcribe_meeting',
    max_retries=2,
    default_retry_delay=60,  # Esperar 1 min antes de reintentar
)
def transcribe_meeting(self, meeting_id: str) -> dict:
    """
    Job principal de transcripción.

    Args:
        meeting_id: UUID de la reunión a transcribir

    Returns:
        dict con transcription_id y estadísticas

    Raises:
        Se auto-reintenta hasta 2 veces en caso de error transitorio.
        Si falla definitivamente, actualiza meeting.status = 'failed'.
    """
    db = get_supabase_admin()

    try:
        # Actualizar status
        db.schema('meetingboard').table('meetings').update({
            'status': 'transcribing',
            'processing_started_at': 'now()',
        }).eq('id', meeting_id).execute()

        # Obtener meeting
        meeting = db.schema('meetingboard').table('meetings').select(
            'id, title, recording_url, recording_format'
        ).eq('id', meeting_id).single().execute()

        if not meeting.data or not meeting.data.get('recording_url'):
            raise ValueError(f'Meeting {meeting_id} sin archivo de grabación')

        recording_path = meeting.data['recording_url']
        logger.info(f'[{meeting_id}] Iniciando transcripción: {meeting.data["title"]}')

        # Descargar desde Supabase Storage a archivo temporal
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_file = os.path.join(tmpdir, 'audio.wav')

            # Descargar grabación
            logger.info(f'[{meeting_id}] Descargando desde Storage...')
            file_bytes = db.storage.from_(settings.storage_bucket).download(recording_path)

            raw_file = os.path.join(tmpdir, f'recording.{meeting.data.get("recording_format", "mp4")}')
            with open(raw_file, 'wb') as f:
                f.write(file_bytes)

            # Extraer audio con ffmpeg
            logger.info(f'[{meeting_id}] Extrayendo audio con ffmpeg...')
            _extract_audio(raw_file, audio_file)

            # Transcribir con Whisper
            logger.info(f'[{meeting_id}] Transcribiendo con Whisper {settings.whisper_model}...')
            segments_whisper, info = self.whisper_model.transcribe(
                audio_file,
                language='es',
                beam_size=5,
                vad_filter=True,          # Filtrar silencio
                vad_parameters={'min_silence_duration_ms': 500},
                word_timestamps=False,     # Solo segmentos, más rápido
            )
            segments_whisper = list(segments_whisper)  # Materializar el generador
            logger.info(
                f'[{meeting_id}] Whisper completado: {len(segments_whisper)} segmentos, '
                f'duración: {info.duration:.1f}s'
            )

            # Diarizar (si hay token de HuggingFace configurado)
            speaker_map = {}
            if self.diarization_pipeline:
                logger.info(f'[{meeting_id}] Diarizando hablantes...')
                speaker_map = _diarize_audio(self.diarization_pipeline, audio_file)
                logger.info(
                    f'[{meeting_id}] Diarización completa: {len(set(speaker_map.values()))} hablantes'
                )
            else:
                logger.warning(
                    f'[{meeting_id}] HuggingFace token no configurado, '
                    f'saltando diarización. Todos los segmentos serán SPEAKER_00.'
                )

            # Mergear transcripción + diarización
            merged_segments = _merge_whisper_diarization(segments_whisper, speaker_map)

            # Guardar en BD
            transcription_id = _save_transcription(
                db, meeting_id, merged_segments, info.duration
            )

        # Actualizar status
        db.schema('meetingboard').table('meetings').update({
            'status': 'transcribed',
            'duration_seconds': int(info.duration),
        }).eq('id', meeting_id).execute()

        logger.info(f'[{meeting_id}] Transcripción guardada: {transcription_id}')

        # Encolar análisis LLM
        from app.workers.analysis_task import analyze_meeting
        analyze_meeting.delay(meeting_id, transcription_id)

        return {'meeting_id': meeting_id, 'transcription_id': transcription_id}

    except Exception as exc:
        logger.error(f'[{meeting_id}] Error en transcripción: {exc}')
        db.schema('meetingboard').table('meetings').update({
            'status': 'failed',
            'processing_error': str(exc)[:500],
        }).eq('id', meeting_id).execute()
        raise self.retry(exc=exc)


def _extract_audio(input_path: str, output_path: str) -> None:
    """
    Extrae el audio del video usando ffmpeg.

    Por qué WAV 16kHz mono:
    - Whisper fue entrenado con audio 16kHz
    - Mono reduce el tamaño a la mitad vs estéreo
    - WAV es sin compresión → Whisper no pierde tiempo decodificando
    """
    import ffmpeg
    (
        ffmpeg
        .input(input_path)
        .output(
            output_path,
            acodec='pcm_s16le',  # PCM 16-bit little-endian (WAV)
            ar=16000,            # 16kHz
            ac=1,                # Mono
        )
        .overwrite_output()
        .run(quiet=True)
    )


def _diarize_audio(pipeline, audio_path: str) -> dict:
    """
    Corre pyannote para identificar quién habló cuándo.

    Retorna: {(start, end): 'SPEAKER_00', ...}
    """
    diarization = pipeline(audio_path)
    speaker_map = {}
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_map[(round(turn.start, 3), round(turn.end, 3))] = speaker
    return speaker_map


def _merge_whisper_diarization(
    whisper_segments: list,
    speaker_map: dict,
) -> list:
    """
    Asigna un speaker_label a cada segmento de Whisper.

    Estrategia: para cada segmento de Whisper, encontrar el speaker de pyannote
    cuyo turno tiene más overlap con el segmento.
    """
    merged = []
    for seg in whisper_segments:
        best_speaker = 'SPEAKER_00'
        best_overlap = 0.0

        for (s_start, s_end), speaker in speaker_map.items():
            overlap = min(seg.end, s_end) - max(seg.start, s_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker

        merged.append({
            'start': seg.start,
            'end': seg.end,
            'text': seg.text.strip(),
            'speaker_label': best_speaker,
            'confidence': getattr(seg, 'avg_logprob', None),
        })

    return merged


def _save_transcription(db, meeting_id: str, segments: list, duration: float) -> str:
    """Guarda la transcripción y sus segmentos en Supabase."""
    import uuid

    # Crear transcripción
    word_count = sum(len(s['text'].split()) for s in segments)
    transcription_result = db.schema('meetingboard').table('transcriptions').insert({
        'id': str(uuid.uuid4()),
        'meeting_id': meeting_id,
        'whisper_model': settings.whisper_model,
        'language': 'es',
        'word_count': word_count,
        'duration_seconds': int(duration),
    }).execute()

    transcription_id = transcription_result.data[0]['id']

    # Insertar segmentos en lotes de 100 para no superar límites de Supabase
    BATCH_SIZE = 100
    segment_rows = [
        {
            'transcription_id': transcription_id,
            'meeting_id': meeting_id,
            'segment_index': i,
            'speaker_label': seg['speaker_label'],
            'start_time': seg['start'],
            'end_time': seg['end'],
            'text': seg['text'],
            'confidence': seg.get('confidence'),
        }
        for i, seg in enumerate(segments)
        if seg['text']  # Ignorar segmentos vacíos
    ]

    for i in range(0, len(segment_rows), BATCH_SIZE):
        batch = segment_rows[i:i + BATCH_SIZE]
        db.schema('meetingboard').table('transcription_segments').insert(batch).execute()

    return transcription_id
