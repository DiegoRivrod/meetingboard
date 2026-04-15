"""
Worker de análisis LLM — extrae los action items con Claude.

Por qué chunks con overlap:
- Una reunión de 60 min tiene ~10,000-15,000 tokens de transcripción
- Claude claude-sonnet-4-6 tiene context window de 200k tokens, así que cabe todo
- Sin embargo, la calidad de extracción baja hacia el final de inputs muy largos
- Con chunks de 4,000 tokens con overlap de 500, cada chunk tiene contexto suficiente
- Hacemos deduplicación al final para items que aparezcan en múltiples chunks

Por qué guardar el raw_llm_response:
- Si el modelo mejora o el prompt cambia, podemos re-parsear sin re-procesar la reunión
- Facilita debugging cuando el modelo extrae algo incorrecto
"""

import json
import uuid
from loguru import logger
from celery import Task
from tenacity import retry, stop_after_attempt, wait_exponential

from app.workers.celery_app import celery_app
from app.database import get_supabase_admin
from app.config import get_settings

settings = get_settings()

# ─── Prompt de extracción ─────────────────────────────────────────────────────
# El prompt más importante del sistema — define la calidad del producto

EXTRACTION_SYSTEM_PROMPT = """Eres un asistente experto en análisis de reuniones de negocios en español latinoamericano.
Tu tarea es identificar compromisos, decisiones y tareas en transcripciones de reuniones.

REGLAS IMPORTANTES:
- Solo extrae items que estén EXPLÍCITA o IMPLÍCITAMENTE presentes en el texto
- Para due_date_iso, si se menciona "la próxima semana" o "el viernes", estima la fecha relativa basándote en el contexto
- Si no puedes estimar la fecha, usa null
- confidence debe reflejar tu certeza: 0.9+ para items muy claros, 0.5-0.7 para compromisos implícitos
- No inventes personas ni fechas que no estén mencionadas"""

EXTRACTION_USER_PROMPT = """Analiza esta transcripción de reunión y extrae todos los elementos importantes.

TIPOS A DETECTAR:
1. action_item: Tarea concreta asignada a alguien
   Señales: "tienes que", "encárgate de", "necesitamos que X haga", "X debe"

2. decision: Decisión tomada que afecta al negocio
   Señales: "quedamos en", "se decide", "vamos a proceder con", "acordamos"

3. commitment: Compromiso implícito sin asignación formal
   Señales: "yo me encargo", "lo reviso", "te mando el informe", "lo veo"

4. risk: Riesgo, problema o bloqueador identificado
   Señales: "puede que no lleguemos", "hay un problema con", "me preocupa", "riesgo de"

RESPONDE ÚNICAMENTE con este JSON (sin markdown, sin texto adicional):
{{
  "items": [
    {{
      "type": "action_item|decision|commitment|risk",
      "title": "Título corto máximo 80 caracteres",
      "description": "Descripción completa con contexto",
      "context_quote": "Frase exacta de la transcripción que originó este item",
      "speaker": "Nombre del hablante o etiqueta SPEAKER_XX",
      "assignee": "Nombre completo de quien es responsable, o null",
      "due_date_raw": "Texto original de la fecha mencionada, o null",
      "due_date_iso": "YYYY-MM-DD estimado, o null",
      "confidence": 0.85,
      "priority": "low|medium|high|critical"
    }}
  ],
  "executive_summary": "Resumen ejecutivo de 2-3 oraciones de los puntos más importantes",
  "topics": ["tema principal 1", "tema principal 2"],
  "sentiment": "positive|neutral|tense|unproductive"
}}

TRANSCRIPCIÓN:
{transcript}"""


class AnalysisTask(Task):
    """Lazy loading del cliente Anthropic."""
    _anthropic_client = None

    @property
    def client(self):
        if self._anthropic_client is None:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._anthropic_client


@celery_app.task(
    base=AnalysisTask,
    bind=True,
    name='app.workers.analysis_task.analyze_meeting',
    max_retries=3,
    default_retry_delay=30,
)
def analyze_meeting(self, meeting_id: str, transcription_id: str) -> dict:
    """Analiza la transcripción de una reunión y extrae action items."""
    db = get_supabase_admin()

    try:
        db.schema('meetingboard').table('meetings').update({
            'status': 'analyzing',
        }).eq('id', meeting_id).execute()

        # Obtener todos los segmentos
        segments = db.schema('meetingboard').table('transcription_segments').select(
            'speaker_label, start_time, text'
        ).eq('transcription_id', transcription_id).order('segment_index').execute()

        if not segments.data:
            raise ValueError(f'No hay segmentos para la transcripción {transcription_id}')

        # Formatear transcripción para el LLM
        transcript_text = _format_transcript(segments.data)

        # Dividir en chunks si es muy larga
        chunks = _chunk_transcript(transcript_text, max_tokens=4000, overlap_tokens=500)
        logger.info(f'[{meeting_id}] Analizando {len(chunks)} chunks con Claude...')

        all_items = []
        executive_summary = ''
        topics: list[str] = []
        sentiment = 'neutral'
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for i, chunk in enumerate(chunks):
            logger.info(f'[{meeting_id}] Procesando chunk {i+1}/{len(chunks)}...')
            result = _call_claude(self.client, chunk)

            if result:
                all_items.extend(result.get('items', []))
                if not executive_summary and result.get('executive_summary'):
                    executive_summary = result['executive_summary']
                topics.extend(result.get('topics', []))
                if result.get('sentiment') and result['sentiment'] != 'neutral':
                    sentiment = result['sentiment']
                total_prompt_tokens += result.get('prompt_tokens', 0)
                total_completion_tokens += result.get('completion_tokens', 0)

        # Deduplicar items similares
        all_items = _deduplicate_items(all_items)
        topics = list(dict.fromkeys(topics))[:10]  # Deduplicate preserving order

        # Guardar análisis
        analysis_id = _save_analysis(
            db, meeting_id,
            items=all_items,
            executive_summary=executive_summary,
            topics=topics,
            sentiment=sentiment,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
        )

        db.schema('meetingboard').table('meetings').update({
            'status': 'analyzed',
            'processing_completed_at': 'now()',
        }).eq('id', meeting_id).execute()

        logger.info(
            f'[{meeting_id}] Análisis completado: {len(all_items)} items extraídos'
        )
        return {'meeting_id': meeting_id, 'analysis_id': analysis_id, 'items_count': len(all_items)}

    except Exception as exc:
        logger.error(f'[{meeting_id}] Error en análisis: {exc}')
        db.schema('meetingboard').table('meetings').update({
            'status': 'failed',
            'processing_error': str(exc)[:500],
        }).eq('id', meeting_id).execute()
        raise self.retry(exc=exc)


