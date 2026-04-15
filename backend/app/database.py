"""
Clientes de base de datos.

Usamos dos clientes de Supabase:
1. Cliente público (anon_key): para operaciones que respetan RLS (Row Level Security)
2. Cliente admin (service_role_key): para operaciones del backend que bypasan RLS
   (e.g., actualizar estado de transcripción en un worker de Celery)

Por qué separar los dos:
- RLS protege que un usuario no pueda ver los datos de otro
- El worker de Celery no tiene contexto de usuario, necesita acceso total
- Usar service_role en el frontend sería un riesgo de seguridad grave
"""

from functools import lru_cache
from supabase import create_client, Client
from app.config import get_settings


@lru_cache
def get_supabase_admin() -> Client:
    """
    Cliente con service_role_key.
    Solo usar en código de servidor (workers, webhooks internos).
    NUNCA exponer al frontend.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


@lru_cache
def get_supabase_anon() -> Client:
    """
    Cliente con anon_key.
    Para verificar tokens de usuarios del frontend.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
