"""
Punto de entrada de la API FastAPI.

Por qué FastAPI:
- Genera documentación OpenAPI automática en /docs (útil para el frontend TypeScript)
- Async nativo — puede manejar múltiples requests mientras espera I/O
- Pydantic V2 integrado para validación de tipos en la frontera del sistema
- Performance comparable a Node.js para este tipo de carga
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Código que corre al arrancar y al apagar el servidor.
    Útil para inicializar conexiones, cargar modelos, etc.
    """
    logger.info(f"MeetingBoard API v{settings.app_version} arrancando...")
    logger.info(f"Ambiente: {settings.environment}")
    logger.info(f"Debug: {settings.debug}")

    # Aquí se cargará el modelo Whisper en memoria (Fase 1)
    # Así evitamos el cold start en el primer request de transcripción
    # from app.services.transcription import load_whisper_model
    # await load_whisper_model()

    yield  # El servidor está corriendo

    logger.info("MeetingBoard API apagando...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## MeetingBoard API

Backend para procesamiento de reuniones virtuales:
- **Upload** de grabaciones MP4/M4A/WAV
- **Transcripción** con faster-whisper (local, privado)
- **Diarización** con pyannote (quién habló cuándo)
- **Análisis LLM** con Claude para extraer action items
- **Webhooks** de Zoom y Microsoft Teams
    """,
    docs_url='/docs' if settings.debug else None,  # Deshabilitar en producción
    redoc_url='/redoc' if settings.debug else None,
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Permite al frontend React hacer llamadas al backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
# Se importan aquí para evitar imports circulares
# Cada router se agrega con prefix=/api para que coincida con el proxy de Vite

from app.api import meetings, action_items, people, analytics, webhooks  # noqa: E402

app.include_router(meetings.router,      prefix='/api/meetings',      tags=['Meetings'])
app.include_router(action_items.router,  prefix='/api/action-items',  tags=['Action Items'])
app.include_router(people.router,        prefix='/api/people',        tags=['People'])
app.include_router(analytics.router,     prefix='/api/analytics',     tags=['Analytics'])
app.include_router(webhooks.router,      prefix='/api/webhooks',      tags=['Webhooks'])


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get('/health', tags=['System'])
async def health_check():
    """
    Endpoint de salud para Railway, Docker healthcheck y monitoreo.
    Responde rápido sin tocar la BD.
    """
    return {
        'status': 'ok',
        'version': settings.app_version,
        'environment': settings.environment,
    }


@app.get('/api/health', tags=['System'])
async def api_health_check():
    """Mismo health check accesible bajo /api para el frontend."""
    return await health_check()
