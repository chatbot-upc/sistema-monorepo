"""RAG agent service. Agent built fresh per call.

A cached LangChain agent holds a `ChatOpenAI` whose internal httpx client gets
tied to whatever event loop initialised it. Celery workers run each task in
their own `asyncio.run()` loop, so a process-wide agent crashes from the
second task on with "Event loop is closed". We trade ~50-100 ms of agent
construction per call for correctness — negligible vs. the multi-second RAG
round-trips.
"""

from pathlib import Path
from typing import Any

import structlog
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.settings import get_settings
from chatbot_api.rag.tools import (
    escalate_to_human,
    list_programs,
    make_search_knowledge_base,
    reply_to_message,
)
from chatbot_api.repositories.prompt_version import prompt_version_repository

log = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "v1"
_PROMPT_NAME = "agent_system"

# Tier-2 fallback: contenido del archivo. Inmutable, cache de proceso seguro.
_static_prompt: str | None = None

# Tier-1: versión activa de la DB, cacheada por proceso e invalidada vía un
# generation counter en Redis (mismo patrón que el índice SBERT de SW-16). La
# API hace INCR tras activar/editar; el worker lo detecta y recarga sin reiniciar.
_active_prompt: str | None = None
_active_gen: int | None = None
_GEN_KEY = "chatbot:prompt_version_gen"


def _get_static_prompt() -> str:
    global _static_prompt
    if _static_prompt is None:
        _static_prompt = (_PROMPTS_DIR / "agent_system.md").read_text(
            encoding="utf-8"
        )
    return _static_prompt


async def _current_gen() -> int | None:
    """Lee la generación actual. None si Redis falla → caller conserva su cache."""
    settings = get_settings()
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url)
        try:
            raw = await client.get(_GEN_KEY)
        finally:
            await client.aclose()
        return int(raw) if raw is not None else 0
    except Exception:
        log.exception("prompt_version_gen_read_failed")
        return None


async def bump_prompt_generation() -> None:
    """Invalida el prompt cacheado en todos los procesos. API la llama tras write."""
    settings = get_settings()
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url)
        try:
            await client.incr(_GEN_KEY)
        finally:
            await client.aclose()
    except Exception:
        log.exception("prompt_version_gen_bump_failed")


async def _get_system_prompt(db: AsyncSession | None) -> str:
    """Versión activa del prompt.

    - `db is None` (tests / sin sesión): usa el archivo estático.
    - con `db`: cache-aside sobre la versión activa de la DB, invalidada por el
      generation counter en Redis. Si no hay activa o Redis falla, cae al archivo.
    """
    if db is None:
        return _get_static_prompt()
    gen = await _current_gen()
    global _active_prompt, _active_gen
    if _active_prompt is None or (gen is not None and gen != _active_gen):
        row = await prompt_version_repository.get_active(db, _PROMPT_NAME)
        _active_prompt = row.content if row else _get_static_prompt()
        _active_gen = gen
    return _active_prompt


def _get_agent(system_prompt: str, program: str | None = None) -> Any:
    """Builds a fresh agent per call (see module docstring).

    `program`: scope de carrera del alumno → la tool de búsqueda solo trae la
    malla de esa carrera + docs generales (fix SW-46). None = búsqueda global.
    """
    settings = get_settings()
    chat = ChatOpenAI(
        model=settings.openai_model,
        api_key=SecretStr(settings.openai_api_key),
    )
    return create_agent(
        model=chat,
        tools=[
            escalate_to_human,
            reply_to_message,
            list_programs,
            make_search_knowledge_base(program),
        ],
        system_prompt=system_prompt,
    )


async def answer(
    *,
    user_text: str,
    correlation_id: str,
    history: list[dict[str, str]] | None = None,
    db: AsyncSession | None = None,
    profile_context: str | None = None,
    program: str | None = None,
) -> dict[str, Any]:
    """Invoca el agente con el mensaje del usuario + historial reciente.

    `history` is a list of {"role": "user"|"assistant", "content": str} entries
    chronologically ordered (oldest first). It is prepended to the current user
    message so the agent has multi-turn context (SW-18/SW-25).

    Returns:
        {
            "text": str,           # respuesta final al usuario
            "tool_calls": list,    # herramientas invocadas (search_kb, escalate)
            "input_tokens": int|None,
            "output_tokens": int|None,
        }
    """
    messages: list[dict[str, str]] = list(history or [])
    messages.append({"role": "user", "content": user_text})

    system_prompt = await _get_system_prompt(db)
    if profile_context:
        system_prompt = f"{system_prompt}\n\n{profile_context}"
    try:
        result = await _get_agent(system_prompt, program).ainvoke(
            {"messages": messages},
            config={
                "recursion_limit": 12,
                "metadata": {"correlation_id": correlation_id},
            },
        )
    except GraphRecursionError:
        # El agente se atascó en un bucle de búsquedas (p. ej. el dato no está en
        # el KB). En vez de reventar la task y dejar al alumno sin respuesta,
        # devolvemos un fallback de cortesía. Lo marcamos para escalar a humano.
        log.warning("rag_recursion_limit_exhausted", correlation_id=correlation_id)
        return {
            "text": (
                "Disculpa, no logré encontrar esa información en este momento. "
                "Voy a derivarte con un asesor para que te ayude mejor. 🙏"
            ),
            "tool_calls": [
                {
                    "name": "escalate_to_human",
                    "args": {"reason": "rag_recursion_limit"},
                }
            ],
            "input_tokens": None,
            "output_tokens": None,
        }

    last = result["messages"][-1]
    tool_calls: list[dict[str, Any]] = []
    input_tokens = 0
    output_tokens = 0
    for msg in result["messages"]:
        for tc in getattr(msg, "tool_calls", None) or []:
            tool_calls.append({"name": tc.get("name"), "args": tc.get("args")})
        # Sum usage_metadata across every AIMessage. With tool calls the agent
        # may invoke the LLM 2-4 times per turn — each AIMessage carries its
        # own input/output counts. Pre-LangChain 0.3 wrappers occasionally
        # missed this dict, so we fall back to response_metadata.token_usage.
        usage = getattr(msg, "usage_metadata", None) or {}
        input_tokens += int(usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("output_tokens") or 0)
        if not usage:
            meta = getattr(msg, "response_metadata", None) or {}
            token_usage = meta.get("token_usage") or {}
            input_tokens += int(token_usage.get("prompt_tokens") or 0)
            output_tokens += int(token_usage.get("completion_tokens") or 0)

    return {
        "text": getattr(last, "content", str(last)),
        "tool_calls": tool_calls,
        "input_tokens": input_tokens or None,
        "output_tokens": output_tokens or None,
    }
