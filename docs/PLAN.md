# Plan de Implementación — Chatbot UPC

> **Versión:** 1.0
> **Fecha:** 2026-05-05
> **Owner:** Renzo Leñes
> **Tipo:** Documento de planificación técnica para tesis

---

## 1. Contexto

Sistema de chatbot conversacional para atención al estudiante en el proceso de matrícula universitaria (UPC). El sistema combina:

- **Canal estudiante:** WhatsApp (Meta Cloud API)
- **Inteligencia:** RAG (Retrieval-Augmented Generation) con OpenAI + LangChain sobre documentos oficiales UPC (mallas, calendarios, becas, reglamentos)
- **CRM administrativo:** Web app para que asesores supervisen, hagan takeover, gestionen documentos, intenciones y reportes

**Alcance del piloto:** 45 alumnos reales, evaluación manual de calidad de respuestas durante implementación.

**Backlog:** 34 historias de usuario (HU01–HU34) distribuidas en 5 sprints. Mockup admin completo en Pencil (`design/chatbot-admin.pen`).

---

## 2. Arquitectura

### 2.1 Diagrama físico

Ver `DiagramaFisicoV1.png` en raíz del repo.

**Dos visiones:**

| Aspecto | Arquitectura objetivo (defensa tesis) | Implementación piloto (Free Tier) |
|---|---|---|
| Compute | 3x Auto Scaling Groups (Next.js, FastAPI, Celery) | **1x EC2 t3.micro** con Docker Compose |
| Load Balancer | ALB | nginx en la EC2 |
| Cache | ElastiCache Redis | Redis dentro del docker-compose |
| Base de datos | RDS PostgreSQL + pgvector | RDS db.t3.micro + pgvector (free 750h/mes) |
| Storage docs | S3 | S3 (5GB free) |
| Cola async | SQS | SQS (1M req free) o Redis broker |
| Notificaciones | SNS | SNS (1M publish free) |
| Auth admin | Cognito | Cognito (50K MAU free) |
| DNS / TLS | Route 53 + Certificate Manager | Route 53 + ACM |
| Observabilidad | CloudWatch métricas custom | CloudWatch logs básicos |

**Justificación:** durante el piloto se mantiene una sola instancia para minimizar costos. La arquitectura escalable se documenta como diseño objetivo que se activa cuando el volumen lo justifique.

### 2.2 Flujo principal

**Estudiante envía mensaje:**

```
WhatsApp Estudiante
   ↓ (webhook Meta Cloud API)
FastAPI /webhooks/whatsapp
   ↓ (validar firma HMAC + encolar)
SQS (o Redis broker)
   ↓
Celery Worker
   ↓
   1. Clasificar intención (LLM)
   2. Retrieval en pgvector (top-k chunks)
   3. Generar respuesta (LLM con contexto)
   4. Persistir mensaje + intent + tokens consumidos
   5. Enviar respuesta vía Meta Cloud API
```

**Admin opera CRM:**

```
Admin → Next.js (Cognito JWT) → FastAPI → PostgreSQL
                                     ↓
                              S3 (subir/leer PDFs)
                                     ↓
                              Celery (re-indexar al subir doc)
```

---

## 3. Stack técnico

### Backend (`apps/api/`)

- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 async
- **Migraciones:** Alembic
- **Validación:** Pydantic v2
- **Settings:** pydantic-settings
- **Worker:** Celery (broker Redis local, SQS en producción)
- **Vector store:** pgvector dentro de Postgres
- **RAG:** LangChain (loaders, splitters, retrievers, agents)
- **LLM:** OpenAI `gpt-4o-mini`
- **Embeddings:** OpenAI `text-embedding-3-small` (1536 dims)
- **Logging:** structlog (JSON estructurado + correlation_id)
- **Testing:** pytest + testcontainers (Postgres+pgvector real)
- **Lint/format:** ruff
- **Type checking:** mypy strict
- **Package manager:** **uv** (no pip, no poetry)

### Frontend (`apps/web/`)

