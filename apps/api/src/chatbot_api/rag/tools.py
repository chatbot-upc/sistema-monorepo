"""LangChain tools que invoca el agente."""

from typing import Any

import structlog
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.programs import canonical_program
from chatbot_api.core.settings import get_settings
from chatbot_api.core.text import public_doc_url
from chatbot_api.models import Document
from chatbot_api.models.enums import DocumentStatus

from .retriever import retrieve

log = structlog.get_logger()


async def _resolve_program(db: Any, scope: str) -> str | None:
    """Resuelve un scope de carrera 'corto'/informal a la carrera oficial ÚNICA
    que lo contiene.

    Ej: "marketing" → "administracion-marketing"; "sistemas" → "sistemas-informacion".
    Si hay 0 o >1 candidatos (ambiguo, p. ej. "administracion" calza con varias),
    devuelve None → el caller cae a búsqueda global. Compara por subconjunto de
    tokens para no mezclar carreras parecidas.
    """
    rows = (
        await db.execute(
            select(Document.program)
            .where(
                Document.status == DocumentStatus.indexed,
                Document.program.is_not(None),
            )
            .distinct()
        )
    ).scalars().all()
    toks = set(scope.split("-"))
    cands = sorted({p for p in rows if p and toks.issubset(set(p.split("-")))})
    return cands[0] if len(cands) == 1 else None


def make_search_knowledge_base(program: str | None = None) -> Any:
    """Construye la tool de búsqueda scopeada a la carrera del alumno (SW-46).

    El agente se arma fresco por request (ver rag_service), así que cada
    conversación recibe una tool que ya lleva el `program` del estudiante. Con
    `program=None` la búsqueda es global (alumno sin perfil / carrera sin malla).
    """

    @tool
    async def search_knowledge_base(
        query: str, career: str | None = None, top_k: int = 5
    ) -> str:
        """Busca info oficial UPC en la base de conocimiento (PDFs y HTML scrapeados).

        Usa esta tool ANTES de responder cualquier pregunta sobre UPC: matrícula,
        fechas, costos, becas, reglamentos, mallas, calendarios.

        Args:
            query: la consulta del usuario o keywords concretas. Si es sobre la
                malla/cursos, INCLUYE el nombre de la carrera en el texto.
            career: carrera del estudiante para acotar a SU malla. Pásala si la
                conoces (del perfil o de lo que dijo en el chat), idealmente la
                carrera OFICIAL (usa `list_programs` para resolver typos/variantes).
                Omítela si no la sabes → búsqueda global.
            top_k: cuántos chunks devolver (default 5).

        Returns:
            Fragmentos relevantes, cada uno con [fuente: <nombre> — <url>].
        """
        # Fresh engine per call: the agent runs inside asyncio.run() in Celery
        # workers, so a process-wide cached engine would end up tied to a dead
        # event loop on the second task. Spinning up a transient engine sidesteps
        # the "different loop" RuntimeError at the cost of ~10ms per call.
        # Scope efectivo: la carrera que pase el agente (del chat) tiene prioridad
        # sobre la del perfil (closure). canonical_program normaliza ambas al mismo
        # slug que la malla.
        scope = canonical_program(career) if career else program
        settings = get_settings()
        min_score = settings.rag_min_score
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as db:
                results = await retrieve(db, query, k=top_k, program=scope)
                kept = [(c, d) for c, d in results if (1 - d) >= min_score]
                used = scope
                # Resolución tolerante: el agente pasó una carrera corta/informal
                # que no matchea exacto (p. ej. "marketing" vs "administracion-
                # marketing"). Busca la carrera oficial ÚNICA que la contenga y
                # reintenta acotado a ESA (mejor que global, que mezcla mallas).
                if not kept and scope is not None:
                    resolved = await _resolve_program(db, scope)
                    if resolved is not None and resolved != scope:
                        results = await retrieve(db, query, k=top_k, program=resolved)
                        kept = [(c, d) for c, d in results if (1 - d) >= min_score]
                        used = resolved
                # Último recurso: global (el agente elige la malla correcta de
                # los [fuente: ...]).
                fellback = False
                if not kept and scope is not None:
                    results = await retrieve(db, query, k=top_k, program=None)
                    kept = [(c, d) for c, d in results if (1 - d) >= min_score]
                    used = None
                    fellback = True
        finally:
            await engine.dispose()

        top_score = max((1 - d for _, d in results), default=0.0)
        log.info(
            "rag_search",
            query=query,
            scope=scope,
            used=used,
            fellback=fellback,
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
async def list_programs() -> str:
    """Lista las carreras (mallas) disponibles en la base de conocimiento.

    Úsala para resolver la carrera que menciona el estudiante a la carrera
    OFICIAL, AUNQUE la escriba con errores ortográficos o nombre informal
    (p. ej. "sistmas", "ing de sistemas" → "sistemas-informacion"). Luego pasa
    esa carrera oficial como `career` a `search_knowledge_base` para acotar a la
    malla correcta.

    Returns:
        Una carrera por línea (slug oficial), o "no_programs" si no hay mallas.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            rows = (
                await db.execute(
                    select(Document.program)
                    .where(
                        Document.status == DocumentStatus.indexed,
                        Document.program.is_not(None),
                    )
                    .distinct()
                )
            ).scalars().all()
    finally:
        await engine.dispose()

    progs = sorted({p for p in rows if p})
    log.info("list_programs", count=len(progs))
    return "\n".join(progs) if progs else "no_programs"


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
