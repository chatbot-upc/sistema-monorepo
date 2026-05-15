"""LangChain tools que invoca el agente."""

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings

from .retriever import retrieve


@tool
async def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """Busca info oficial UPC en la base de conocimiento (PDFs y HTML scrapeados).

    Usa esta tool ANTES de responder cualquier pregunta sobre UPC: matrícula,
    fechas, costos, becas, reglamentos, mallas, calendarios.

    Args:
        query: la consulta del usuario o keywords concretas.
        top_k: cuántos chunks devolver (default 5).

    Returns:
        Texto con fragmentos relevantes, cada uno con score y doc_id como cita.
    """
    # Fresh engine per call: the agent runs inside asyncio.run() in Celery workers,
    # so a process-wide cached engine would end up tied to a dead event loop on the
    # second task. Spinning up a transient engine sidesteps the "different loop"
    # RuntimeError at the cost of ~10ms per call.
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            results = await retrieve(db, query, k=top_k)
    finally:
        await engine.dispose()
    if not results:
        return "no_results"
    return "\n\n---\n\n".join(
        f"[score={1 - d:.3f}] [doc_id={c.document_id}] {c.chunk_text}"
        for c, d in results
    )


@tool
def escalate_to_human(reason: str) -> str:
    """Marca la conversación para takeover humano. Usa esta tool cuando:
    - El usuario lo pide explícitamente.
    - No tienes información suficiente tras buscar 2+ veces.
    - Tema fuera de alcance UPC.

    Args:
        reason: razón concreta del escalation (1-2 frases).

    Returns:
        Marca de escalation. Fase 4 conecta esto a conversation.status='takeover'.
    """
    return f"escalation_requested:{reason}"