- **Framework:** Next.js 16 (App Router)
- **UI:** React 19
- **Estilos:** Tailwind v4 con `@theme` mapeado a tokens del diseño Pencil
- **Componentes:** shadcn/ui + Lucide icons
- **Auth:** AWS Amplify Auth (Cognito) o oidc-client-ts
- **HTTP client:** fetch nativo + tipos generados desde OpenAPI del API
- **Lint/format:** ESLint + Prettier
- **Performance:** Server Components por defecto, RSC para data fetching, Client Components solo cuando se necesita interactividad

### Infra y DevOps

- **Local:** Docker Compose (Postgres+pgvector, Redis, opcional LocalStack)
- **AWS:** Free Tier — 1x EC2 t3.micro, RDS db.t3.micro, S3, SQS, SNS, Cognito, Route 53, ACM
- **IaC:** Terraform o AWS CDK (Fase posterior)
- **CI/CD:** GitHub Actions (lint + test, deploy manual al inicio)

---

## 4. Estructura del monorepo

```
chatbot-upc/
├── apps/
│   ├── web/                          # Next.js admin
│   │   ├── src/
│   │   ├── package.json
│   │   └── ...
│   └── api/                          # FastAPI + Celery worker
│       ├── src/
│       │   └── chatbot_api/
│       │       ├── api/              # HTTP layer (Fase 2)
│       │       │   ├── dependencies.py    # get_current_admin
│       │       │   ├── webhooks.py        # /webhooks/whatsapp (sin v1)
│       │       │   └── v1/
│       │       │       ├── router.py      # aggregator
│       │       │       └── endpoints/     # auth, conversations, ...
│       │       ├── core/             # settings, db, logging, security, lifespan
│       │       ├── middlewares/      # correlation_id (Fase 2)
│       │       ├── models/           # SQLAlchemy ORM (Fase 1)
│       │       ├── repositories/     # data access — BaseRepository[Model, Create, Update] (Fase 2)
│       │       ├── schemas/          # Pydantic shapes I/O (Fase 2)
│       │       ├── services/         # business logic (Fase 2)
│       │       ├── rag/              # LangChain pipeline (Fase 3)
│       │       ├── workers/          # Celery tasks (Fase 4)
│       │       └── prompts/          # system prompts versionados (Fase 3)
│       ├── alembic/                  # migraciones (Fase 1)
│       ├── tests/
│       ├── scripts/                  # seed.py, etc.
│       ├── pyproject.toml            # uv
│       └── Dockerfile
├── packages/
│   └── shared-types/                 # tipos TS generados desde openapi.json
├── design/                           # Pencil .pen + previews HTML
├── docs/                             # PLAN.md, ADRs
├── infra/                            # docker init.sql, Terraform/CDK futuro
├── scrapping/                        # one-shot externo, NO runtime
├── docker-compose.yml                # postgres+pgvector + redis local
├── pnpm-workspace.yaml
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
└── README.md
```

**Arquitectura por capas (Fase 2+):**

```
HTTP Request
   ↓
api/v1/endpoints/   ← routers thin (parse, HTTP codes)
   ↓
services/           ← business logic + Pydantic conversion
   ↓
repositories/       ← data access (queries SQLAlchemy)
   ↓
models/             ← ORM declarative
```

**Decisiones de estructura:**

- `apps/api/src/chatbot_api/` (src layout) facilita el packaging y evita imports relativos confusos.
- Patrón clean architecture (router → service → repository → model) según skill `fastapi-templates`.
- `repositories/` con `BaseRepository[Model, Create, Update]` genérico para CRUD básico, extendido por dominio.
- `services/` como clases con singleton al final de cada archivo.
- Worker Celery vivirá dentro de `apps/api/workers/` como módulo (Fase 4), comparte modelos y settings con el API.
- `packages/shared-types/` se genera con `openapi-typescript` desde `openapi.json` del API (Fase 5).
- `scrapping/` se queda sin tocar (es one-shot, no parte del runtime).

---

## 5. Decisiones operativas

