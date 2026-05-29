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

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from chatbot_api.core.settings import get_settings
from chatbot_api.rag.tools import escalate_to_human, search_knowledge_base

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "v1"
_system_prompt: str | None = None  # immutable text cache; safe to keep


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = (_PROMPTS_DIR / "agent_system.md").read_text(encoding="utf-8")
    return _system_prompt


def _get_agent() -> Any:
    """Builds a fresh agent per call (see module docstring)."""
    settings = get_settings()
    chat = ChatOpenAI(
        model=settings.openai_model,
        api_key=SecretStr(settings.openai_api_key),
    )
    return create_agent(
        model=chat,
        tools=[escalate_to_human, search_knowledge_base],
        system_prompt=_get_system_prompt(),
    )


async def answer(
    *,
    user_text: str,
    correlation_id: str,
    history: list[dict[str, str]] | None = None,
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

    result = await _get_agent().ainvoke(
        {"messages": messages},
        config={
            "recursion_limit": 10,
            "metadata": {"correlation_id": correlation_id},
        },
    )

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