def _format_transcript(segments: list) -> str:
    """Convierte segmentos de BD en texto con timestamps y speaker labels."""
    lines = []
    current_speaker = None

    for seg in segments:
        speaker = seg.get('speaker_label', 'DESCONOCIDO')
        text = seg.get('text', '').strip()
        if not text:
            continue

        # Agregar encabezado de hablante cuando cambia
        if speaker != current_speaker:
            lines.append(f'\n[{speaker}]:')
            current_speaker = speaker

        lines.append(f'  {text}')

    return '\n'.join(lines)


def _chunk_transcript(text: str, max_tokens: int = 4000, overlap_tokens: int = 500) -> list[str]:
    """
    Divide la transcripción en chunks con overlap.

    Estimación de tokens: ~4 caracteres por token en español.
    El overlap asegura que los compromisos que cruzan el límite del chunk no se pierdan.
    """
    chars_per_chunk = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    if len(text) <= chars_per_chunk:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chars_per_chunk
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap_chars

    return chunks


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
)
def _call_claude(client, transcript: str) -> dict | None:
    """
    Llama a la API de Claude con retry automático.

    Por qué tenacity para retry:
    - La API puede tener rate limits o errores transitorios
    - Backoff exponencial: espera 4s, 8s, 16s entre intentos
    - Máximo 3 intentos antes de fallar definitivamente
    """
    prompt = EXTRACTION_USER_PROMPT.format(transcript=transcript)

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=4096,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
    )

    content = message.content[0].text.strip()

    # Limpiar posible markdown
    if content.startswith('```'):
        content = content.split('```')[1]
        if content.startswith('json'):
            content = content[4:]

    try:
        data = json.loads(content)
        data['prompt_tokens'] = message.usage.input_tokens
        data['completion_tokens'] = message.usage.output_tokens
        return data
    except json.JSONDecodeError as e:
        logger.error(f'Claude retornó JSON inválido: {e}. Respuesta: {content[:200]}')
        return None


def _deduplicate_items(items: list) -> list:
    """
    Elimina items duplicados basándose en similitud del title.
    Los chunks con overlap pueden generar el mismo item dos veces.
    """
    seen_titles: set[str] = set()
    unique = []
    for item in items:
        title_normalized = item.get('title', '').lower().strip()[:50]
        if title_normalized not in seen_titles:
            seen_titles.add(title_normalized)
            unique.append(item)
    return unique


def _save_analysis(
    db, meeting_id: str,
    items: list, executive_summary: str, topics: list,
    sentiment: str, prompt_tokens: int, completion_tokens: int,
) -> str:
    """Guarda el análisis y los action items en BD."""

    analysis_id = str(uuid.uuid4())

    db.schema('meetingboard').table('ai_analyses').insert({
        'id': analysis_id,
        'meeting_id': meeting_id,
        'llm_model': 'claude-sonnet-4-6',
        'executive_summary': executive_summary,
        'meeting_sentiment': sentiment,
        'topics_discussed': topics,
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'raw_llm_response': {'items_count': len(items), 'topics': topics},
    }).execute()

    # Insertar action items
    item_rows = []
    for item in items:
        item_rows.append({
            'id': str(uuid.uuid4()),
            'meeting_id': meeting_id,
            'analysis_id': analysis_id,
            'item_type': item.get('type', 'action_item'),
            'title': item.get('title', '')[:200],
            'description': item.get('description'),
            'context_quote': item.get('context_quote'),
            'assignee_name_raw': item.get('assignee'),
            'due_date': item.get('due_date_iso'),
            'due_date_raw': item.get('due_date_raw'),
            'ai_confidence': item.get('confidence', 0.8),
            'priority': item.get('priority', 'medium'),
            'is_ai_generated': True,
            'was_manually_edited': False,
            'status': 'pending',
        })

    if item_rows:
        BATCH = 50
        for i in range(0, len(item_rows), BATCH):
            db.schema('meetingboard').table('action_items').insert(
                item_rows[i:i + BATCH]
            ).execute()

    return analysis_id