### 5.1 Manejo de secretos

- **Local:** `.env` en cada `apps/*` (gitignored) + `.env.example` versionado con todas las keys vacías.
- **Producción AWS:** AWS Secrets Manager o SSM Parameter Store. Lectura via boto3 al iniciar la app.
- **Nunca:** keys hardcoded en código ni en migraciones.

**Variables principales (ver `.env.example`):**

```bash
# OpenAI
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Meta WhatsApp
META_VERIFY_TOKEN=
META_APP_SECRET=
META_PHONE_NUMBER_ID=
META_ACCESS_TOKEN=
META_GRAPH_API_VERSION=v21.0

# Database
DATABASE_URL=postgresql+asyncpg://chatbot:chatbot@localhost:5432/chatbot
DATABASE_URL_SYNC=postgresql://chatbot:chatbot@localhost:5432/chatbot  # Alembic

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# AWS
AWS_REGION=us-east-1
AWS_S3_BUCKET=chatbot-upc-docs
COGNITO_USER_POOL_ID=
COGNITO_CLIENT_ID=
COGNITO_REGION=us-east-1

# App
ENV=local                      # local | staging | production
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

### 5.2 Convenciones de código

**Python (`apps/api/`):**

- `uv` para dependency management y venv.
- `ruff` para lint + format (reemplaza black + isort + flake8).
- `mypy --strict` en CI (en local opcional).
- Type hints en todo. Nada de `Any` salvo justificado.
- Async by default en routers y services (FastAPI nativo).
- `pyproject.toml` único, sin `requirements.txt` ni `setup.py`.

**TypeScript (`apps/web/`):**

- ESLint + Prettier (ya configurados).
- `strict: true` en `tsconfig.json`.
- Server Components por defecto. Client Components (`"use client"`) solo cuando se necesite estado, eventos del navegador o hooks.
- Data fetching en Server Components con `fetch()` y caching de Next.js.
- Convenciones de Vercel React Best Practices: minimizar `useEffect`, preferir Server Actions para mutaciones.

### 5.3 Logging

**structlog** con configuración global:

- Formato JSON en producción, consola color en local.
- `correlation_id` por cada mensaje WhatsApp y cada request HTTP. Se propaga a Celery via headers.
- Niveles: `DEBUG` local, `INFO` en producción.
- Nunca loggear contenido completo de mensajes con PII en producción (solo metadatos: `student_id_hash`, `intent`, `latency_ms`).

```python
# ejemplo
log = structlog.get_logger()
log.info("message_received", student_id=phone_hash, correlation_id=cid, channel="whatsapp")
```

### 5.4 Testing

**pytest + testcontainers:**

- Fixture `postgres` levanta `pgvector/pgvector:pg16` por sesión de tests.
- Fixture `db_session` rollback por test (transaction isolation).
- Mocks solo para servicios externos: OpenAI, Meta Cloud API.
- Coverage objetivo: **70%** en `services/` y `rag/`. Routers se testean con `TestClient`.
- E2E: 5–10 escenarios críticos (recibir mensaje WA → respuesta correcta, takeover, subir doc → indexación).

### 5.5 Pre-commit hooks

`.pre-commit-config.yaml` con:

- `ruff format` + `ruff check --fix` (Python)
- `prettier --write` (JS/TS/MD)
- `check-yaml`, `check-json`, `end-of-file-fixer`, `trailing-whitespace`
- `mypy` opcional (lento, solo si CI)

Setup:

```bash
uv add --dev pre-commit
pre-commit install
```

---

## 6. Modelo de datos

Schema diseñado a partir de las HUs admin. Todas las tablas con `created_at`/`updated_at` automáticos y `id` UUID v7 (excepto donde tenga sentido natural key).

### Tablas

#### `admins`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| cognito_sub | text | unique, identificador Cognito |
| email | text | unique |
| name | text | |
| role | enum | `admin`, `supervisor`, `viewer` |
| active | bool | default true |
| created_at | timestamptz | |

#### `students`
| Campo | Tipo | Notas |
|---|---|---|
| phone_e164 | text | PK (formato `+51...`) |
| display_name | text | nullable, viene de Meta profile |
| first_seen_at | timestamptz | |
| last_seen_at | timestamptz | |

#### `conversations`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| student_phone | text | FK students |
| status | enum | `abierta`, `cerrada`, `takeover` |
| opened_at | timestamptz | |
| closed_at | timestamptz | nullable |
| closed_by | UUID | FK admins, nullable |
| takeover_admin | UUID | FK admins, nullable |
| meta | jsonb | tags, etiquetas, etc. |

#### `messages`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| conversation_id | UUID | FK conversations, indexed |
| role | enum | `bot`, `student`, `admin` |
| content | text | |
| intent_id | UUID | FK intents, nullable |
| retrieved_chunks | jsonb | array de `{chunk_id, score}` |
| input_tokens | int | tracking costos OpenAI |
| output_tokens | int | tracking costos OpenAI |
| model_used | text | `gpt-4o-mini`, `gpt-4o`, etc. |
| latency_ms | int | tiempo de respuesta del LLM |
| meta_message_id | text | id de Meta para idempotencia |
| created_at | timestamptz | indexed |

#### `documents`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| title | text | |
| source_type | enum | `upload`, `scraped`, `link` |
| source_url | text | nullable |
| s3_key | text | path en bucket |
| sha256 | text | unique, dedupe |
| version | int | empieza en 1 |
| version_history | jsonb | array de versiones anteriores: `{version, sha256, replaced_at}` |
| status | enum | `pending`, `indexing`, `indexed`, `error` |
| error_message | text | nullable |
| uploaded_by | UUID | FK admins |
| indexed_at | timestamptz | nullable |
| created_at | timestamptz | |

#### `document_chunks`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| document_id | UUID | FK documents (cascade delete) |
| chunk_text | text | |
| embedding | vector(1536) | índice HNSW |
| metadata | jsonb | `{page, section, tipo}` |
| chunk_index | int | orden dentro del documento |

#### `intents`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| name | text | unique, ej `consulta_fechas_pago` |
| description | text | |
| examples | jsonb | array de ejemplos para few-shot |
| active | bool | |
| created_by | UUID | FK admins |
| created_at | timestamptz | |

#### `conversation_intents`
| Campo | Tipo | Notas |
|---|---|---|
| conversation_id | UUID | FK conversations |
| intent_id | UUID | FK intents |
| confidence | float | 0..1 |
| detected_at | timestamptz | |

PK compuesta `(conversation_id, intent_id, detected_at)`.

#### `notifications`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| template_name | text | nombre de plantilla aprobada en Meta |
| audience_filter | jsonb | `{intent: "...", status: "..."}` |
| scheduled_at | timestamptz | |
| sent_at | timestamptz | nullable |
| status | enum | `draft`, `scheduled`, `sending`, `sent`, `failed` |
| sent_count | int | |
| failed_count | int | |
| created_by | UUID | FK admins |

#### `prompt_versions`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| name | text | `agent_main`, `intent_classifier` |
| version | int | |
| content | text | el system prompt |
| active | bool | solo uno activo por `name` |
| created_by | UUID | FK admins |
| created_at | timestamptz | |

#### `metrics_daily`
| Campo | Tipo | Notas |
|---|---|---|
| date | date | PK |
| conversations_total | int | |
| conversations_takeover | int | |
| messages_total | int | |
| avg_response_ms | int | |
| total_input_tokens | bigint | |
| total_output_tokens | bigint | |
| intent_distribution | jsonb | `{intent_id: count}` |
| cost_usd | numeric(10,4) | calculado |

### Índices clave

- `messages.conversation_id` btree
- `messages.created_at` btree
- `document_chunks.embedding` HNSW (cosine distance)
- `document_chunks.document_id` btree
- `conversations.status` btree (filtros del admin)
- `students.last_seen_at` btree

### Convenciones

- **UUID v7** (sortable por tiempo): mejor que UUID v4 para índices.
- **Hard-delete chunks** al actualizar versión de documento. Histórico va en `documents.version_history` jsonb. Razón: simplicidad y suficiente para auditoría de tesis.
- **Filtros pgvector:** `WHERE document_id IN (SELECT id FROM documents WHERE status='indexed')` para excluir docs en re-indexación.

---

## 7. Plan de fases

### Fase 0 — Monorepo (1–2h)

**Objetivo:** estructura base lista para que ambos apps coexistan.

**Tareas:**

1. Crear `pnpm-workspace.yaml` en raíz.
2. Mover `web/` → `apps/web/` preservando historia git (`git mv` o `git subtree`).
3. Crear `apps/api/` con esqueleto: `pyproject.toml` (uv init), estructura `src/chatbot_api/`.
4. Crear `docker-compose.yml`: Postgres+pgvector, Redis.
5. Crear `.env.example`, `.gitignore` consolidado, `.pre-commit-config.yaml`.
6. README raíz con instrucciones de setup.

**Entregable:** `pnpm dev` corre web; `cd apps/api && uv run uvicorn ...` corre API stub; `docker-compose up -d` levanta DB + Redis.

---

### Fase 1 — Modelo de datos + Alembic (2–3h)

**Objetivo:** schema en Postgres con pgvector, migraciones reproducibles.

**Tareas:**

1. `uv add sqlalchemy[asyncio] alembic asyncpg pgvector`
2. Configurar `alembic/env.py` para async + auto-detectar modelos.
3. Crear modelos SQLAlchemy en `apps/api/src/chatbot_api/models/`:
   - `base.py` (Base + mixins de timestamps)
   - `admin.py`, `student.py`, `conversation.py`, `message.py`
   - `document.py`, `document_chunk.py`
   - `intent.py`, `conversation_intent.py`
   - `notification.py`, `prompt_version.py`, `metrics_daily.py`
4. Migración inicial: `alembic revision --autogenerate -m "initial schema"`.
5. Migración manual para `CREATE EXTENSION IF NOT EXISTS vector;` y índice HNSW.
6. Seed mínimo: 1 admin de prueba, 3 intents base (`consulta_fechas`, `consulta_costos`, `consulta_becas`).
7. Test: `pytest tests/test_models.py` con testcontainers.

**Entregable:** `alembic upgrade head` deja la BD lista. Tests pasan.

---

### Fase 2 — FastAPI esqueleto (2–3h)

**Objetivo:** API arranca, healthcheck OK, routers stub en su lugar.

**Tareas:**

1. `uv add fastapi uvicorn pydantic-settings python-multipart structlog`
2. `apps/api/src/chatbot_api/main.py`: app FastAPI, CORS, exception handlers, structlog middleware.
3. `core/settings.py`: pydantic-settings desde `.env`.
4. `core/db.py`: AsyncEngine, AsyncSession, dependency `get_session`.
5. `core/security.py`: dependency `get_current_admin` que valida JWT Cognito (en local: bypass con header `X-Dev-User`).
6. Routers stub (devuelven `[]` o 501):
   - `routers/webhooks.py` → `POST /webhooks/whatsapp`, `GET /webhooks/whatsapp` (verify token)
   - `routers/auth.py`
   - `routers/conversations.py`
   - `routers/documents.py`
   - `routers/intents.py`
   - `routers/notifications.py`
   - `routers/reports.py`
7. `Dockerfile` multi-stage (uv install → copy code → uvicorn).
8. Test: `pytest tests/test_health.py`, `tests/test_routers_smoke.py`.

**Entregable:** `uv run uvicorn chatbot_api.main:app --reload` arranca. Swagger en `/docs`. Healthcheck `/health` devuelve 200.

---

### Fase 3 — RAG pipeline con LangChain (4–6h)

**Objetivo:** ingestar PDFs UPC y poder hacer retrieval + generación.

**Tareas:**

1. `uv add langchain langchain-openai langchain-community pypdf unstructured`
2. `apps/api/src/chatbot_api/rag/`:
   - `loaders.py` — PyPDFLoader + UnstructuredHTMLLoader
   - `splitter.py` — `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)`
   - `embeddings.py` — `OpenAIEmbeddings(model="text-embedding-3-small")`
   - `vector_store.py` — `PGVector` apuntando a Postgres del proyecto (no extension separada, usa la tabla `document_chunks`)
   - `retriever.py` — wrapper con MMR + filtros por metadata
   - `agent.py` — `create_agent` con tools: `search_knowledge_base`, `get_calendar_dates`, `escalate_to_human`
3. Prompts en `prompts/v1/`:
   - `agent_system.md` — system prompt principal (rol, tono UPC, citar fuentes)
   - `intent_classifier.md` — clasificación con few-shot
4. Worker Celery `workers/ingest.py`:
   - Task `ingest_document(document_id)` → descarga de S3 → split → embed → guarda chunks → marca `status=indexed`
5. Endpoint `POST /documents` que sube PDF a S3 y dispara la task.
6. Endpoint `POST /rag/query` (interno, para tests) que ejecuta el agent y devuelve respuesta.
7. Tests:
   - Unit: splitter, retriever
   - Integration: ingestar 1 PDF de prueba, hacer query, validar que retorna chunks relevantes
   - Mock OpenAI con responses fijas

**Entregable:** subir un PDF al endpoint → en ~30s aparece indexado → query devuelve respuesta con citas.

**Buenas prácticas LangChain aplicadas:**
- Usar `create_agent` (LangChain v1+) en vez de `AgentExecutor` deprecated.
- Tools tipados con Pydantic.
- `LangSmith` opcional para debugging traces (variable `LANGCHAIN_TRACING_V2=true`).
- Embeddings cacheados con `CacheBackedEmbeddings` para no re-embeddar el mismo chunk.

---

### Fase 4 — WhatsApp E2E (3–4h)

**Objetivo:** flujo completo estudiante ↔ bot funcionando.

**Tareas:**

1. `services/whatsapp.py`:
   - `verify_webhook(token)` — handshake Meta
   - `verify_signature(payload, signature)` — HMAC SHA256 con `META_APP_SECRET`
   - `send_message(to, body)` — POST a Graph API
   - `send_template(to, template_name, params)` — para notificaciones proactivas
   - `get_templates()` — GET de plantillas aprobadas (read-only)
2. Webhook `POST /webhooks/whatsapp`:
   - Valida firma
   - Parsea evento Meta (mensaje entrante)
   - Idempotencia con `meta_message_id`
   - Encola task Celery con `correlation_id`
3. Worker `workers/conversation.py`:
   - `process_incoming_message(payload)`:
     - Upsert student
     - Get/create conversation (status=abierta)
     - Persistir mensaje del estudiante
     - Si `conversation.status == 'takeover'`, no responder (admin tiene control)
     - Sino: clasificar intent → RAG → generar respuesta → enviar Meta → persistir respuesta bot
4. Lógica de takeover (HU14):
   - Triggers: confianza intent < 0.7, palabras `asesor`/`humano`/`persona`, o trigger manual desde admin
   - Cuando se activa: cambiar `conversation.status='takeover'`, notificar al admin asignado vía SNS/email
5. Endpoints admin para gestionar conversaciones:
   - `GET /conversations` (filtros: status, fecha, intent)
   - `POST /conversations/{id}/takeover`
   - `POST /conversations/{id}/release` (devolver al bot)
   - `POST /conversations/{id}/messages` (admin envía mensaje)
   - `POST /conversations/{id}/close`
   - `POST /conversations/{id}/reopen` (HU30)
6. Tests E2E con webhook mock.

**Entregable:** mandar WA a número Meta sandbox → llega respuesta del bot con info real. Admin puede hacer takeover.

---

### Fase 5 — Conectar frontend (2–3h)

**Objetivo:** reemplazar mocks del Next.js por datos reales del API.

**Tareas:**

1. Generar tipos TS desde OpenAPI:
   - `pnpm add -D openapi-typescript` en root
   - Script: `openapi-typescript http://localhost:8000/openapi.json -o packages/shared-types/api.d.ts`
