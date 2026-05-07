# Plan de Implementación — Chatbot UPC

> **Versión:** 2.0 (rewrite tras auditoría de fases 0–2 implementadas)
> **Fecha:** 2026-05-07
> **Owner:** Renzo Leñes
> **Tipo:** Documento de planificación técnica para tesis

---

## Tabla de contenidos

1. [Contexto](#1-contexto)
2. [Estado actual](#2-estado-actual)
3. [Arquitectura](#3-arquitectura)
4. [Stack técnico](#4-stack-técnico)
5. [Estructura del monorepo](#5-estructura-del-monorepo)
6. [Endpoints REST](#6-endpoints-rest)
7. [Modelo de datos](#7-modelo-de-datos)
8. [Convenciones de código](#8-convenciones-de-código)
9. [Plan de fases](#9-plan-de-fases)
10. [Mapeo HU ↔ endpoint ↔ pantalla](#10-mapeo-hu--endpoint--pantalla)
11. [Métricas de éxito](#11-métricas-de-éxito)
12. [Referencias](#12-referencias)

---

## 1. Contexto

Sistema conversacional para atención a estudiantes en el proceso de matrícula UPC. Tres piezas:

- **Canal estudiante:** WhatsApp (Meta Cloud API).
- **Inteligencia:** RAG con OpenAI + LangChain sobre documentos oficiales UPC (mallas, calendarios, becas, reglamentos). Agente con tools (`search_knowledge_base`, `escalate_to_human`).
- **CRM administrativo:** Web app Next.js 16 para que asesores supervisen, hagan takeover, gestionen documentos, intenciones, notificaciones y reportes.

**Alcance del piloto:** 45 alumnos reales. Evaluación manual de calidad de respuestas durante el período de implementación.

**Backlog:** ≈32–34 historias (HU01–HU34) distribuidas en 5 sprints. **El archivo `Product_Backlog_Chatbot_RAG_v7 (1).xlsx` no está commiteado en el repo** — hay que recuperarlo del PO antes de cerrar el mapeo HU↔endpoint (ver §10).

**Mockup admin:** `design/chatbot-admin.pen` (Pencil) — 100% navegable, ya traducido a Next.js mock-only.

---

## 2. Estado actual

Snapshot al 2026-05-07. Fases 0/1/2 implementadas; fases 3/4/5 pendientes.

### Implementado

| Capa | Estado | Notas |
|---|---|---|
| Monorepo (`apps/web`, `apps/api`, `docker-compose.yml`) | [x] | Fase 0: `2460a7c` + fix `b95011c` |
| Modelos SQLAlchemy (11 tablas) + enums + base mixin | [x] | Fase 1: `6b9b82f` + fix `89d5341` |
| Migraciones Alembic (extensions, schema inicial, índices HNSW, seed, índices auxiliares) | [x] | 5 revisiones, BD reproducible |
| FastAPI esqueleto + routers v1 + auth dev bypass + layered architecture | [x] | Fase 2: `ab7f0ae` + fix `86d8c8b` + refactor `11d246c` (services funcionales + webhook /api/webhooks) |
| Endpoints **read** (auth/me, conversations, documents, intents, notifications, reports) | [x] | 12 endpoints respondiendo 200 + `/health` con DB ping |
| Endpoints **write** (takeover, release, close, reopen, send message, upload doc, intent CRUD, notification create) | [ ] | 12 endpoints stub 501 (5 conversations writes + 2 documents writes + 3 intents CUD + 2 notifications: templates+create) |
| Frontend admin (Next.js 16, App Router, shadcn/ui, todas las pantallas con `useMockStore`) | [x] | Mock-only, no consume API real |
| Auth Cognito (web + API) | [ ] | Stub en `apps/web/src/app/login`. Dev bypass `X-Dev-User` en API |
| RAG pipeline (loaders, splitter, embeddings, retriever, agent) | [ ] | Sin carpeta `rag/` aún (se crea en Fase 3) |
| Worker Celery + broker Redis | [ ] | `docker-compose.yml` ya tiene Redis listo |
| Webhook WhatsApp + Meta Cloud API integration | [~] | Webhook básico funcional en `api/webhooks.py` (verify token GET + acepta POST). HMAC + Celery dispatch en Fase 4 |

### Próximas fases

- **Fase 3** — RAG ingest + retrieval + generación (incluye `POST /documents`, `DELETE /documents`).
- **Fase 4** — WhatsApp E2E (webhook + Celery worker + Meta API) + writes de conversaciones (takeover, send, close, reopen) + CRUD intents + notifications create.
- **Fase 5** — Frontend conectado al API real + Auth.js v5 con Cognito + observabilidad.

---

## 3. Arquitectura

### 3.1 Diagrama físico

Ver `DiagramaFisicoV1.png` en raíz. Dos visiones según madurez:

| Aspecto | Arquitectura objetivo (defensa de tesis) | Implementación piloto (Free Tier) |
|---|---|---|
| Compute | 3× Auto Scaling Groups (Next.js, FastAPI, Celery) | **1× EC2 t3.micro** con Docker Compose |
| Load Balancer | ALB | nginx en la EC2 |
| Cache | ElastiCache Redis | Redis dentro del docker-compose |
| Base de datos | RDS PostgreSQL 16 + pgvector | RDS db.t3.micro + pgvector (free 750h/mes) |
| Storage docs | S3 | S3 (5 GB free) |
| Cola async | SQS | Redis broker (Celery) en piloto |
| Notificaciones | SNS | SNS (1M publish free) |
| Auth admin | Cognito User Pool | Cognito (50K MAU free) |
| DNS / TLS | Route 53 + ACM | Route 53 + ACM |
| Observabilidad | CloudWatch métricas custom | CloudWatch logs + structlog JSON |

**Justificación:** durante el piloto se mantiene una sola instancia para minimizar costo. La arquitectura escalable se documenta como diseño objetivo y se activa cuando el volumen lo justifique.

### 3.2 Flujo principal

**Estudiante envía mensaje:**

```
WhatsApp Estudiante
   ↓ webhook Meta Cloud API
FastAPI POST /api/webhooks/whatsapp
   ↓ valida HMAC + idempotencia (meta_message_id)
   ↓ encola en Celery (broker Redis local / SQS prod)
Celery Worker (workers/conversation.py)
   ↓ 1. Upsert student + conversation
   ↓ 2. Persistir mensaje entrante
   ↓ 3. Si conversation.status == 'takeover' → noop
   ↓ 4. Si no:
   ↓    a. Clasificar intent (LLM con few-shot)
   ↓    b. RAG retrieval en pgvector (top-k chunks con MMR)
   ↓    c. create_agent invoca tools si es necesario
   ↓    d. Generar respuesta (LLM con contexto + citas)
   ↓    e. Persistir mensaje bot + intent + tokens + latencia
   ↓ 5. Enviar respuesta vía Meta Cloud API
```

**Admin opera CRM:**

```
Admin → /login (form custom shadcn)
     ↓ Auth.js Credentials Provider
     ↓ POST /api/v1/auth/login (FastAPI bridge)
     ↓ boto3 cognito_idp.initiate_auth
Cognito User Pool valida → JWT
     ↓ Auth.js guarda en cookie httpOnly
Admin navega (app)/* → middleware.ts protege rutas
     ↓ RSC fetch a FastAPI con Authorization: Bearer <jwt>
FastAPI valida JWT contra JWKs de Cognito → procesa
     ↓
PostgreSQL / S3 / Celery (re-indexación al subir doc)
```

### 3.3 Arquitectura por capas (clean architecture)

```
HTTP Request
   ↓
api/v1/endpoints/*.py    ← funciones async thin: parse params, HTTP codes, delegar
   ↓
services/*.py            ← business logic — TODOS módulos funcionales (RORO, sin clases)
                              · estado compartido (httpx client, agente LLM, S3 client)
                                en variables _privadas a nivel de módulo
                              · funciones públicas async def planas
   ↓
repositories/*.py        ← BaseRepository[Model, Create, Update] genérico
                              + funciones específicas por dominio
   ↓
models/*.py              ← ORM SQLAlchemy declarative
```

**Reglas:**
- Endpoints nunca tocan SQLAlchemy directo. Solo invocan services.
- Services nunca devuelven ORM models a la capa HTTP — convierten a Pydantic primero.
- Repositories devuelven ORM models o `None`. No conocen Pydantic.
- **Services siempre como módulos funcionales.** Si un service necesita un recurso compartido (httpx client persistente, agente LangChain construido, cliente S3), va como variable `_privada` a nivel de módulo. Python ya garantiza que el módulo se inicializa una sola vez por proceso. Sin clases, sin `self`, sin singleton al final del archivo. Si en el futuro se necesitan múltiples instancias del mismo recurso (ej. dos cuentas Meta), recién ahí se evalúa pasar a clase.

---

## 4. Stack técnico

### 4.1 Backend (`apps/api/`)

- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 async
- **Migraciones:** Alembic
- **Validación:** Pydantic v2
- **Settings:** pydantic-settings
- **Worker:** Celery (broker Redis local, SQS en producción)
- **Vector store:** pgvector dentro del Postgres del proyecto (no Chroma, no FAISS, no Pinecone)
- **RAG:** LangChain v1+ (`create_agent`, `@tool`, `RecursiveCharacterTextSplitter`, `OpenAIEmbeddings`)
- **LLM:** OpenAI `gpt-4o-mini` (clasificación + generación)
- **Embeddings:** OpenAI `text-embedding-3-small` (1536 dims)
- **Auth (validación JWT):** `python-jose[cryptography]` + `httpx` para fetch JWKs cacheado del User Pool. `boto3` para `initiate_auth` en el bridge `/api/v1/auth/login`.
- **Logging:** structlog (JSON estructurado + correlation_id)
- **Testing:** pytest + testcontainers (Postgres+pgvector real, no mocks de DB)
- **Lint/format:** ruff
- **Type checking:** mypy strict en CI
- **Package manager:** **uv** (no pip, no poetry)

> **Decisión de RAG (importante):** **no usamos `langchain_postgres.PGVector` wrapper**. PGVector crea sus propias tablas (`langchain_pg_embedding`, `langchain_pg_collection`) que colisionan con nuestro modelo `document_chunks`. En su lugar, calculamos embeddings con `OpenAIEmbeddings.embed_documents()` y los persistimos directamente en `document_chunks.embedding` vía SQLAlchemy. La búsqueda usa el operador pgvector `<=>` (cosine distance). Detalle en §9 Fase 3.

### 4.2 Frontend (`apps/web/`)

- **Framework:** Next.js 16 (App Router)
- **UI:** React 19
- **Estilos:** Tailwind v4 con `@theme` mapeado a tokens del diseño Pencil
- **Componentes:** shadcn/ui + Lucide icons
- **Auth:** **Auth.js v5 (NextAuth) con `CredentialsProvider`**. Login UI 100% custom (form shadcn en `/login`). El `authorize()` callback llama a `POST /api/v1/auth/login` del backend, que internamente habla con Cognito vía boto3. Auth.js gestiona la sesión, guarda el JWT en cookie httpOnly, expone `auth()` server-side y middleware ready para proteger `(app)/*`.
- **HTTP client:** `fetch` nativo + tipos generados desde `openapi.json` del API
- **State server-side:** Server Components por defecto + `fetch` con caching de Next.js
- **State client:** `useState`/`useReducer` para UI local; SWR solo si se necesita cliente-side dedupe
- **Mutaciones:** Server Actions
- **Lint/format:** ESLint + Prettier

### 4.3 Skills aplicados

El plan se apoya en cinco skills de Claude Code que aportan patrones validados:

| Skill | Aplicación en el proyecto |
|---|---|
| `langchain-rag` | Pipeline ingest (Fase 3): `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`, `OpenAIEmbeddings(model="text-embedding-3-small")`, MMR retrieval (`fetch_k=20, lambda_mult=0.5, k=5`). |
| `langchain-fundamentals` | Agent (Fase 3): `create_agent(model, tools, system_prompt)` en lugar de `AgentExecutor`. Tools con `@tool` y descripciones explícitas. `recursion_limit=10` en invoke config. |
| `fastapi-templates` | API: `BaseRepository[Model, Create, Update]` genérico, JWT con `OAuth2PasswordBearer`, `get_db` con commit/rollback automático. |
| `fastapi-python` | Services como módulos funcionales (RORO), early returns, guard clauses, `HTTPException` para errores esperados, lifespan context manager. Combina con `fastapi-templates`: `BaseRepository` genérico (clase) + services funcionales (módulo). |
| `vercel-react-best-practices` | Frontend (Fase 5): Server Components con `Promise.all` para evitar waterfalls; `next/dynamic` para componentes pesados; imports directos (no barrel files); `useTransition` para loading. |

### 4.4 Infra y DevOps

- **Local:** Docker Compose (Postgres+pgvector, Redis). Opcional LocalStack para SQS/S3.
- **AWS:** Free Tier — 1× EC2 t3.micro, RDS db.t3.micro, S3, SQS, SNS, Cognito, Route 53, ACM.
- **IaC:** Terraform o AWS CDK (Sprint 4–5).
- **CI/CD:** GitHub Actions (ruff + mypy + pytest + ESLint). Deploy manual al inicio.

---

## 5. Estructura del monorepo

### 5.1 Árbol final completo

Este es el árbol que el repo debe tener al cierre de Fase 5. Hoy está al ~60%; el §5.2 muestra el diff por fase.

```
chatbot-upc/
├── apps/
│   ├── web/                                  # Next.js 16 admin
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── (app)/                    # layout group autenticado
│   │   │   │   │   ├── layout.tsx            # Sidebar + Topbar persistentes
│   │   │   │   │   ├── dashboard/page.tsx
│   │   │   │   │   ├── conversations/
│   │   │   │   │   │   ├── page.tsx          # redirect a [id]
│   │   │   │   │   │   ├── [id]/page.tsx     # thread + ContactInfo
│   │   │   │   │   │   └── [id]/actions.ts   # takeover, release, send, close, reopen
│   │   │   │   │   ├── documents/
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   └── actions.ts        # upload, delete
│   │   │   │   │   ├── intents/
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   └── actions.ts        # CRUD intents
│   │   │   │   │   ├── notifications/
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   └── actions.ts        # send notification
│   │   │   │   │   └── reports/page.tsx
│   │   │   │   ├── login/page.tsx            # form shadcn custom (no Hosted UI)
│   │   │   │   ├── api/auth/[...nextauth]/route.ts  # handlers Auth.js
│   │   │   │   ├── layout.tsx                # root, providers globales
│   │   │   │   └── globals.css
│   │   │   ├── components/
│   │   │   │   ├── conversations/            # ConvList, Thread, ContactInfo, ConversationActions
│   │   │   │   ├── dashboard/                # DashboardHeader, KpiCard, IntentChart
│   │   │   │   ├── documents/                # DocumentsTable, DocumentsStats, UploadDrawer
│   │   │   │   ├── intents/                  # IntentRow, IntentEditorModal
│   │   │   │   ├── notifications/            # NotificationsDropdown, NotificationModal
│   │   │   │   ├── reports/                  # ConversationsTimeseries, IntentsDistribution
│   │   │   │   ├── shell/                    # Sidebar, Topbar
│   │   │   │   └── ui/                       # shadcn primitives
│   │   │   ├── lib/
│   │   │   │   ├── api/
│   │   │   │   │   ├── client.ts             # fetch wrapper + JWT injection (server-side)
│   │   │   │   │   ├── conversations.ts
│   │   │   │   │   ├── documents.ts
│   │   │   │   │   ├── intents.ts
│   │   │   │   │   ├── notifications.ts
│   │   │   │   │   └── reports.ts
│   │   │   │   ├── mock.ts                   # se ELIMINA al cierre de Fase 5
│   │   │   │   └── utils.ts
│   │   │   ├── auth.ts                       # NextAuth({ providers: [Credentials({...})] })
│   │   │   └── middleware.ts                 # auth() de Auth.js para proteger (app)/*
│   │   ├── public/
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   ├── tsconfig.json
│   │   └── tailwind.config.ts
│   └── api/                                  # FastAPI + Celery
│       ├── src/chatbot_api/
│       │   ├── api/                          # HTTP layer
│       │   │   ├── dependencies.py           # get_session, get_current_admin, get_correlation_id
│       │   │   ├── webhooks.py               # POST/GET /api/webhooks/whatsapp
│       │   │   └── v1/
│       │   │       ├── router.py             # APIRouter aggregator
│       │   │       └── endpoints/
│       │   │           ├── auth.py           # /me, /login (bridge a Cognito), /logout
│       │   │           ├── conversations.py
│       │   │           ├── documents.py
│       │   │           ├── intents.py
│       │   │           ├── notifications.py
│       │   │           └── reports.py
│       │   ├── core/
│       │   │   ├── settings.py               # pydantic-settings
│       │   │   ├── db.py                     # AsyncEngine, AsyncSessionLocal, get_session
│       │   │   ├── logging.py                # structlog config
│       │   │   ├── security.py               # JWKs cache + verify_jwt + boto3 cognito_idp client
│       │   │   ├── lifespan.py               # startup/shutdown hooks
│       │   │   └── celery_app.py             # Celery instance
│       │   ├── middlewares/
│       │   │   └── correlation_id.py
│       │   ├── models/                       # ORM (11 tablas)
│       │   │   ├── base.py
│       │   │   ├── enums.py
│       │   │   ├── admin.py, student.py
│       │   │   ├── conversation.py, message.py
│       │   │   ├── document.py, document_chunk.py
│       │   │   ├── intent.py, conversation_intent.py
│       │   │   ├── notification.py, prompt_version.py, metrics_daily.py
│       │   │   └── __init__.py
│       │   ├── repositories/                 # BaseRepository + funciones por dominio
│       │   │   ├── base.py                   # BaseRepository[Model, Create, Update] PEP 695
│       │   │   ├── admin.py                  # Fase 2 ✓
│       │   │   ├── conversation.py           # Fase 2 ✓
│       │   │   ├── message.py                # Fase 2 ✓
│       │   │   ├── document.py               # Fase 2 ✓
│       │   │   ├── intent.py                 # Fase 2 ✓
│       │   │   ├── notification.py           # Fase 2 ✓
│       │   │   ├── document_chunk.py         # Fase 3 (cuando tenga endpoints/RAG)
│       │   │   ├── student.py                # Fase 4 (cuando tenga endpoints)
│       │   │   ├── prompt_version.py         # Fase 4 (admin CRUD prompts)
│       │   │   └── metrics_daily.py          # Fase 5 (reports avanzados)
│       │   ├── schemas/                      # Pydantic v2 I/O
│       │   │   ├── common.py                 # ErrorResponse, HealthResponse
│       │   │   ├── pagination.py             # Page[T] PEP 695, PageParams
│       │   │   ├── admin.py                  # AdminRead
│       │   │   ├── student.py                # StudentRead
│       │   │   ├── conversation.py           # ConversationListItem, ConversationDetail
│       │   │   ├── message.py                # MessageRead
│       │   │   ├── document.py               # DocumentRead (chunk_count computed)
│       │   │   ├── intent.py                 # IntentRead
│       │   │   └── notification.py           # NotificationRead
│       │   ├── services/                     # todos módulos funcionales (RORO)
│       │   │   ├── conversation_service.py   # sin estado compartido
│       │   │   ├── document_service.py       # sin estado (S3 client en core/aws.py)
│       │   │   ├── intent_service.py         # sin estado
│       │   │   ├── notification_service.py   # sin estado
│       │   │   ├── report_service.py         # sin estado
│       │   │   ├── whatsapp_service.py       # _client httpx a nivel de módulo
│       │   │   └── rag_service.py            # _agent LangChain a nivel de módulo
│       │   ├── rag/                          # Pipeline LangChain
│       │   │   ├── loaders.py                # PyPDFLoader + UnstructuredHTMLLoader
│       │   │   ├── splitter.py               # RecursiveCharacterTextSplitter
│       │   │   ├── embeddings.py             # OpenAIEmbeddings + CacheBackedEmbeddings
│       │   │   ├── retriever.py              # custom: SQLAlchemy + pgvector <=>
│       │   │   ├── agent.py                  # create_agent con tools
│       │   │   └── tools.py                  # @tool search_knowledge_base, escalate_to_human
│       │   ├── prompts/
│       │   │   └── v1/
│       │   │       ├── agent_system.md
│       │   │       └── intent_classifier.md
│       │   ├── workers/                      # Celery tasks
│       │   │   ├── ingest.py                 # ingest_document(document_id)
│       │   │   ├── conversation.py           # process_incoming_message(payload)
│       │   │   └── notifications.py          # send_notification_batch(notification_id)
│       │   └── main.py                       # FastAPI app + routers
│       ├── alembic/
│       │   ├── env.py
│       │   └── versions/
│       │       ├── 0000_extensions.py
│       │       ├── 0001_initial_schema.py
│       │       ├── 0002_pgvector_indexes.py
│       │       ├── 0003_seed_baseline.py
│       │       └── 0004_students_last_seen_index.py
│       ├── tests/
│       │   ├── conftest.py                   # fixtures pg testcontainer + factory_boy
│       │   ├── factories.py
│       │   ├── unit/                         # services + rag (mocked OpenAI)
│       │   ├── integration/                  # endpoints contra DB real
│       │   └── e2e/                          # webhook → respuesta WA
│       ├── scripts/
│       │   └── seed.py
│       ├── pyproject.toml                    # uv
│       ├── uv.lock
│       └── Dockerfile
├── packages/
│   └── shared-types/                         # tipos TS desde openapi.json (Fase 5)
│       ├── api.d.ts
│       └── package.json
├── design/                                   # Pencil .pen + previews
├── docs/
│   ├── PLAN.md                               # este archivo
│   ├── ENDPOINTS.md                          # mapeo HU↔endpoint detallado (Fase 3)
│   └── adr/                                  # decisiones arquitectónicas
├── infra/
│   ├── docker/                               # init.sql con CREATE EXTENSION
│   └── terraform/                            # IaC futuro
├── scrapping/                                # one-shot externo, NO runtime
├── docker-compose.yml
├── pnpm-workspace.yaml
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
└── README.md
```

### 5.2 Diff por fase

Lo que se agrega en cada fase respecto al árbol final:

**Fase 0 (DONE):** raíz del monorepo, `apps/web/`, `apps/api/` esqueleto, `docker-compose.yml`, `.env.example`, configs root. Commits: `2460a7c` + fix `b95011c` (init.sql con CREATE EXTENSION, .gitignore consolidado, scripts dev/test/lint).

**Fase 1 (DONE):** `apps/api/src/chatbot_api/models/*.py` (11 modelos + enums), `alembic/` y 5 migraciones (0000_extensions, 0001_initial, 0002_pgvector_indexes, 0003_seed_baseline, 0004_students_last_seen_index), `scripts/seed.py`, `tests/test_models.py`. Commits: `6b9b82f` + fix `89d5341` (índice last_seen_at, lazy engine, conftest cleanup).

**Fase 2 (DONE):** Layered architecture completa:
- `core/{settings,db,logging,security,lifespan}.py`, `middlewares/correlation.py`
- `api/dependencies.py` (`get_current_admin` con regex email validation), `api/v1/router.py` aggregator, 6 endpoints en `api/v1/endpoints/`, `api/webhooks.py` (bajo `/api/webhooks/*`)
- 6 repositories: `base.py` (`BaseRepository[Model, Create, Update]` PEP 695) + admin/conversation/message/document/intent/notification
- 6 services como **módulos funcionales** (RORO, sin clases): conversation/document/intent/notification/report. `get_active_by_email` consumido directo desde `repositories/admin.py` por `dependencies.py` (sin `admin_service`)
- 9 schemas Pydantic v2 (common, pagination, admin, student, conversation, message, document, intent, notification)
- `tests/{test_health,test_models,test_routers_smoke,test_routers_reads,factories,conftest}.py` (34 tests pasando)
- `Dockerfile` con HEALTHCHECK
- Commits: `ab7f0ae` + fix `86d8c8b` (N+1 con scalar subqueries correlated, lifespan en tests con asgi-lifespan, structlog ↔ stdlib bridge) + refactor `11d246c` (services class→funcional + webhook prefix `/api/webhooks/*`).

**Fase 3 (TODO):**
- `apps/api/src/chatbot_api/repositories/document_chunk.py` (NUEVO)
- `apps/api/src/chatbot_api/services/{document_service.py amplía writes, rag_service.py NUEVO}`
- `apps/api/src/chatbot_api/rag/{loaders,splitter,embeddings,retriever,agent,tools}.py` (NUEVO directorio)
- `apps/api/src/chatbot_api/prompts/v1/{agent_system,intent_classifier}.md` (NUEVO)
- `apps/api/src/chatbot_api/workers/ingest.py` (NUEVO directorio `workers/`)
- `apps/api/src/chatbot_api/core/celery_app.py`, `core/aws.py` (S3 client lazy)
- Endpoints write `POST /documents`, `DELETE /documents/{id}` pasan a 200/202
- `tests/integration/test_rag_*.py`

**Fase 4 (TODO):**
- `apps/api/src/chatbot_api/services/whatsapp_service.py` (NUEVO; estado compartido `_client` httpx a nivel de módulo)
- `apps/api/src/chatbot_api/workers/{conversation,notifications}.py`
- `apps/api/src/chatbot_api/repositories/{student.py, prompt_version.py}` cuando tengan endpoints
- Endpoints write conversations (takeover/release/close/reopen/messages) + intents CRUD + notifications create pasan a 200/201/202
- `api/webhooks.py` se refuerza con HMAC SHA256 + idempotencia + dispatch Celery
- `core/security.py` se completa con JWKs verify (validación JWT real, fin del dev bypass)
- `tests/e2e/test_whatsapp_flow.py`

**Fase 5 (TODO):**
- `apps/web/src/lib/api/*.ts` (cliente HTTP por dominio)
- `apps/web/src/auth.ts` + `middleware.ts` (Auth.js v5 + Credentials provider)
- `apps/web/src/app/api/auth/[...nextauth]/route.ts` (handlers)
- `apps/web/src/app/(app)/**/actions.ts` (Server Actions)
- `apps/api/src/chatbot_api/api/v1/endpoints/auth.py` agrega `POST /login` (bridge a Cognito vía boto3)
- `packages/shared-types/api.d.ts` (generado por `openapi-typescript`)
- Eliminar `apps/web/src/lib/mock.ts`

---

## 6. Endpoints REST

### 6.1 Convenciones

- **Base path:** `/api/v1` (excepto webhooks: `/api/webhooks/*` y health: `/health`).
- **Webhooks sin versión** porque dependen del proveedor externo (Meta). Bajo `/api/*` para que el reverse proxy enrute todo lo del backend con un solo upstream.
- **IDs:** `BIGINT` autoincrement (BIGSERIAL) en path params. Excepción: `students.phone_e164` natural PK; `metrics_daily.date` natural PK; `conversation_intents` PK compuesta. UUID v7 reservado para futuras columnas `public_id` si se necesita ID no-secuencial expuesto.
- **Paginación:** `?page=1&size=20` → respuesta `{items, total, page, size, pages}` (esquema `Page[T]` en `schemas/pagination.py`).
- **Errores:** RFC 7807 problem+json. Dominio-específicos vía exception handlers en `main.py`.
- **Auth:**
  - Todos los `/api/v1/*` (excepto `/auth/login`) requieren JWT Cognito en header `Authorization: Bearer <jwt>`. Validado contra JWKs del User Pool (cacheados).
  - En local: header `X-Dev-User: <email>` cuando `ENV=local` (bypass solo en development).

### 6.2 Tabla completa

Estado: `[x]` implementado · `[~]` 501 stub · `[ ]` aún sin definir.

| Método | Ruta | Estado | Fase | Pantalla / consumidor | HU (TODO) |
|---|---|---|---|---|---|
| GET | `/health` | [x] | 2 | DB ping (FE devs, K8s/Docker liveness probe) | — |
| GET | `/api/webhooks/whatsapp` | [x] | 2 | Meta verify token (handshake funcional; refuerzo HMAC en Fase 4) | — |
| POST | `/api/webhooks/whatsapp` | [x] | 2 | Meta event delivery (acepta payload + 200; HMAC + dispatch Celery en Fase 4) | — |
| **POST** | **`/api/v1/auth/login`** | [ ] | 5 | `/login` form (Auth.js bridge) | TBD |
| POST | `/api/v1/auth/logout` | [ ] | 5 | Topbar / Auth.js | TBD |
| GET | `/api/v1/auth/me` | [x] | 2 | providers, header user info | TBD |
| GET | `/api/v1/conversations` | [x] | 2 | `(app)/conversations` | TBD |
| GET | `/api/v1/conversations/{id}` | [x] | 2 | `(app)/conversations/[id]` | TBD |
| GET | `/api/v1/conversations/{id}/messages` | [x] | 2 | `Thread` component | TBD |
| POST | `/api/v1/conversations/{id}/takeover` | [~] | 4 | `ConversationActions` | TBD |
| POST | `/api/v1/conversations/{id}/release` | [~] | 4 | `ConversationActions` | TBD |
| POST | `/api/v1/conversations/{id}/close` | [~] | 4 | `ConversationActions` | TBD |
| POST | `/api/v1/conversations/{id}/reopen` | [~] | 4 | `ConversationActions` | TBD (HU30) |
| POST | `/api/v1/conversations/{id}/messages` | [~] | 4 | `Thread` (admin envía) | TBD |
| GET | `/api/v1/documents` | [x] | 2 | `(app)/documents` | TBD |
| GET | `/api/v1/documents/{id}` | [x] | 2 | `DocumentsTable` preview | TBD |
| POST | `/api/v1/documents` | [~] | 3 | `UploadDrawer` | TBD |
| DELETE | `/api/v1/documents/{id}` | [~] | 3 | `DocumentsTable` action | TBD |
| GET | `/api/v1/intents` | [x] | 2 | `(app)/intents` | TBD |
| GET | `/api/v1/intents/{id}` | [x] | 2 | `IntentRow` expand | TBD |
| POST | `/api/v1/intents` | [~] | 4 | `IntentEditorModal` | TBD |
| PUT | `/api/v1/intents/{id}` | [~] | 4 | `IntentEditorModal` | TBD |
| DELETE | `/api/v1/intents/{id}` | [~] | 4 | `IntentEditorModal` | TBD |
| GET | `/api/v1/notifications` | [x] | 2 | `NotificationsDropdown` | TBD |
| GET | `/api/v1/notifications/templates` | [~] | 4 | `NotificationModal` | TBD (HU27) |
| POST | `/api/v1/notifications` | [~] | 4 | `NotificationModal` | TBD (HU27) |
| GET | `/api/v1/reports/dashboard` | [x] | 2 | `(app)/dashboard` | TBD |
| GET | `/api/v1/reports/conversations` | [x] | 2 | `(app)/reports` | TBD |
| GET | `/api/v1/reports/intents` | [x] | 2 | `(app)/reports` | TBD |

**Total:** 26 endpoints `/api/v1/*` + 2 webhooks `/api/webhooks/*` + 1 `/health` = **29**. La columna HU se completa cuando el backlog Excel sea recuperado.

---

## 7. Modelo de datos

Schema implementado en Fase 1. Resumen; el código autoritativo está en `apps/api/src/chatbot_api/models/`.

**11 tablas:** `admins`, `students`, `conversations`, `messages`, `documents`, `document_chunks`, `intents`, `conversation_intents`, `notifications`, `prompt_versions`, `metrics_daily`. PK natural en `students.phone_e164` y `metrics_daily.date`. PK compuesta en `conversation_intents (conversation_id, intent_id, detected_at)`. Resto BIGINT autoincrement (BIGSERIAL).

**Relaciones clave:**
- `conversations.student_phone` → `students.phone_e164`
- `messages.conversation_id` → `conversations.id` (cascade)
- `messages.intent_id` → `intents.id` (nullable)
- `document_chunks.document_id` → `documents.id` (cascade delete)

**Embeddings:** `document_chunks.embedding vector(1536)` con índice HNSW (cosine distance).

**Convenciones:**
- BIGINT autoincrement (BIGSERIAL) para PKs simples. Decisión Fase 1 para tesis 45 alumnos: simplicidad, índices más rápidos, debug más fácil. UUID solo se considera cuando se necesite ID público no-predecible.
- Timestamps `created_at`/`updated_at` automáticos vía mixin en `models/base.py` (todos `TIMESTAMP WITHOUT TIME ZONE`, factories y services usan datetime naive UTC).
- Hard-delete de chunks al actualizar versión de documento. Histórico va en `documents.version_history` jsonb.
- Filtros pgvector siempre con `WHERE document_id IN (SELECT id FROM documents WHERE status='indexed')` para excluir docs en re-indexación.

**Índices clave:**
- `messages.conversation_id` btree
- `messages.created_at` btree
- `document_chunks.embedding` HNSW (cosine)
- `document_chunks.document_id` btree
- `conversations.status` btree
- `students.last_seen_at` btree

---

## 8. Convenciones de código

### 8.1 Python (`apps/api/`)

- `uv` para dependency management y venv. `pyproject.toml` único.
- `ruff format` + `ruff check --fix` (reemplaza black/isort/flake8).
- `mypy --strict` en CI.
- Type hints en todo. `Any` solo justificado por comentario.
- **`async def` para todo I/O; `def` para funciones puras.**
- **RORO** (Receive Object, Return Object): cada función recibe Pydantic y devuelve Pydantic.
- **Early returns + guard clauses**, evitar `else` innecesarios.
- `HTTPException` para errores esperados, modelados como respuestas HTTP específicas.
- Lifespan context manager (no `@app.on_event`).

### 8.2 TypeScript (`apps/web/`)

- ESLint + Prettier. `strict: true` en `tsconfig.json`.
- **Server Components por defecto.** `"use client"` solo cuando se necesita estado, eventos del navegador, o hooks.
- Data fetching en Server Components con `fetch()` + caching de Next.js. Mutaciones con Server Actions.
- Reglas críticas del skill `vercel-react-best-practices` aplicadas:
  - `async-parallel`: `Promise.all` para fetches independientes en RSC.
  - `bundle-barrel-imports`: importar directo (no desde `index.ts`).
  - `bundle-dynamic-imports`: `next/dynamic` para `IntentEditorModal`, `UploadDrawer`, `NotificationModal`.
  - `rendering-conditional-render`: ternarios sobre `&&` para evitar renderizar `0` o strings vacíos.
  - `rerender-derived-state-no-effect`: derivar estado durante render, no en `useEffect`.

### 8.3 Logging (structlog)

- Formato JSON en producción, consola coloreada en local.
- `correlation_id` por request HTTP y por mensaje WhatsApp. Se propaga a Celery vía headers de la task.
- Niveles: `DEBUG` local, `INFO` producción.
- **Nunca loggear contenido completo de mensajes con PII en producción.** Solo metadatos: `student_id_hash`, `intent`, `latency_ms`, `tokens`.

```python
log = structlog.get_logger()
log.info("message_received", student_id=phone_hash, correlation_id=cid, channel="whatsapp")
```

### 8.4 Testing

- pytest + testcontainers (`pgvector/pgvector:pg16`) por sesión.
- Fixture `db_session` con rollback por test.
- Mocks **solo** para servicios externos: OpenAI, Meta Cloud API, S3, Cognito.
- Coverage objetivo: **70%** en `services/` y `rag/`. Routers se testean con `TestClient`.
- E2E: 5–10 escenarios críticos.

### 8.5 Pre-commit

`.pre-commit-config.yaml`:
- `ruff format` + `ruff check --fix`
- `prettier --write` (JS/TS/MD)
- `check-yaml`, `check-json`, `end-of-file-fixer`, `trailing-whitespace`
- `mypy` en CI únicamente

---

## 9. Plan de fases

### Fase 0 — Monorepo `[x] DONE`

Commit `2460a7c`. Estructura base, docker-compose, configs root, `.env.example`.

### Fase 1 — Modelo de datos `[x] DONE`

Commit `6b9b82f`. 12 modelos SQLAlchemy + 5 migraciones Alembic + seed.

### Fase 2 — FastAPI esqueleto `[x] DONE`

Commits: `ab7f0ae` + fix `86d8c8b` + refactor `11d246c`.

**Entregado:**
- Routers v1, middlewares (`correlation.py`), settings expandido (Cognito + Meta), `core/{db,logging,security,lifespan}.py`, dev bypass `X-Dev-User` con regex email validation.
- Layered architecture completa: 6 repositories (`base.py` PEP 695 + admin/conversation/message/document/intent/notification), 6 services como **módulos funcionales** (RORO, sin clases ni singletons), 9 schemas Pydantic.
- 12 reads + 12 writes 501 + 2 webhooks (`/api/webhooks/whatsapp` GET handshake / POST recibir) + `/health` con DB ping.
- 34 tests pasando (`tests/test_health.py`, `test_models.py`, `test_routers_smoke.py`, `test_routers_reads.py`, `factories.py`, `conftest.py` con `LifespanManager`).
- N+1 arreglado: `list_filtered_with_aggregates` y `list_filtered_with_chunk_count` con scalar subqueries correlated.
- structlog ↔ stdlib bridge (uvicorn/sqlalchemy logs llevan correlation_id).
- `Dockerfile` con HEALTHCHECK.

**Reorganización tests en `tests/{unit,integration,e2e}/`** queda diferida a Fase 5 (es polish, no bloquea Fase 3).

#### Snippet — `BaseRepository` genérico (PEP 695, Python 3.12+)

```python
# apps/api/src/chatbot_api/repositories/base.py
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel


class BaseRepository[ModelType, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel]:
    """Generic CRUD repository for SQLAlchemy models."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        result = await db.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalars().first()

    async def list(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        db_obj = self.model(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, db_obj: ModelType, obj_in: UpdateSchemaType
    ) -> ModelType:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, id: Any) -> bool:
        obj = await self.get(db, id)
        if obj is None:
            return False
        await db.delete(obj)
        return True
```

#### Snippet — Service como módulo funcional (skill `fastapi-python`)

```python
# apps/api/src/chatbot_api/services/conversation_service.py
"""Business logic para conversaciones. Funcional (RORO), sin clases."""
from math import ceil
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models.enums import ConversationStatus
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.schemas.conversation import ConversationDetail, ConversationListItem
from chatbot_api.schemas.pagination import Page, PageParams


async def list_paginated(
    db: AsyncSession,
    *,
    status: ConversationStatus | None = None,
    pagination: PageParams,
) -> Page[ConversationListItem]:
    rows = await conversation_repository.list_filtered_with_aggregates(
        db, status=status, skip=pagination.offset, limit=pagination.size,
    )
    total = await conversation_repository.count_filtered(db, status=status)
    items = [
        ConversationListItem(id=conv.id, ..., message_count=cnt, last_message_preview=prev)
        for conv, cnt, prev in rows
    ]
    return Page(
        items=items, total=total, page=pagination.page, size=pagination.size,
        pages=ceil(total / pagination.size) if total else 0,
    )


async def get_detail(db: AsyncSession, conversation_id: int) -> ConversationDetail:
    conv = await conversation_repository.get_with_messages(db, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    return ConversationDetail.model_validate(conv)
```

> **Convención clave:** services raise `HTTPException` cuando aplica (404). Routers quedan ultra-thin (`return await svc.fn(...)`). Estado compartido (httpx client, agente LangChain) en variables `_privadas` a nivel de módulo, NO en clases.

---

### Fase 3 — RAG pipeline (4–6 h)

**Objetivo:** ingestar PDFs UPC, indexar en `document_chunks`, exponer retrieval + agente para que Fase 4 lo consuma.

#### Tareas

1. **Dependencias:** `uv add langchain langchain-openai langchain-community langchain-text-splitters pypdf unstructured boto3 celery[redis]`.
2. **Loaders** (`rag/loaders.py`): `PyPDFLoader` (PDF) + `UnstructuredHTMLLoader` (HTML scrapeado).
3. **Splitter** (`rag/splitter.py`): `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`.
4. **Embeddings** (`rag/embeddings.py`): `OpenAIEmbeddings(model="text-embedding-3-small")` envuelto en `CacheBackedEmbeddings` con `LocalFileStore("./.cache/embeddings")`.
5. **Retriever custom** (`rag/retriever.py`): query embedding → SQL con operador `<=>` cosine + filtros por `document_id`/`metadata`. MMR opcional vía sobre-fetch + reranking en Python.
6. **Tools** (`rag/tools.py`): `search_knowledge_base(query, top_k=5)` y `escalate_to_human(reason)`.
7. **Agente cacheado** (`services/rag_service.py`): `_agent = create_agent(...)` a nivel de módulo. Se construye una sola vez al importar (Python garantiza módulo singleton). Función pública `answer(user_text, correlation_id)`.
8. **Worker Celery** (`workers/ingest.py`): task `ingest_document(document_id)` → S3 → loader → splitter → embed → bulk insert chunks → marca `documents.status='indexed'`.
9. **Endpoints write:**
   - `POST /api/v1/documents` (multipart): valida tamaño/tipo, sube a S3, crea `documents` con `status='pending'`, dispara `ingest_document.delay(id)`, devuelve 202.
   - `DELETE /api/v1/documents/{id}`: borra de S3, cascade chunks.
10. **Tests:**
    - Unit: splitter (boundaries), retriever (filtros, k, MMR mock).
    - Integration: ingestar 1 PDF de prueba → query → validar score top-1 > umbral.
    - Mocks de OpenAI con responses fijas.

#### Decisión clave: por qué NO usamos `langchain_postgres.PGVector`

El wrapper de LangChain crea las tablas `langchain_pg_embedding` y `langchain_pg_collection` con su propio schema. Nuestro modelo `document_chunks` tiene FKs a `documents`, metadata jsonb propia y se gestiona vía Alembic. Mezclar ambos rompe migraciones y duplica almacenamiento. Mantenemos control total.

#### Snippet — Retriever custom (skill `langchain-rag`)

```python
# apps/api/src/chatbot_api/rag/retriever.py
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from chatbot_api.models.document_chunk import DocumentChunk
from chatbot_api.models.document import Document
from chatbot_api.models.enums import DocumentStatus
from chatbot_api.rag.embeddings import get_embeddings

async def retrieve(
    db: AsyncSession,
    query: str,
    *,
    k: int = 5,
    fetch_k: int = 20,
    metadata_filter: dict | None = None,
) -> list[DocumentChunk]:
    embeddings = get_embeddings()
    query_vec = await embeddings.aembed_query(query)

    stmt = (
        select(
            DocumentChunk,
            DocumentChunk.embedding.cosine_distance(query_vec).label("distance"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.status == DocumentStatus.INDEXED)
        .order_by(text("distance"))
        .limit(fetch_k)
    )
    if metadata_filter:
        for key, value in metadata_filter.items():
            stmt = stmt.where(DocumentChunk.metadata[key].astext == str(value))

    rows = (await db.execute(stmt)).all()
    return [row[0] for row in rows[:k]]
```

#### Snippet — Service con agente cacheado a nivel de módulo (skill `langchain-fundamentals`)

```python
# apps/api/src/chatbot_api/services/rag_service.py
"""Agente LangChain construido una vez al importar el módulo."""
from pathlib import Path
from langchain.agents import create_agent
from chatbot_api.rag.tools import search_knowledge_base, escalate_to_human
from chatbot_api.core.settings import settings

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "v1"

# Estado compartido — se inicializa una sola vez al importar el módulo
_system_prompt = (_PROMPTS_DIR / "agent_system.md").read_text()
_agent = create_agent(
    model=f"openai:{settings.openai_model}",
    tools=[search_knowledge_base, escalate_to_human],
    system_prompt=_system_prompt,
)

async def answer(*, user_text: str, correlation_id: str) -> dict:
    result = await _agent.ainvoke(
        {"messages": [{"role": "user", "content": user_text}]},
        config={"recursion_limit": 10, "metadata": {"correlation_id": correlation_id}},
    )
    last = result["messages"][-1]
    tool_calls = [
        tc for m in result["messages"]
        for tc in (getattr(m, "tool_calls", None) or [])
    ]
    return {"text": last.content, "tool_calls": tool_calls}
```

#### Snippet — Tools del agente

```python
# apps/api/src/chatbot_api/rag/tools.py
from langchain_core.tools import tool
from chatbot_api.core.db import AsyncSessionLocal
from chatbot_api.rag.retriever import retrieve

@tool
async def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """Busca información en los documentos oficiales UPC indexados.

    Úsala para responder preguntas sobre fechas de pago, mallas curriculares,
    becas, reglamentos. Devuelve los chunks más relevantes con su fuente.

    Args:
        query: pregunta en lenguaje natural (10–30 palabras recomendado)
        top_k: número de chunks a devolver (default 5)
    """
    async with AsyncSessionLocal() as db:
        chunks = await retrieve(db, query, k=top_k)
    return "\n\n".join(
        f"[doc:{c.document_id} chunk:{c.chunk_index}] {c.chunk_text}" for c in chunks
    )

@tool
def escalate_to_human(reason: str) -> str:
    """Marca la conversación para takeover por un asesor humano.

    Úsala cuando no puedas responder con confianza o el estudiante pida hablar
    con una persona.

    Args:
        reason: motivo breve del escalamiento
    """
    return f"ESCALATE::{reason}"
```

**Entregable:** `POST /api/v1/documents` → en ~30 s aparece `status=indexed` → `rag_service.answer(...)` devuelve respuesta con citas.

---

### Fase 4 — WhatsApp E2E + writes (3–4 h)

**Objetivo:** cerrar el flujo estudiante↔bot y los writes admin (takeover, send, close, intents CRUD, notifications).

#### Tareas

1. **`services/whatsapp_service.py` (módulo funcional):**
   - `_client = httpx.AsyncClient(...)` a nivel de módulo (persistente con timeout y retries).
   - `verify_webhook(mode, token, challenge)`, `verify_signature(payload, signature)` (HMAC-SHA256 con `META_APP_SECRET`).
   - `send_message(to, body) -> meta_message_id` (POST Graph API).
   - `send_template(to, template_name, params)`.
   - `get_templates() -> list[Template]` (read-only).
   - `shutdown()` invocado desde el lifespan para `await _client.aclose()`.

2. **Webhook real** (`api/webhooks.py`):
   - GET: handshake.
   - POST: valida firma → parsea evento → idempotencia con `meta_message_id` (UNIQUE en `messages`) → encola `process_incoming_message.delay(payload, correlation_id)`.
   - Devolver 200 < 200 ms para que Meta no reintente.

3. **Worker `workers/conversation.py`:**
   ```python
   @celery_app.task(name="chatbot.process_incoming_message", bind=True)
   def process_incoming_message(self, payload: dict, correlation_id: str) -> None:
       # 1) upsert_student(phone, display_name)
       # 2) get_or_create_open_conversation(phone)
       # 3) persist student message
       # 4) si conversation.status == 'takeover' → return
       # 5) classify_intent(text) → intent_id, confidence
       # 6) si confidence < 0.7 OR text matches /asesor|humano|persona/i:
       #       conversation.status = 'takeover'
       #       notify_admin_via_sns()
       #       send_message("Te voy a derivar con un asesor humano")
       #       return
       # 7) result = rag_service.answer(user_text=text, correlation_id=correlation_id)
       # 8) si tool ESCALATE invocado → flujo de takeover
       # 9) persist bot message (intent, retrieved_chunks, tokens, latency)
       # 10) whatsapp_service.send_message(phone, result["text"])
   ```

4. **Endpoints write conversations** (501 → 200):
   - `POST /conversations/{id}/takeover` → set status, asigna `takeover_admin=current_admin`.
   - `POST /conversations/{id}/release` → vuelve a `abierta`.
   - `POST /conversations/{id}/messages` → admin envía → persiste con `role='admin'` → `whatsapp_service.send_message`.
   - `POST /conversations/{id}/close` → `status='cerrada'`, `closed_by=admin.id`.
   - `POST /conversations/{id}/reopen` → vuelve a `abierta` (HU30).

5. **Endpoints write intents** (501 → 200/201):
   - `POST /intents`, `PUT /intents/{id}`, `DELETE /intents/{id}` → CRUD via `intent_service`. Cambios invalidan cache del classifier.

6. **Endpoints notifications** (501 → 200/201):
   - `GET /notifications/templates` → proxy a Meta Graph (read-only).
   - `POST /notifications` → crea con `status='scheduled'`, dispara `send_notification_batch.delay(id)`.

7. **`core/security.py` completo:** validación JWT con JWKs cacheados (60 min TTL).

8. **Worker `workers/notifications.py`:** itera audience, llama `whatsapp_service.send_template`, actualiza `sent_count`/`failed_count`.

9. **Tests E2E:** `tests/e2e/test_whatsapp_flow.py` con webhook mock + LLM mock.

#### Snippet — Validación JWT contra JWKs Cognito

```python
# apps/api/src/chatbot_api/core/security.py
from functools import lru_cache
from time import time
import httpx
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from chatbot_api.core.settings import settings

_jwks_cache: dict = {"keys": None, "fetched_at": 0}
_JWKS_TTL = 3600  # 1h

async def _get_jwks() -> dict:
    now = time()
    if _jwks_cache["keys"] and now - _jwks_cache["fetched_at"] < _JWKS_TTL:
        return _jwks_cache["keys"]
    url = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    _jwks_cache["keys"] = resp.json()
    _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]

bearer = HTTPBearer(auto_error=False)

async def get_current_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    # … + dev bypass header X-Dev-User cuando ENV=local
) -> AdminClaims:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_token")
    token = creds.credentials
    try:
        unverified = jwt.get_unverified_header(token)
        jwks = await _get_jwks()
        key = next(k for k in jwks["keys"] if k["kid"] == unverified["kid"])
        claims = jwt.decode(
            token,
            key,
            algorithms=[unverified["alg"]],
            audience=settings.cognito_client_id,
            issuer=(
                f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
                f"{settings.cognito_user_pool_id}"
            ),
        )
    except ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token_expired")
    except (JWTError, StopIteration):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    return AdminClaims.model_validate(claims)
```

**Entregable:** mandar WhatsApp al número Meta sandbox → llega respuesta del bot con info real. Admin puede hacer takeover desde el CRM.

---

### Fase 5 — Frontend conectado + Auth.js (3–4 h)

**Objetivo:** reemplazar `mock.ts` por datos reales del API; auth Cognito vía Auth.js v5 + Credentials provider; observabilidad básica.

#### Tareas

1. **Tipos generados** desde OpenAPI:
   ```bash
   pnpm add -D openapi-typescript -w
   pnpm dlx openapi-typescript http://localhost:8000/openapi.json -o packages/shared-types/api.d.ts
   ```

2. **Auth.js v5 setup:**
   - `pnpm add next-auth@beta` en `apps/web`.
   - `apps/web/src/auth.ts`: `NextAuth({ providers: [Credentials({ ... })] })` con `authorize()` que llama a `POST /api/v1/auth/login` y devuelve el JWT.
   - `apps/web/src/app/api/auth/[...nextauth]/route.ts`: re-export `handlers`.
   - `apps/web/src/middleware.ts`: usa `auth()` para proteger `(app)/*`.
   - `apps/web/src/app/login/page.tsx`: form shadcn con `signIn("credentials", { email, password })`.

3. **Bridge backend** `POST /api/v1/auth/login`:
   - Recibe `{email, password}`.
   - Llama `boto3.client("cognito-idp").initiate_auth(AuthFlow="USER_PASSWORD_AUTH", ...)`.
   - Devuelve `{access_token, id_token, refresh_token, expires_in, admin: {id, email, name, role}}`.
   - Errores Cognito → `HTTPException(401)`.

4. **Cliente HTTP** (`apps/web/src/lib/api/client.ts`):
   - `fetch` wrapper con base URL desde `process.env.NEXT_PUBLIC_API_URL`.
   - Server-side: lee JWT desde la sesión Auth.js (`auth()`).
   - Tipos importados desde `@chatbot/shared-types`.

5. **Reemplazar mocks por RSC:**
   - `app/(app)/conversations/page.tsx` → fetch real (server) con paginación.
   - `app/(app)/dashboard/page.tsx` → `Promise.all` de KPIs (skill rule `async-parallel`).
   - `app/(app)/documents/page.tsx` → fetch + Server Action upload.
   - `app/(app)/intents/page.tsx` → fetch + Server Actions CRUD.
   - `app/(app)/reports/page.tsx` → fetch series con `cache: "no-store"` para datos en vivo.

6. **Mutaciones con Server Actions** (no `useEffect + fetch`):
   - `app/(app)/documents/actions.ts`: `uploadDocumentAction`, `deleteDocumentAction`.
   - `app/(app)/intents/actions.ts`: `createIntentAction`, `updateIntentAction`, `deleteIntentAction`.
   - `app/(app)/conversations/[id]/actions.ts`: `takeoverAction`, `sendMessageAction`, `closeAction`, `reopenAction`, `releaseAction`.

7. **Componentes pesados con `next/dynamic`** (skill rule `bundle-dynamic-imports`):
   - `IntentEditorModal`, `UploadDrawer`, `NotificationModal` → `dynamic(() => import("..."), { ssr: false })`.

8. **Polling para mensajes nuevos** en `/conversations/[id]`: cada 5 s (suficiente para piloto). WebSocket queda como mejora.

9. **Eliminar `apps/web/src/lib/mock.ts`** y `useMockStore`.

#### Snippet — Auth.js v5 con Credentials Provider

```ts
// apps/web/src/auth.ts
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { z } from "zod";

const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      name: "Cognito (UPC)",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(raw) {
        const parsed = LoginSchema.safeParse(raw);
        if (!parsed.success) return null;

        const res = await fetch(`${process.env.API_URL}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(parsed.data),
        });
        if (!res.ok) return null;

        const data = await res.json();
        return {
          id: data.admin.id,
          email: data.admin.email,
          name: data.admin.name,
          role: data.admin.role,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          accessTokenExpires: Date.now() + data.expires_in * 1000,
        };
      },
    }),
  ],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.accessTokenExpires = user.accessTokenExpires;
        token.role = user.role;
      }
      // TODO: refresh token rotation cuando accessTokenExpires < now
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.user.role = token.role as string;
      return session;
    },
  },
  pages: { signIn: "/login" },
});
```

```ts
// apps/web/src/middleware.ts
export { auth as middleware } from "@/auth";

export const config = {
  matcher: ["/((?!api/auth|login|_next/static|_next/image|favicon.ico).*)"],
};
```

```ts
// apps/web/src/app/api/auth/[...nextauth]/route.ts
export { GET, POST } from "@/auth";
```

#### Snippet — Login page con Server Action

```tsx
// apps/web/src/app/login/page.tsx
"use client";
import { signIn } from "next-auth/react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    startTransition(async () => {
      const res = await signIn("credentials", { email, password, redirect: false });
      if (res?.error) {
        setError("Credenciales inválidas");
        return;
      }
      router.push("/dashboard");
    });
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-sm space-y-4 py-20">
      <Input type="email" placeholder="email@upc.edu.pe" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input type="password" placeholder="contraseña" value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button type="submit" disabled={isPending} className="w-full">
        {isPending ? "Ingresando…" : "Ingresar"}
      </Button>
    </form>
  );
}
```

#### Snippet — RSC con Promise.all (skill `vercel-react-best-practices`)

```tsx
// apps/web/src/app/(app)/dashboard/page.tsx
import { fetchDashboard, fetchConversationsByDay, fetchIntentsDistribution } from "@/lib/api/reports";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { IntentChart } from "@/components/dashboard/IntentChart";
import { ConversationsTimeseries } from "@/components/dashboard/ConversationsTimeseries";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string; to?: string }>;
}) {
  const { from, to } = await searchParams;
  // Paraleliza los 3 fetches independientes — evita waterfall (rule async-parallel)
  const [kpis, byDay, intents] = await Promise.all([
    fetchDashboard({ from, to }),
    fetchConversationsByDay({ from, to }),
    fetchIntentsDistribution({ from, to }),
  ]);

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-4 gap-4">
        <KpiCard label="Conversaciones hoy" value={kpis.conversations_total} />
        <KpiCard label="Takeover rate" value={`${kpis.takeover_rate}%`} />
        <KpiCard label="Latencia p95" value={`${kpis.p95_ms} ms`} />
        <KpiCard label="Costo USD" value={`$${kpis.cost_usd}`} />
      </div>
      <ConversationsTimeseries data={byDay} />
      <IntentChart data={intents} />
    </div>
  );
}
```

#### Snippet — Server Action con revalidación

```ts
// apps/web/src/app/(app)/intents/actions.ts
"use server";
import { revalidatePath } from "next/cache";
import { auth } from "@/auth";
import { apiClient } from "@/lib/api/client";

