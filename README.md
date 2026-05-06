# Chatbot UPC

Sistema chatbot RAG para atención al estudiante en proceso de matrícula universitaria.
WhatsApp (Meta Cloud API) + RAG (LangChain + OpenAI) + CRM admin web.

## Estructura

```
chatbot-upc/
├── apps/
│   ├── web/        Next.js admin (CRM)
│   └── api/        FastAPI + Celery worker (webhook WhatsApp + RAG)
├── packages/       Tipos compartidos (futuro)
├── design/         Mockups Pencil + previews HTML
├── docs/           Documentación técnica (PLAN.md, ADRs)
├── infra/          IaC (futuro)
├── scrapping/      Scraper UPC one-shot (externo, no runtime)
└── docker-compose.yml   Postgres+pgvector + Redis local
```

Ver [`docs/PLAN.md`](docs/PLAN.md) para el plan completo de implementación.

## Setup inicial

### Prerrequisitos

- Python 3.12+
- Node.js 20+ y pnpm 10+
- Docker Desktop (para Postgres y Redis locales)
- [`uv`](https://github.com/astral-sh/uv) para Python (`brew install uv`)

### 1. Variables de entorno

```bash
cp .env.example .env
# editar .env con tus claves (OpenAI, Meta, AWS)
```

### 2. Levantar infra local

```bash
docker compose up -d
```

Esto levanta Postgres 16 con pgvector en `localhost:5432` y Redis 7 en `localhost:6379`.

### 3. Frontend (`apps/web`)

```bash
pnpm install
pnpm dev:web
# http://localhost:3000
```

### 4. Backend API (`apps/api`)

```bash
cd apps/api
uv sync
uv run uvicorn chatbot_api.main:app --reload --port 8000
# http://localhost:8000/docs
```

### 5. Pre-commit hooks (opcional pero recomendado)

```bash
uv tool install pre-commit
pre-commit install
```

## Comandos útiles

```bash
# Tests del API
cd apps/api && uv run pytest

# Lint del API
cd apps/api && uv run ruff check . && uv run mypy

# Lint del frontend
pnpm lint:web

# Build del frontend
pnpm build:web
```

## Documentación

- [Plan completo](docs/PLAN.md) — fases, modelo de datos, decisiones operativas
- [Diagrama físico](DiagramaFisicoV1.png) — arquitectura AWS objetivo
- Mockup admin: `design/chatbot-admin.pen`

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + LangChain + Celery
- **Frontend:** Next.js 16 + React 19 + Tailwind v4 + shadcn/ui
- **DB:** PostgreSQL 16 + pgvector
- **LLM:** OpenAI gpt-4o-mini + text-embedding-3-small
- **Infra:** AWS (Free Tier durante piloto)