2. Cliente HTTP en `apps/web/src/lib/api.ts`:
   - `fetch` wrapper con base URL desde env
   - Interceptor que añade JWT Cognito al header `Authorization`
   - Tipos importados desde `shared-types`
3. Auth Cognito en Next.js:
   - Setup AWS Amplify Auth o oidc-client-ts
   - Middleware `app/middleware.ts` que protege rutas admin
   - Login page conectada a Cognito hosted UI o flow custom
4. Reemplazar mocks por React Server Components con `fetch`:
   - `app/(admin)/conversations/page.tsx` → fetch real desde API
   - `app/(admin)/dashboard/page.tsx` → fetch métricas
   - `app/(admin)/documents/page.tsx` → fetch + upload real
   - etc.
5. Mutaciones con Server Actions o `use mutation` patterns.
6. WebSocket o polling para mensajes nuevos en `/conversations/{id}` (decidir según latencia aceptable).

**Entregable:** admin se autentica con Cognito, ve conversaciones reales, puede subir PDF y verlo indexarse, puede hacer takeover.

**Buenas prácticas Next.js / Vercel aplicadas:**
- Server Components por defecto, fetch con caching estratégico.
- Suspense + streaming para loading states.
- Mutaciones con Server Actions, no `useEffect + fetch`.
- Rutas dinámicas con `generateStaticParams` donde aplique.
- Bundle analysis con `@next/bundle-analyzer` antes de prod.