export async function createIntentAction(formData: FormData) {
  const session = await auth();
  if (!session) throw new Error("unauthorized");

  const payload = {
    name: String(formData.get("name")),
    description: String(formData.get("description")),
    examples: JSON.parse(String(formData.get("examples"))),
  };
  await apiClient(session.accessToken).post("/api/v1/intents", payload);
  revalidatePath("/intents");
}
```

**Entregable:** admin se autentica con form custom (UI 100% UPC) → JWT real de Cognito en cookie httpOnly → ve conversaciones reales, sube PDF y lo ve indexarse, ejecuta takeover y envía mensajes que llegan al WhatsApp del estudiante.

---

## 10. Mapeo HU ↔ endpoint ↔ pantalla

> **Estado:** **bloqueado parcialmente** — el archivo `Product_Backlog_Chatbot_RAG_v7 (1).xlsx` no está commiteado en el repo. No es posible cerrar el mapeo HU→endpoint sin él.
>
> **Acción requerida:** solicitar al PO el `.xlsx` (o equivalente) y commitearlo en `docs/backlog/`. Una vez disponible, completar la columna "HU" en §6.2 y mover este detalle a `docs/ENDPOINTS.md`.

### 10.1 Mapeo provisional (pantalla → endpoints)

Esto se construye desde la auditoría del frontend mock-only. Sustituye el HU faltante hasta tener el Excel.

| Pantalla | Endpoints consumidos | Skill aplicado |
|---|---|---|
| `/login` | `POST /api/v1/auth/login` (Auth.js Credentials → bridge → Cognito) | — |
| `(app)/dashboard` | `GET /reports/dashboard`, `/reports/conversations`, `/reports/intents` (paralelo) | `async-parallel` |
| `(app)/conversations` | `GET /conversations?status=...` | `server-cache-react` |
| `(app)/conversations/[id]` | `GET /conversations/{id}`, `GET /conversations/{id}/messages`, polling 5 s | `client-swr-dedup` (cliente) |
| `(app)/conversations/[id]` (actions) | `POST .../takeover`, `.../release`, `.../messages`, `.../close`, `.../reopen` | Server Actions |
| `(app)/documents` | `GET /documents?status=...` | `server-parallel-fetching` |
| `(app)/documents` (actions) | `POST /documents`, `DELETE /documents/{id}` | Server Actions + `bundle-dynamic-imports` |
| `(app)/intents` | `GET /intents?active=true` | — |
| `(app)/intents` (actions) | `POST /intents`, `PUT /intents/{id}`, `DELETE /intents/{id}` | Server Actions |
| `(app)/notifications` | `GET /notifications`, `GET /notifications/templates`, `POST /notifications` | Server Actions |
| `(app)/reports` | `GET /reports/conversations`, `/reports/intents` | `async-parallel` |
| `NotificationsDropdown` (Topbar) | `GET /notifications?status=unread` | `client-swr-dedup` |

---

## 11. Métricas de éxito (tesis)

| Métrica | Meta piloto |
|---|---|
| Tasa de respuesta automática (sin takeover) | ≥ 70% |
| Latencia p95 respuesta bot | < 3 s |
| Costo promedio por conversación | < $0.05 USD |
| Precisión clasificación intent | ≥ 80% (eval manual) |
| Documentos indexados | ≥ 30 PDFs UPC |
| Usuarios piloto | 45 alumnos |
| Disponibilidad servicio | ≥ 95% durante piloto |

---

## 12. Referencias

### Documentos del repo

- Mockup admin: `design/chatbot-admin.pen`
- Diagrama físico: `DiagramaFisicoV1.png`
- Backlog Excel: **TODO — solicitar al PO** (esperado en `docs/backlog/`)
- Spec scraper one-shot: `scrapping/SPEC.md`
- Memoria de proyecto: `~/.claude/projects/.../memory/MEMORY.md`

### Skills de Claude Code aplicados

- `langchain-rag` — pipeline ingest + retrieval (Fase 3)
- `langchain-fundamentals` — `create_agent`, `@tool`, middleware (Fase 3 + 4)
- `fastapi-templates` — `BaseRepository` genérico, JWT con dependencies (todas las fases)
- `fastapi-python` — services como módulos funcionales, RORO, early returns, lifespan (todas las fases)
- `vercel-react-best-practices` — Server Components, async-parallel, bundle-dynamic-imports (Fase 5)

### Decisiones arquitectónicas clave (resumen)

1. **Auth frontend:** Auth.js v5 con `CredentialsProvider`. Login UI 100% custom (form shadcn). NO Hosted UI, NO Amplify.
2. **Auth backend:** validación JWT contra JWKs cacheados del User Pool Cognito (`python-jose` + `httpx`). Bridge `POST /api/v1/auth/login` con boto3 `cognito_idp.initiate_auth`.
3. **Vector store:** pgvector en la BD del proyecto, modelo propio `document_chunks`. NO `langchain_postgres.PGVector` wrapper.
4. **Services:** todos como **módulos funcionales** (RORO, sin clases). Estado compartido (httpx client, agente LangChain) vive en variables `_privadas` a nivel de módulo — Python ya garantiza módulo singleton. Si en el futuro se necesitan múltiples instancias del mismo recurso, ahí se evalúa pasar a clase.
5. **Repositories:** `BaseRepository[Model, Create, Update]` clase genérica con sintaxis PEP 695 (Python 3.12+) + funciones específicas por dominio. Cada `repository/*.py` exporta singleton al final (`admin_repository = AdminRepository(Admin)`).
6. **PKs:** BIGINT autoincrement (BIGSERIAL) salvo natural PK (`students.phone_e164`, `metrics_daily.date`) y composite PK (`conversation_intents`). UUID v7 NO en uso para PKs internas.
7. **Webhook prefix:** todos los endpoints del backend bajo `/api/*` (`/api/v1/*` y `/api/webhooks/*`) para que el reverse proxy enrute con un solo upstream. `/health` queda en root para liveness probes estándar.
8. **Frontend:** Server Components por defecto, mutaciones con Server Actions, `next/dynamic` para componentes pesados, `Promise.all` en RSC.

---

## Próximo paso inmediato

1. **Fase 3 — RAG pipeline:** dependencias LangChain (`langchain`, `langchain-openai`, `langchain-community`, `pypdf`, `unstructured`, `boto3`, `celery[redis]`), `rag/{loaders,splitter,embeddings,retriever,agent,tools}.py`, `services/rag_service.py`, `workers/ingest.py`, `core/celery_app.py`, `core/aws.py` (S3), prompts versionados en `prompts/v1/`. Endpoints `POST /documents` y `DELETE /documents/{id}` pasan a 200/202.
2. **Auditoría Fase 2 cerrada** (commits `ab7f0ae` + `86d8c8b` + `11d246c`). Plan v2.0 alineado al código real.
3. **En paralelo:** recuperar backlog Excel del PO para completar §10 y §6.2 (columna HU).
