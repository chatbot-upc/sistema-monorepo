"""LangChain tools que invoca el agente."""

from typing import Any

import structlog
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.core.text import public_doc_url

from .retriever import retrieve

log = structlog.get_logger()


def make_search_knowledge_base(program: str | None = None) -> Any:
    """Construye la tool de búsqueda scopeada a la carrera del alumno (SW-46).

    El agente se arma fresco por request (ver rag_service), así que cada
    conversación recibe una tool que ya lleva el `program` del estudiante. Con
    `program=None` la búsqueda es global (alumno sin perfil / carrera sin malla).
    """

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
        # Fresh engine per call: the agent runs inside asyncio.run() in Celery
        # workers, so a process-wide cached engine would end up tied to a dead
        # event loop on the second task. Spinning up a transient engine sidesteps
        # the "different loop" RuntimeError at the cost of ~10ms per call.
        settings = get_settings()
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as db:
                results = await retrieve(db, query, k=top_k, program=program)
        finally:
            await engine.dispose()

        # Piso de relevancia: descarta chunks débiles. Si NINGUNO supera el
        # umbral, devolvemos "no_results" para que el agente derive en vez de
        # responder con basura (el KB puede no tener doc para ese tema).
        min_score = settings.rag_min_score
        kept = [(c, d) for c, d in results if (1 - d) >= min_score]
        top_score = max((1 - d for _, d in results), default=0.0)
        log.info(
            "rag_search",
            query=query,
            top_score=round(top_score, 3),
            min_score=min_score,
            kept=len(kept),
            total=len(results),
        )
        if not kept:
            return "no_results"

        # Citamos por NOMBRE del documento (no doc_id): es lo que el agente
        # mostrará al alumno → "(Fuente: <nombre>)" en vez de un id técnico.
        # Si hay dominio público configurado, adjuntamos el link permanente al
        # PDF (proxy al S3 privado) para que el agente lo comparta en su respuesta.
        def _fuente(doc: Any) -> str:
            url = public_doc_url(doc.id, doc.title)
            return f"{doc.title} — {url}" if url else doc.title

        return "\n\n---\n\n".join(
            f"[score={1 - d:.3f}] [fuente: {_fuente(c.document)}] {c.chunk_text}"
            for c, d in kept
        )

    return search_knowledge_base


# Instancia global sin scope: la usan tests u otros importadores que no tienen
# perfil de alumno. El flujo real arma la tool por request con make_*().
search_knowledge_base = make_search_knowledge_base(None)


@tool
def reply_to_message(message_number: int) -> str:
    """Cita (responde a) un mensaje específico de los que el estudiante acaba de enviar.

    Úsala cuando el estudiante mandó VARIOS mensajes seguidos y uno de ellos lleva
    la consulta o intención real — cita ESE para que quede claro a cuál respondes.
    Elige el mensaje con la pregunta concreta, NO un saludo o relleno ("hola",
    "buenas", "qué tal"). Si todos son saludos o tu respuesta cubre todo por igual,
    NO la uses.

    Args:
        message_number: el número del mensaje a citar, según la lista numerada que
            recibiste (1 = el primero que envió, y así sucesivamente).

    Returns:
        Marca interna; el sistema traduce el número al mensaje real.
    """
    return f"reply_to_message:{message_number}"


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
