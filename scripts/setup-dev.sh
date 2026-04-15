#!/bin/bash
##
## setup-dev.sh — Script de configuración del entorno de desarrollo.
## Ejecutar desde la raíz del proyecto: bash scripts/setup-dev.sh
##

set -e  # Parar si cualquier comando falla

echo "=== MeetingBoard — Setup de desarrollo ==="
echo ""

# ─── 1. Frontend ──────────────────────────────────────────────────────────────
echo "► Instalando dependencias del frontend..."
cd frontend

if [ ! -f ".env.local" ]; then
    cp .env.example .env.local
    echo "  ✓ Creado frontend/.env.local (edita con tus credenciales de Supabase)"
else
    echo "  ✓ frontend/.env.local ya existe"
fi

npm install
echo "  ✓ Dependencias npm instaladas"
cd ..

# ─── 2. Backend ───────────────────────────────────────────────────────────────
echo ""
echo "► Configurando backend Python..."
cd backend

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  ✓ Creado backend/.env (edita con tus credenciales)"
else
    echo "  ✓ backend/.env ya existe"
fi

cd ..

# ─── 3. Docker ────────────────────────────────────────────────────────────────
echo ""
echo "► Verificando Docker Desktop..."
if command -v docker &> /dev/null; then
    echo "  ✓ Docker disponible: $(docker --version)"
else
    echo "  ✗ Docker no encontrado. Instalar desde: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# ─── 4. Instrucciones finales ─────────────────────────────────────────────────
echo ""
echo "=== Setup completado ==="
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Configurar Supabase:"
echo "   - Crear proyecto en supabase.com"
echo "   - Ejecutar supabase/migrations/001_meetingboard_schema.sql en el SQL Editor"
echo "   - Crear bucket 'meeting-recordings' (privado) en Storage"
echo "   - Copiar credenciales en backend/.env y frontend/.env.local"
echo ""
echo "2. Levantar el backend:"
echo "   cd backend && docker compose up"
echo ""
echo "3. Levantar el frontend (en otra terminal):"
echo "   cd frontend && npm run dev"
echo ""
echo "4. Abrir en el navegador: http://localhost:5173"
