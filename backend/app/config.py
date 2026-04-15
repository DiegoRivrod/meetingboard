"""
Configuración centralizada con pydantic-settings.

Por qué pydantic-settings:
- Lee variables de entorno Y archivos .env automáticamente
- Valida tipos en el arranque (falla rápido si falta una variable crítica)
- Documenta qué variables necesita el sistema en un solo lugar
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    app_name: str = 'MeetingBoard API'
    app_version: str = '0.1.0'
    debug: bool = False
    environment: str = 'development'  # development | staging | production

    # ─── Supabase ─────────────────────────────────────────────────────────────
    supabase_url: str
    supabase_service_role_key: str  # Service role para operaciones backend (bypass RLS)
    supabase_anon_key: str          # Para verificar tokens de usuario

    # ─── JWT (Supabase firma los tokens con esto) ──────────────────────────────
    supabase_jwt_secret: str        # En Supabase: Settings → API → JWT Secret

    # ─── Redis (Celery broker) ────────────────────────────────────────────────
    redis_url: str = 'redis://localhost:6379/0'

    # ─── LLM (Claude) ─────────────────────────────────────────────────────────
    anthropic_api_key: str

    # ─── Transcripción ────────────────────────────────────────────────────────
    whisper_model: str = 'medium'       # medium para dev rápido, large-v3 para prod
    whisper_device: str = 'cpu'         # cpu | cuda (si hay GPU)
    whisper_compute_type: str = 'int8'  # int8 para CPU, float16 para GPU

    # pyannote requiere token de HuggingFace (registro gratuito + aceptar términos)
    # https://huggingface.co/pyannote/speaker-diarization-3.1
    huggingface_token: str = ''

    # ─── Zoom API ─────────────────────────────────────────────────────────────
    zoom_account_id: str = ''
    zoom_client_id: str = ''
    zoom_client_secret: str = ''
    zoom_webhook_secret_token: str = ''  # Para verificar firma HMAC

    # ─── Microsoft Graph (Teams) ──────────────────────────────────────────────
    ms_tenant_id: str = ''
    ms_client_id: str = ''
    ms_client_secret: str = ''

    # ─── Email (Resend) ───────────────────────────────────────────────────────
    resend_api_key: str = ''
    email_from: str = 'MeetingBoard <noreply@meetingboard.app>'

    # ─── Storage ──────────────────────────────────────────────────────────────
    # Nombre del bucket en Supabase Storage (debe crearse como privado)
    storage_bucket: str = 'meeting-recordings'
    max_upload_size_mb: int = 500  # 500 MB máximo por archivo

    # ─── CORS ─────────────────────────────────────────────────────────────────
    # En prod: solo el dominio de Vercel. En dev: localhost:5173
    allowed_origins: list[str] = [
        'http://localhost:5173',
        'http://localhost:4173',
    ]


@lru_cache
def get_settings() -> Settings:
    """
    Singleton cacheado. Se instancia una vez al arrancar.
    Usar como: from app.config import get_settings; settings = get_settings()
    """
    return Settings()  # type: ignore[call-arg]
