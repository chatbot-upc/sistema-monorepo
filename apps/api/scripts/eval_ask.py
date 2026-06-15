"""Eval CLI: "hacerse pasar" por un número y correr el pipeline RAG real.

Replica las entradas del worker (`_run_reply`): carga el perfil del estudiante
por `phone_e164` (`profile_context` + `program`) e invoca `rag_service.answer`
con `history=None` (conversación limpia). NO pasa por WhatsApp/Meta/Celery, NO
aplica debounce ni clasificador de intención, y NO escribe en la BD — es la
misma respuesta que daría el bot por WhatsApp, capturada para calificar los
escenarios de evaluación de la tesis (S1 simple, S2 complejo).

Precondiciones: DB levantada, perfil sembrado, documentos indexados y
OPENAI_API_KEY en el entorno.

    uv run python scripts/eval_ask.py --phone +51904890457 --text "¿...?"
    uv run python scripts/eval_ask.py --phone +51904890457 --batch
"""

from __future__ import annotations

import argparse
import asyncio
import time
import uuid

from chatbot_api.core.db import get_session_factory
from chatbot_api.services import rag_service, student_profile_service

# Batería por defecto: consultas oficiales (S1/S2) + variantes de robustez.
# Pensada para el alumno de prueba de Pregrado, Ing. de Sistemas de Información.
DEFAULT_QUESTIONS: list[tuple[str, str]] = [
    (
        "S1",
        "¿Cuál es la información sobre matrícula 2026-1 y el cronograma de "
        "pagos para el ciclo 2026-1?",
    ),
    ("S1", "¿Cuándo me toca matricularme este ciclo?"),
    ("S1", "¿Hasta cuándo puedo pagar la primera cuota del 2026-1?"),
    ("S1", "¿Cuándo empiezan las clases en el 2026-1?"),
    ("S1", "¿Cuándo es la matrícula del 2026-2?"),
    (
        "S2",
        "Si estoy en la carrera de Ingeniería de Sistemas de Información, "
        "¿qué cursos puedo llevar en noveno ciclo y cuáles son sus requisitos?",
    ),
    ("S2", "¿Qué cursos llevo este ciclo?"),
    ("S2", "¿Qué necesito tener aprobado para llevar Taller de Proyecto I?"),
    ("S2", "¿Cuántos créditos son los cursos de noveno ciclo?"),
]

_SEP = "=" * 78


def _fmt_tool_calls(tool_calls: list[dict]) -> str:
    if not tool_calls:
        return "  (ninguna — el bot respondió sin buscar en el KB)"
    lines: list[str] = []
    for tc in tool_calls:
        name = tc.get("name")
        args = tc.get("args") or {}
        if name == "search_knowledge_base":
            q = args.get("query", "")
            lines.append(f"  · search_knowledge_base(query={q!r})")
        elif name == "escalate_to_human":
            lines.append(f"  · escalate_to_human(reason={args.get('reason')!r}) ⚠️")
        else:
            lines.append(f"  · {name}({args})")
    return "\n".join(lines)


async def _ask_one(db, *, tag: str, question: str, ctx: str | None, program: str | None) -> None:
    correlation_id = f"eval-{uuid.uuid4().hex[:12]}"
    started = time.perf_counter()
    result = await rag_service.answer(
        user_text=question,
        correlation_id=correlation_id,
        history=None,
        db=db,
        profile_context=ctx,
        program=program,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    print(_SEP)
    print(f"[{tag}] {question}")
    print(_SEP)
    print("\nRESPUESTA:\n")
    print(result.get("text") or "(respuesta vacía)")
    print("\nTOOL CALLS:")
    print(_fmt_tool_calls(result.get("tool_calls") or []))
    print(
        f"\nmeta: tokens in={result.get('input_tokens')} "
        f"out={result.get('output_tokens')} · latencia={latency_ms} ms "
        f"· correlation_id={correlation_id}"
    )
    print()


async def _run(phone: str, text: str | None, batch: bool) -> int:
    factory = get_session_factory()
    async with factory() as db:
        # Pre-flight: cargar el perfil tal como lo hace el worker.
        ctx, program = await student_profile_service.get_profile_scope(db, phone)
        if ctx is None:
            print(
                f"❌ No hay perfil para {phone}. El eval no sería válido "
                "(el RAG correría global, sin scope de carrera).\n"
                "   Siembra el perfil antes de correr (seed_student_profiles.py)."
            )
            return 1

        print(_SEP)
        print(f"PERFIL CARGADO · {phone}")
        print(_SEP)
        print(ctx)
        print(f"\nprogram (slug de scope RAG): {program!r}\n")

        if batch:
            questions = DEFAULT_QUESTIONS
        elif text:
            questions = [("--", text)]
        else:
            print("❌ Pasa --text \"...\" o --batch.")
            return 2

        for tag, question in questions:
            await _ask_one(db, tag=tag, question=question, ctx=ctx, program=program)

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Corre el pipeline RAG haciéndose pasar por un número (read-only)."
    )
    parser.add_argument("--phone", required=True, help="phone_e164, ej. +51904890457")
    parser.add_argument("--text", help="Una sola consulta a evaluar.")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Corre la batería por defecto (oficiales S1/S2 + variantes).",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.phone, args.text, args.batch)))


if __name__ == "__main__":
    main()
