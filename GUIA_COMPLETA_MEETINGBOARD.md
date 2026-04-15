# GUÍA COMPLETA — MeetingBoard
## De la Idea al Sistema de Control de Reuniones

> **Para quién es esta guía:** Para ti, que quieres entender no solo QUÉ se hizo,
> sino POR QUÉ se tomó cada decisión. Cada sección explica la lógica detrás del código.

---

## ÍNDICE

1. [¿Qué problema resuelve MeetingBoard?](#1-qué-problema-resuelve-meetingboard)
2. [Cómo funciona el sistema (visión general)](#2-cómo-funciona-el-sistema-visión-general)
3. [Las decisiones técnicas clave y por qué](#3-las-decisiones-técnicas-clave-y-por-qué)
4. [Estructura del proyecto explicada](#4-estructura-del-proyecto-explicada)
5. [La base de datos: cada tabla y por qué existe](#5-la-base-de-datos-cada-tabla-y-por-qué-existe)
6. [El pipeline de procesamiento paso a paso](#6-el-pipeline-de-procesamiento-paso-a-paso)
7. [Cómo instalar y correr el proyecto](#7-cómo-instalar-y-correr-el-proyecto)
8. [Configurar Supabase (base de datos)](#8-configurar-supabase-base-de-datos)
9. [Las fases del proyecto](#9-las-fases-del-proyecto)
10. [Glosario técnico](#10-glosario-técnico)

---

## 1. ¿Qué problema resuelve MeetingBoard?

### El problema real

En las empresas pasan reuniones virtuales todos los días. En esas reuniones se dicen cosas como:

- *"Carlos, para el viernes me mandas el informe de ventas"*
- *"Quedamos en que el área de logística va a revisar el proceso antes del martes"*
- *"Me encargo de gestionar el presupuesto con el proveedor"*

¿Qué pasa con esos compromisos? Generalmente... **se olvidan**. Nadie los escribe, nadie los rastrea, y en la próxima reunión hay que recordarlos de memoria.

### La solución

MeetingBoard toma la grabación de esa reunión y:

1. **Transcribe** todo lo que se dijo (convierte audio a texto)
2. **Identifica** quién dijo qué y cuándo
3. **Extrae automáticamente** con inteligencia artificial todos los compromisos, tareas y decisiones
4. **Los organiza** en un tablero visual (Kanban) con nombre del responsable y fecha límite
5. **Mide** quién cumple y quién no, generando un porcentaje de adherencia por persona
6. **Alerta** 48 horas antes de que venza un compromiso

### El resultado

Puedes tener un dashboard que te diga: *"Carlos tiene 70% de adherencia este mes — completó 7 de 10 compromisos"*. Esto te permite gestionar con datos, no con suposiciones.

---

## 2. Cómo funciona el sistema (visión general)

Imagina una cadena de producción:

```
[ENTRADA]              [PROCESAMIENTO]              [SALIDA]
                              │
Grabación MP4    ──►  Extracción de audio  ──►  Action Log (Kanban)
(Zoom o Teams)         (ffmpeg)                  con responsables
                              │                  y deadlines
                       Transcripción                   │
                       (Whisper IA)              Dashboard de
                              │                  adherencia
                       Identificación                  │
                       de hablantes             Notificaciones
                       (pyannote)               de deadlines
                              │
                       Análisis de texto
                       (Claude IA)
                              │
                       Extracción de
                       compromisos (JSON)
```

### Las tres capas del sistema

**Capa 1 — Frontend (lo que ves):**
La aplicación web que corre en tu navegador. Hecha con React. Tiene el tablero Kanban, el dashboard con gráficos, y la pantalla para subir grabaciones.

**Capa 2 — Backend (el cerebro):**
Un servidor Python que recibe los archivos, los procesa, llama a la inteligencia artificial y guarda los resultados. No lo ves directamente, pero hace todo el trabajo pesado.

**Capa 3 — Base de datos (la memoria):**
Supabase (PostgreSQL). Guarda todas las reuniones, transcripciones, compromisos y métricas. Persiste cuando cierras el navegador.

---

## 3. Las decisiones técnicas clave y por qué

Esta sección es la más importante. Aquí explico cada elección tecnológica.

---

### ¿Por qué Python para el backend y no JavaScript/Node.js?

**La razón:** Las herramientas de inteligencia artificial para audio existen **casi exclusivamente en Python**.

- `faster-whisper` (transcripción) → solo Python
- `pyannote.audio` (identificar quién habló) → solo Python
- Si usáramos Node.js, tendríamos que llamar a scripts Python desde Node, creando una arquitectura frágil donde dos sistemas distintos tienen que coordinarse

**Analogía:** Es como si necesitas un carpintero y un electricista. Es más fácil contratar a alguien que sabe hacer ambas cosas (Python) que tener dos personas que se tienen que comunicar constantemente.

---

### ¿Por qué faster-whisper para transcribir y no la API de OpenAI?

**La razón principal: privacidad y costo.**

OpenAI cobra $0.006 por minuto de audio. Una reunión de 60 minutos = $0.36. Con 20 reuniones al mes = $86.40 al año. Con 50 reuniones = $216/año.

Pero más importante: las grabaciones de tus reuniones contienen información sensible de tu empresa — estrategias, números, nombres de clientes, problemas internos. Enviarlas a los servidores de OpenAI significa que esa información sale de tu control.

**faster-whisper** es el mismo modelo de IA de Whisper que usa OpenAI, pero corre **en tu propio computador/servidor**. La calidad es idéntica, el costo es $0, y los datos nunca salen de tu infraestructura.

**El tradeoff:** Corre más lento que la API. Una reunión de 60 minutos puede tardar entre 20 y 60 minutos en transcribirse (dependiendo del procesador). Pero como el procesamiento es en segundo plano (no tienes que esperar mirando la pantalla), esto es aceptable.

---

### ¿Por qué pyannote para identificar quién habló?

**La razón:** La transcripción de Whisper sola te dice el texto, pero no QUIÉN lo dijo. Solo obtienes:

```
"Vamos a revisar el presupuesto antes del viernes"
"Sí, yo me encargo de eso"
```

Con pyannote obtienes:

```
[SPEAKER_00]: "Vamos a revisar el presupuesto antes del viernes"
[SPEAKER_01]: "Sí, yo me encargo de eso"
```

Y después tú mapeas: SPEAKER_00 = Carlos, SPEAKER_01 = Ana.

Esto es crítico porque el sistema necesita saber QUÉ persona hizo el compromiso para asignarle la responsabilidad en el Action Log.

---

### ¿Por qué Claude (Anthropic) para analizar la transcripción?

**La razón:** No es suficiente con tener el texto de la reunión. Necesitas que una IA entienda el CONTEXTO y distinga entre:

- Una afirmación: *"El presupuesto está en $50,000"* → no es un compromiso
- Una tarea asignada: *"Carlos, prepara el informe"* → SÍ es un action item
- Un compromiso implícito: *"Yo lo veo"* → SÍ es un compromiso (aunque no se diga explícitamente "me comprometo")

Claude (el mismo modelo que te responde en esta conversación) es especialmente bueno en español y en entender contexto conversacional.

**El costo:** ~$0.03 por reunión de 60 minutos. Muy barato comparado con el valor que entrega.

---

### ¿Por qué Celery + Redis para el procesamiento?

**La razón:** Este es uno de los conceptos más importantes para entender.

Cuando un usuario sube una grabación de 60 minutos, el sistema necesita:
1. Extraer el audio → 1 minuto
2. Transcribir → 20-60 minutos
3. Analizar con Claude → 2-3 minutos

Total: entre 23 y 64 minutos.

Un servidor web normal tiene un **timeout** de ~30 segundos. Si le dices "espera mientras proceso tu archivo de 60 minutos", el servidor dirá "ya esperé demasiado, me desconecto" antes de terminar.

**Celery** es un sistema de cola de trabajos:
- El usuario sube el archivo
- El servidor dice inmediatamente: "¡Recibido! Tu archivo está en la cola, número 3"
- El usuario ve en pantalla un indicador de progreso
- Un proceso separado (el "worker") toma el archivo de la cola y lo procesa lentamente
- Cuando termina, actualiza la base de datos
- La pantalla del usuario se actualiza automáticamente

**Redis** es la "pizarra" donde se escribe la cola. El servidor anota "hay trabajo pendiente", el worker lee "hay trabajo pendiente" y lo hace.

**Analogía:** Es como pedir comida por delivery. No te quedas parado en la cocina esperando. Haces el pedido (upload), recibes confirmación, haces otras cosas, y cuando está listo te avisan.

---

### ¿Por qué Supabase?

**La razón:** Supabase en una herramienta que combina en un solo lugar:
- **Base de datos** PostgreSQL (guardas tus datos)
- **Autenticación** (login/logout sin escribir código de seguridad)
- **Storage** (guardar archivos grandes como las grabaciones)
- **Realtime** (notificaciones instantáneas cuando algo cambia)

El cuarto punto es clave: con Supabase Realtime, cuando el worker termina de transcribir una reunión, la base de datos notifica automáticamente al navegador del usuario, que actualiza la barra de progreso sin que el usuario tenga que hacer nada.

**Precio:** Gratis hasta 500 MB de almacenamiento y 50,000 requests al mes.

---

### ¿Por qué React + TypeScript para el frontend?

**La razón:** Usas React porque ya tienes AuditBoard construido con React. Reutilizas el mismo stack, los mismos patrones visuales, y (en el futuro) hasta los mismos componentes.

**TypeScript** es JavaScript pero con "tipos" — básicamente le dices al lenguaje que una variable es un "ActionItem" y no puede ser mezclada con un "Meeting". Esto parece burocrático al principio pero previene errores en runtime (cuando el usuario ya está usando la app).

---

## 4. Estructura del proyecto explicada

```
meetingboard/
│
├── .github/
│   └── workflows/           ← Los "robots" de GitHub que comprueban tu código
│       ├── ci.yml           ← Se ejecuta en cada Pull Request: verifica que compila
│       └── deploy-production.yml  ← Se ejecuta en cada merge a main: despliega
│
├── frontend/                ← Todo lo que ve el usuario en el navegador
│   └── src/
│       ├── pages/           ← Una página = una pantalla de la app
│       │   ├── Auth.tsx         (pantalla de login)
│       │   ├── Dashboard.tsx    (KPIs y gráficos)
│       │   ├── Meetings.tsx     (lista de reuniones)
│       │   ├── ActionLog.tsx    (tablero Kanban)
│       │   ├── People.tsx       (ranking de adherencia)
│       │   └── Settings.tsx     (configuración de integraciones)
│       │
│       ├── components/      ← Piezas reutilizables de UI
│       │   ├── layout/          (Sidebar + Header + Layout wrapper)
│       │   ├── meetings/        (tarjetas de reunión, barra de progreso)
│       │   ├── action-items/    (tarjetas Kanban, modales)
│       │   └── dashboard/       (gráficos de adherencia)
│       │
│       ├── hooks/           ← Lógica reutilizable (carga de datos, realtime)
│       ├── lib/
│       │   ├── supabase.ts      (conexión a la base de datos)
│       │   └── api.ts           (llamadas al backend Python)
│       └── types/           ← Definiciones de qué es un "Meeting", un "ActionItem", etc.
│
├── backend/                 ← El servidor Python (nunca lo ve el usuario)
│   └── app/
│       ├── main.py          ← Punto de entrada: "aquí arranca el servidor"
│       ├── config.py        ← Variables de configuración (API keys, etc.)
│       ├── database.py      ← Conexión a Supabase
│       │
│       ├── api/             ← Los "endpoints": URLs que acepta el servidor
│       │   ├── meetings.py      (subir grabaciones, ver transcripciones)
│       │   ├── action_items.py  (CRUD de compromisos)
│       │   ├── people.py        (gestión de personas)
│       │   ├── analytics.py     (datos para el dashboard)
│       │   └── webhooks.py      (recibir notificaciones de Zoom/Teams)
│       │
│       ├── workers/         ← Los procesos que corren en segundo plano
│       │   ├── celery_app.py        (configuración de la cola de trabajo)
│       │   ├── transcription_task.py (Whisper + pyannote)
│       │   ├── analysis_task.py     (Claude IA)
│       │   └── scheduled_tasks.py   (tareas programadas diarias)
│       │
│       ├── Dockerfile       ← Instrucciones para empaquetar el servidor
│       └── docker-compose.yml ← Levanta TODO el backend con un solo comando
│
├── supabase/
│   └── migrations/
│       └── 001_meetingboard_schema.sql  ← El "plano" de la base de datos
│
├── scripts/
│   └── setup-dev.sh         ← Script que configura todo el entorno de una vez
│
├── .gitignore               ← Lista de archivos que NO se suben a GitHub (contraseñas, etc.)
├── README.md                ← Documentación del proyecto
└── GUIA_COMPLETA_MEETINGBOARD.md  ← Este archivo
```

---

## 5. La base de datos: cada tabla y por qué existe

La base de datos vive en Supabase en un "schema" llamado `meetingboard`. Un schema es como una carpeta dentro de la base de datos — permite que coexista con las tablas de AuditBoard sin conflictos.

---

### Tabla: `people` (personas)

**¿Qué guarda?** Las personas que participan en reuniones.

**¿Por qué existe separada de los usuarios?** Porque una reunión puede tener participantes externos — un proveedor, un cliente, alguien de otra empresa — que no tiene usuario en el sistema. La tabla `people` guarda a TODOS, tengan cuenta o no.

**Columnas importantes:**
- `full_name` — nombre completo
- `email` — para enviarle notificaciones
- `area` — CALIDAD, PRODUCCIÓN, LOGÍSTICA, etc. (para filtrar en dashboards)
- `adherence_rate` — porcentaje de cumplimiento calculado automáticamente

---

### Tabla: `meetings` (reuniones)

**¿Qué guarda?** Una fila por cada grabación que se sube al sistema.

**La columna más importante: `status`**

Esta columna tiene 8 valores posibles y representa en qué paso del pipeline está la reunión:

```
uploaded     → El archivo se subió pero aún no se procesa
queued       → Está en la cola esperando al worker
transcribing → El worker está transcribiendo ahora mismo
transcribed  → La transcripción terminó, falta el análisis LLM
analyzing    → Claude está analizando la transcripción
analyzed     → Todo listo. Los action items ya están disponibles
failed       → Algo salió mal (hay un mensaje de error)
archived     → Se archivó manualmente
```

¿Por qué tantos estados? Porque el procesamiento tarda y el usuario necesita saber exactamente dónde está su reunión. No es lo mismo "subiendo" que "transcribiendo" que "ya listo".

---

### Tabla: `meeting_participants` (participantes)

**¿Qué guarda?** La relación entre una reunión y las personas que asistieron.

**La columna `speaker_label`** guarda el código que asignó pyannote a cada hablante: `SPEAKER_00`, `SPEAKER_01`, etc. Después el usuario hace el mapeo manual: "SPEAKER_00 es Carlos".

¿Por qué esta tabla existe separada? Porque una persona puede estar en muchas reuniones, y una reunión tiene muchas personas. Esto se llama una relación "muchos a muchos" y la forma correcta de modelarla en SQL es con una tabla intermedia.

---

### Tabla: `transcription_segments` (segmentos de transcripción)

**¿Qué guarda?** El texto de la reunión dividido en fragmentos pequeños, uno por cada vez que alguien habló.

```
SPEAKER_00 | 0.0s → 3.5s  | "Buenos días a todos"
SPEAKER_01 | 3.5s → 8.2s  | "Buenos días, ¿empezamos con el tema del presupuesto?"
SPEAKER_00 | 8.2s → 15.0s | "Sí. Carlos, ¿cuánto tenemos disponible?"
```

**¿Por qué con timestamps?** Para que cuando hagas clic en un action item que dice "se comprometió a las 23:45 del video", puedas ir directamente a ese momento en la grabación y escuchar el contexto exacto.

**El índice GIN:** Esta tabla tiene un índice especial que permite hacer búsqueda de texto completo. Puedes buscar "presupuesto" y encontrar todos los segmentos donde se habló de presupuesto, en cualquier reunión.

---

### Tabla: `action_items` (compromisos y tareas)

**El corazón del sistema.** Cada fila es un compromiso detectado por la IA.

**Tipos de items (`item_type`):**
```
action_item  → Tarea concreta asignada: "Carlos prepara el informe"
decision     → Decisión tomada: "Acordamos cambiar el proveedor"
commitment   → Promesa implícita: "Yo lo veo" / "Me encargo"
risk         → Riesgo identificado: "Puede que no lleguemos al plazo"
```

¿Por qué clasificar en 4 tipos? Porque no todos tienen el mismo peso. Una "decisión" ya está tomada y no necesita seguimiento. Un "action item" sí. Un "riesgo" necesita atención pero no tiene un responsable claro.

**Columnas de métricas:**
- `was_on_time` — ¿Se completó antes del deadline? Se calcula automáticamente cuando alguien marca el item como "completado"
- `days_overdue` — ¿Cuántos días tarde llegó? 0 si fue a tiempo
- `ai_confidence` — Qué tan seguro está Claude de haber identificado correctamente este item (0.0 a 1.0)

**¿Por qué guardar `context_quote`?** Para que cuando alguien diga "yo nunca dije eso", puedas mostrar la cita textual de lo que dijo en la reunión.

---

### Tabla: `action_item_updates` (historial de cambios)

**¿Qué guarda?** Cada cambio que se hace a un action item.

Si alguien cambia el deadline de un item, queda registrado:
```
campo: due_date
valor anterior: 2026-04-15
nuevo valor: 2026-04-22
quién lo cambió: supervisor@empresa.com
cuándo: 2026-04-14 10:23 AM
nota: "El proveedor pidió más tiempo"
```

**¿Por qué esto es importante?** Porque evita discusiones del tipo "¿quién movió la fecha?". Hay una pista de auditoría inmutable.

---

### Tabla: `webhook_events` (eventos de Zoom/Teams)

**¿Qué guarda?** Todos los eventos recibidos de Zoom y Teams.

**¿Por qué existe?** Por el concepto de **idempotencia**. Cuando Zoom nos envía una notificación de "hay una nueva grabación", a veces la envía 2 o 3 veces si no recibe respuesta rápido. Sin esta tabla, procesaríamos la misma reunión 3 veces.

Con esta tabla, el sistema revisa: "¿ya procesé este evento?". Si ya existe, lo ignora. Si es nuevo, lo procesa.

---

### Vistas materializadas (tablas precalculadas para el Dashboard)

**`mv_person_adherence`** — Para cada persona: cuántos items tiene, cuántos completó, % de adherencia.

**`mv_monthly_kpis`** — Por mes: cuántas reuniones, cuántos items, tasa global de cumplimiento.

**¿Por qué "materializadas"?** Una vista normal recalcula el resultado cada vez que la consultas. Con 10,000 action items, eso tardaría segundos. Una vista materializada guarda el resultado en disco y lo actualiza cada hora. El dashboard carga en <50 milisegundos.

---

## 6. El pipeline de procesamiento paso a paso

Este es el viaje completo de una grabación:

### Paso 1: El usuario sube el archivo

```
Usuario arrastra el MP4 al navegador
    ↓
El frontend envía el archivo al backend (POST /api/meetings/{id}/upload)
    ↓
El backend valida: ¿Es MP4/M4A/WAV? ¿Pesa menos de 500MB?
    ↓
Sube el archivo a Supabase Storage (guardado privado, no accesible públicamente)
    ↓
Actualiza la BD: meeting.status = 'queued'
    ↓
Responde al frontend: "¡Recibido! Procesando..."
    ↓
El frontend muestra "En cola" en la barra de progreso
```

### Paso 2: El worker de transcripción recibe el job

```
Celery Worker detecta un nuevo job en la cola de Redis
    ↓
Descarga el archivo de Supabase Storage a una carpeta temporal
    ↓
Actualiza BD: meeting.status = 'transcribing'
    ↓
Extrae el audio con ffmpeg:
    MP4 (video+audio) → WAV 16kHz mono (solo audio, más liviano)
    Por qué: Whisper no necesita el video, solo el audio.
             WAV 16kHz es el formato nativo de Whisper, sin re-encodear.
    ↓
Transcribe con faster-whisper:
    - Detecta idioma (español)
    - Filtra silencios (VAD filter)
    - Genera segmentos con timestamps: (0.0s → 3.5s, "texto...")
    ↓
Diariza con pyannote:
    - Identifica cuántos hablantes hay (supongamos 3)
    - Crea un mapa temporal: "de 0s a 15s habla SPEAKER_00"
    ↓
Merge de transcripción + diarización:
    Para cada segmento de Whisper, busca qué speaker de pyannote
    tuvo más "overlap" de tiempo con ese segmento.
    Resultado: cada segmento queda con su SPEAKER_XX asignado.
    ↓
Guarda en BD: tablas transcriptions + transcription_segments
    ↓
Actualiza BD: meeting.status = 'transcribed'
    ↓
Encola el siguiente job: analysis_task
```

### Paso 3: El worker de análisis LLM

```
Celery Worker recibe job de análisis
    ↓
Actualiza BD: meeting.status = 'analyzing'
    ↓
Formatea la transcripción como texto legible:
    [SPEAKER_00]:
      Buenos días a todos
    [SPEAKER_01]:
      Procedemos con el tema del presupuesto...
    ↓
Divide el texto en chunks de 4,000 tokens con overlap de 500 tokens:
    Por qué: Claude puede manejar texto largo, pero la calidad
             de extracción baja al final de textos muy largos.
             Con chunks más pequeños, cada uno recibe atención completa.
             El overlap (los últimos 500 tokens de chunk anterior son
             los primeros 500 del siguiente) evita perder compromisos
             que caen en el límite entre dos chunks.
    ↓
Para cada chunk → llamada a Claude API:
    Prompt: "Extrae todos los action_items, decisions, commitments y risks"
    Claude responde con JSON estructurado:
    {
      "items": [
        {
          "type": "commitment",
          "title": "Carlos revisará el informe de ventas",
          "assignee": "Carlos",
          "due_date_iso": "2026-04-18",
          "confidence": 0.92
        }
      ]
    }
    ↓
Merge de todos los chunks + deduplicación:
    Si el mismo compromiso aparece en dos chunks (por el overlap),
    se elimina el duplicado comparando el título.
    ↓
Guarda en BD: tablas ai_analyses + action_items
    ↓
Actualiza BD: meeting.status = 'analyzed'
    ↓
Supabase Realtime notifica al frontend → la pantalla se actualiza
    ↓
El usuario ve sus action items en el Kanban
```

---

## 7. Cómo instalar y correr el proyecto

### Pre-requisitos (instalar una sola vez)

| Herramienta | Para qué | Dónde descargar |
|-------------|----------|-----------------|
| Node.js 20+ | Correr el frontend | nodejs.org |
| Docker Desktop | Correr el backend sin instalar Python | docker.com/products/docker-desktop |
| Git | Ya instalado (tienes Git Bash) | — |

### Paso 1: Configurar el frontend

```bash
# Abre Git Bash o cualquier terminal
cd "C:\Users\supervisor.ventas\Desktop\meetingboard\frontend"

# Instalar todas las librerías (solo la primera vez)
npm install

# Crear el archivo de configuración
cp .env.example .env.local
# Editar .env.local con tus credenciales de Supabase (ver Sección 8)

# Arrancar el servidor de desarrollo
npm run dev
# → La app abre en http://localhost:5173
```

### Paso 2: Configurar el backend

```bash
cd "C:\Users\supervisor.ventas\Desktop\meetingboard\backend"

# Crear el archivo de configuración
cp .env.example .env
# Editar .env con tus credenciales (ver Sección 8)

# Levantar todo el backend con Docker (API + Redis + Worker)
docker compose up
# → La API corre en http://localhost:8000
# → La documentación de la API: http://localhost:8000/docs
```

### Comandos útiles

```bash
# Ver logs del backend en tiempo real
docker compose logs -f api

# Ver logs del worker de Celery
docker compose logs -f worker

# Apagar todo el backend
docker compose down

# Verificar que el frontend compila sin errores
npm run typecheck

# Construir el frontend para producción
npm run build
```

---

## 8. Configurar Supabase (base de datos)

Supabase es gratuito. Estos son los pasos para conectar el proyecto.

### Paso 1: Crear el proyecto

1. Ir a **supabase.com** → Crear cuenta (gratis)
2. Clic en **"New project"**
3. Nombre: `meetingboard`
4. Contraseña de base de datos: anota esta contraseña, la necesitarás
5. Región: **South America (São Paulo)** (la más cercana a Perú)
6. Esperar ~2 minutos mientras crea el proyecto

### Paso 2: Ejecutar el schema SQL

1. En tu proyecto de Supabase, ir a **SQL Editor** (ícono de terminal en el menú izquierdo)
2. Clic en **"New query"**
3. Abrir el archivo: `meetingboard\supabase\migrations\001_meetingboard_schema.sql`
4. Copiar TODO el contenido y pegarlo en el editor de Supabase
5. Clic en **"Run"** (botón verde, o Ctrl+Enter)
6. Deberías ver: `Success. No rows returned`

Esto crea las 10 tablas, los índices, los triggers y las vistas materializadas.

### Paso 3: Crear el bucket de Storage

1. En Supabase, ir a **Storage** (ícono de archivo en el menú)
2. Clic en **"New bucket"**
3. Nombre: `meeting-recordings`
4. **MUY IMPORTANTE:** Desmarcar "Public bucket" → debe ser **privado**
   - Por qué: las grabaciones son confidenciales. Un bucket privado requiere
     autenticación para acceder. Un bucket público cualquiera puede ver los archivos.
5. Clic en **"Create bucket"**

### Paso 4: Obtener las credenciales

1. Ir a **Project Settings** → **API**
2. Copiar:
   - **Project URL** → va en `VITE_SUPABASE_URL` (frontend) y `SUPABASE_URL` (backend)
   - **anon public** key → va en `VITE_SUPABASE_ANON_KEY` (frontend) y `SUPABASE_ANON_KEY` (backend)
   - **service_role** key → va en `SUPABASE_SERVICE_ROLE_KEY` (solo backend, NUNCA en frontend)
   - **JWT Secret** → va en `SUPABASE_JWT_SECRET` (solo backend)

⚠️ **IMPORTANTE sobre las claves:**
- La clave `anon` es pública — puede estar en el frontend (el navegador la puede ver)
- La clave `service_role` es SECRETA — solo para el servidor backend, nunca en el frontend. Esta clave bypasea toda la seguridad de la base de datos.

### Paso 5: Actualizar los archivos .env

**Frontend** (`frontend/.env.local`):
```env
VITE_SUPABASE_URL=https://tuproyecto.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
```

**Backend** (`backend/.env`):
```env
SUPABASE_URL=https://tuproyecto.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_JWT_SECRET=tu-jwt-secret
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://redis:6379/0
```

### Paso 6: Crear el primer usuario

1. En Supabase, ir a **Authentication** → **Users**
2. Clic en **"Add user"** → **"Create new user"**
3. Email: tu correo
4. Password: una contraseña segura
5. Clic en **"Create user"**

Con esto ya puedes hacer login en http://localhost:5173

---

## 9. Las fases del proyecto

El proyecto se construye en fases. Aquí está el estado actual y lo que viene.

### ✅ Fase 0 — Infraestructura Base (COMPLETADA)

**Qué se hizo:**
- Estructura completa de carpetas del proyecto
- Frontend con React: todas las páginas creadas con UI vacía
- Backend con FastAPI: todos los endpoints creados
- Workers de Celery con la lógica de transcripción y análisis
- Schema completo de base de datos (10 tablas, índices, triggers)
- Docker Compose para levantar el stack completo
- GitHub Actions para CI/CD
- Primer commit en git

**Por qué primero infraestructura:**
No puedes construir un edificio sin cimientos. Esta fase establece todos los patrones que se usarán en las fases siguientes. Una vez que la estructura está, agregar features es agregar código dentro de la estructura, no crear nueva.

---

### 🔜 Fase 1 — Upload Manual + Transcripción

**Qué se hará:**
- Botón "Nueva Reunión" con formulario
- Modal de drag & drop para subir archivos MP4/M4A
  (arrastras el archivo y lo sueltas en la pantalla)
- Barra de progreso en tiempo real mientras se transcribe
  (usa Supabase Realtime: la BD notifica al navegador automáticamente)
- Pantalla de detalle de la reunión con la transcripción segmentada por hablante
- UI para mapear "SPEAKER_00" → "Carlos López"

**Por qué esta fase es el MVP real:**
Con solo esto, el sistema ya es útil. Puedes subir una reunión, ver quién dijo qué, y las personas ya pueden usar la transcripción aunque aún no haya action items automáticos.

---

### 🔜 Fase 2 — Análisis LLM + Kanban Action Log

**Qué se hará:**
- Activar el worker de análisis con Claude API
- Las tarjetas del Kanban se llenan automáticamente después de analizar
- Drag & drop para mover tarjetas entre columnas
- Modal de edición de cada action item
- Historial de cambios visible en cada tarjeta
- Filtros por reunión, persona, estado, tipo

---

### 🔜 Fase 3 — Dashboard + Métricas de Adherencia

**Qué se hará:**
- KPIs globales: reuniones procesadas, items totales, % adherencia
- Gráfico de barras: adherencia por persona (quién cumple más/menos)
- Gráfico de líneas: tendencia mensual de cumplimiento
- Tabla de personas con ranking de cumplimiento
- Actualización automática cada hora de las vistas materializadas

---

### 🔜 Fase 4 — Notificaciones Email

**Qué se hará:**
- Email automático 48h antes del deadline: "Tienes una tarea que vence el jueves"
- Email cuando te asignan un nuevo action item
- Email cuando alguien marca como completado algo que era tuyo
- Página de configuración para activar/desactivar cada tipo

**Tecnología:** Resend.com — 100 emails/día gratis, fácil de configurar.

---

### 🔜 Fase 5 — Integración Zoom API

**Qué se hará:**
- Conectar Zoom con MeetingBoard una sola vez (configuración en Settings)
- Desde ese momento: cuando una reunión de Zoom termina de grabarse, automáticamente llega a MeetingBoard y empieza a procesarse
- No hay que hacer nada manualmente

**Cómo funciona tecnicamente:**
Zoom tiene un sistema de "webhooks": cuando termina una grabación, Zoom envía automáticamente una notificación a una URL que tú configuras. MeetingBoard recibe esa notificación, descarga la grabación, y la encola para procesar.

---

### 🔜 Fase 6 — Integración Microsoft Teams

Similar a Zoom pero usando Microsoft Graph API. Más complejo porque Teams no tiene webhooks nativos — se hace polling (consultar) cada 30 minutos si hay nuevas grabaciones en OneDrive.

---

### 🔜 Fase 7 — Producción + Observabilidad

**Qué se hará:**
- Deploy en producción: frontend en Vercel, backend en Railway
- Monitoreo de errores con Sentry (te avisa si algo falla)
- GitHub Actions completo: cada PR genera un preview deployment
- Documentación de usuario con capturas de pantalla

---

## 10. Glosario técnico

Términos que aparecen en el código y en esta guía:

| Término | Significado simple |
|---------|-------------------|
| **Frontend** | La parte que ves en el navegador (HTML, CSS, JavaScript) |
| **Backend** | El servidor que procesa datos (Python) |
| **API** | Interfaz de comunicación entre frontend y backend. El frontend "pregunta" y el backend "responde" |
| **Endpoint** | Una URL específica del backend que hace una cosa concreta. Ej: `/api/meetings/upload` |
| **Schema** | Una carpeta dentro de la base de datos que agrupa tablas relacionadas |
| **Trigger** | Código SQL que se ejecuta automáticamente cuando ocurre algo (ej: cuando se completa un item) |
| **Vista materializada** | Tabla calculada que se guarda en disco para responder consultas rápidas |
| **Worker** | Proceso separado que ejecuta tareas largas en segundo plano |
| **Queue / Cola** | Lista de trabajos pendientes que los workers van tomando uno por uno |
| **Webhook** | Notificación automática que un servicio externo (Zoom) envía a tu servidor cuando ocurre algo |
| **HMAC** | Forma de verificar que un webhook es genuino (que realmente lo envió Zoom y no alguien malicioso) |
| **JWT** | Token de autenticación. Como un "pase" digital que prueba que eres quien dices ser |
| **RLS** | Row Level Security. Reglas que dicen "este usuario solo puede ver sus propios datos" |
| **Diarización** | Proceso de identificar quién habló cuándo en una grabación de audio |
| **Transcripción** | Convertir audio hablado en texto escrito |
| **Chunk** | Pedazo. Dividir un texto largo en pedazos manejables para el LLM |
| **Overlap** | Solapamiento. El chunk 2 empieza un poco antes de donde terminó el chunk 1, para no perder contexto |
| **LLM** | Large Language Model. Un modelo de IA que entiende y genera texto (como Claude) |
| **Docker** | Sistema para empaquetar aplicaciones con todas sus dependencias en un "contenedor" portátil |
| **Docker Compose** | Herramienta para levantar múltiples contenedores Docker con un solo comando |
| **CI/CD** | Integración Continua / Despliegue Continuo. Sistema automatizado que verifica y despliega código |
| **Pull Request (PR)** | Propuesta de cambio de código que pasa por revisión antes de integrarse al proyecto principal |
| **Idempotencia** | Propiedad de una operación que produce el mismo resultado sin importar cuántas veces se ejecute |
| **Audit trail** | Historial inmutable de todos los cambios. Como una caja negra de avión para tu base de datos |
| **Adherencia** | % de compromisos cumplidos sobre el total de compromisos asignados |
| **Kanban** | Método visual de gestión de tareas con columnas de estado (Pendiente → En Progreso → Completado) |

---

## Notas importantes de seguridad

1. **NUNCA subas el archivo `.env` a GitHub.** Este archivo contiene contraseñas y API keys. El archivo `.gitignore` ya lo excluye, pero es importante que lo sepas.

2. **La clave `service_role` de Supabase es como la llave maestra.** Solo va en el backend. Si la pones en el frontend, cualquier persona que inspeccione el código fuente del navegador podría acceder a TODA tu base de datos.

3. **Los archivos de grabación son privados.** El bucket de Supabase Storage debe ser privado. Las URLs para acceder a los archivos son firmadas y expiran en 1 hora.

4. **Las firmas HMAC de Zoom son obligatorias.** Cuando el webhook de Zoom llega al servidor, se verifica su firma criptográfica. Esto previene que alguien externo envíe datos falsos a tu sistema.

---

## Estado actual del proyecto

**Fecha de inicio:** 15 de abril de 2026
**Fase actual:** 0 (Infraestructura Base) — COMPLETADA
**Archivos creados:** 56
**Primer commit git:** ✅

**Próximo paso:** Configurar Supabase (Sección 8) y luego arrancar la Fase 1 con el upload de archivos.

---

*Este documento se actualiza a medida que avanza el proyecto.*