---

## 8. Roadmap y siguientes pasos

### Inmediato (esta sesión)

- [x] Validar mockup vs backlog (HU27, HU30 ya implementadas en Pencil)
- [x] Definir arquitectura física (diagrama)
- [x] Tomar decisiones de stack
- [x] Documentar plan (este archivo)
- [ ] **Ejecutar Fase 0 + Fase 1 + Fase 2** ← siguiente

### Corto plazo (Sprint 1)

- Fase 3 — RAG pipeline funcionando con 5–10 PDFs UPC
- Fase 4 — Webhook WhatsApp recibiendo y respondiendo
- Setup Cognito User Pool + crear admin de prueba
- Crear plantillas Meta para notificaciones proactivas

### Mediano plazo (Sprint 2-3)

- Fase 5 — Frontend conectado al API real
- Dashboard con métricas reales
- Sistema de intenciones editable desde UI
- Reportes exportables

### Largo plazo (Sprint 4-5)

- Push notifications operativas (HU push notif)
- Reportes avanzados con gráficos
- Optimización de prompts basada en evaluación manual de los 45 alumnos
- IaC con Terraform/CDK
- CI/CD GitHub Actions
- Documentación final para tesis

---

## 9. Métricas de éxito (para tesis)

| Métrica | Meta piloto |
|---|---|
| Tasa de respuesta automática (sin takeover) | ≥ 70% |
| Latencia p95 respuesta bot | < 3s |
| Costo promedio por conversación | < $0.05 USD |
| Precisión clasificación intent | ≥ 80% (eval manual) |
| Documentos indexados | ≥ 30 PDFs UPC |
| Usuarios piloto | 45 alumnos |
| Disponibilidad servicio | ≥ 95% durante piloto |

---

## 10. Referencias

- Mockup admin: `design/chatbot-admin.pen`
- Diagrama físico: `DiagramaFisicoV1.png`
- Backlog Excel: `apps/frontend/public/images/Product_Backlog_Chatbot_RAG_v7 (1).xlsx`
- Spec scraper: `scrapping/SPEC.md`
- Memoria del proyecto: `~/.claude/projects/.../memory/MEMORY.md`

---

**Próximo paso:** ejecutar Fase 0 (monorepo) + Fase 1 (modelo de datos) + Fase 2 (FastAPI esqueleto) en una sola sesión.
