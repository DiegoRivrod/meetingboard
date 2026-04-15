# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
# Instalamos dependencias en una imagen separada para que la imagen final
# no tenga herramientas de build (reduce tamaño ~40%)
FROM python:3.11-slim AS builder

WORKDIR /app

# Instalar ffmpeg (necesario para extraer audio de videos)
# Se hace antes de pip install para aprovechar el cache de Docker layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copiar ffmpeg desde el builder
COPY --from=builder /usr/bin/ffmpeg /usr/bin/ffmpeg
COPY --from=builder /usr/bin/ffprobe /usr/bin/ffprobe
COPY --from=builder /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu

# Copiar librerías Python instaladas
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código
COPY app/ ./app/

# Usuario no-root por seguridad
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Variables de entorno de producción
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

# Health check para Railway / Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Comando por defecto: API FastAPI
# Para el worker de Celery, Railway usa un proceso separado con:
# celery -A app.workers.celery_app worker --loglevel=info -Q transcription,llm,scheduled
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
