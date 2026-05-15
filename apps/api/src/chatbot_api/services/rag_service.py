"""RAG agent service. Agent built lazily on first use.

Eager build at import time crashes tests that don't supply OPENAI_API_KEY (e.g.,
worker-flow tests that mock `answer`). We defer to the first `answer()` call so
imports stay cheap.
"""

from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from chatbot_api.core.settings import get_settings
from chatbot_api.rag.tools import escalate_to_human, search_knowledge_base

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "v1"

_agent: Any = None


def _get_agent() -> Any:
    global _agent
    if _agent is None:
        settings = get_settings()
        chat = ChatOpenAI(
            model=settings.openai_model,
            api_key=SecretStr(settings.openai_api_key),
        )
        system_prompt = (_PROMPTS_DIR / "agent_system.md").read_text(encoding="utf-8")
        _agent = create_agent(
            model=chat,
            tools=[escalate_to_human, search_knowledge_base],
            system_prompt=system_prompt,
        )
    return _agent


async def answer(*, user_text: str, correlation_id: str) -> dict[str, Any]:
    """Invoca el agente con el mensaje del usuario y devuelve respuesta + metadata.

    Returns:
        {
            "text": str,           # respuesta final al usuario
            "tool_calls": list,    # herramientas invocadas (search_kb, escalate)
            "input_tokens": int|None,
            "output_tokens": int|None,
        }
    """
    result = await _get_agent().ainvoke(
        {"messages": [{"role": "user", "content": user_text}]},
        config={
            "recursion_limit": 10,
            "metadata": {"correlation_id": correlation_id},
        },
    )

    last = result["messages"][-1]
    tool_calls: list[dict[str, Any]] = []
    for msg in result["messages"]:
        for tc in getattr(msg, "tool_calls", None) or []:
            tool_calls.append({"name": tc.get("name"), "args": tc.get("args")})

    usage = result.get("usage_metadata") or {}
    return {
        "text": getattr(last, "content", str(last)),
        "tool_calls": tool_calls,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
    }
