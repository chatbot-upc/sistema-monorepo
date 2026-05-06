# Chatbot API

FastAPI backend for Chatbot UPC.

## Setup

```bash
uv sync
cp ../../.env.example .env
uv run uvicorn chatbot_api.main:app --reload --port 8000
```

Open http://localhost:8000/docs

## Test

```bash
uv run pytest
```

## Lint

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
```
