"""Normaliza chunks de malla a filas limpias y uniformes (format-agnostic).

El texto extraído de las mallas (PDF) llega en layouts impredecibles: a veces una
fila por curso (columnas pegadas en una línea), a veces una celda por línea
(vertical). Es el MISMO formato visual, pero el extractor de PDF lo serializa
distinto según el documento. El LLM de respuesta alucina cuando recibe esa sopa.

Por eso, al ingestar, cada chunk de ciclo pasa por una pasada corta
(gpt-4o-mini, temp 0) que lo convierte a filas canónicas:

    <Carrera> — Ciclo N (T créditos)
    - <CÓDIGO> <Nombre> — <c> créditos — Requisitos: <...> | ninguno

Determinista (temp 0 + "no inventes" + el crudo presente). Si la pasada falla o
devuelve vacío, se conserva el texto crudo (nunca queda peor que antes).
"""

import re

import structlog
from langchain_core.documents import Document as LCDocument
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from chatbot_api.core.settings import get_settings

log = structlog.get_logger()

# Un chunk es "de ciclo" si menciona "CICLO N". El preámbulo (créditos generales,
# requisito de inglés…) no lo es y se deja crudo.
_CYCLE_HINT = re.compile(r"(?i)\bCICLO\s+\d+\b")

_SYSTEM = """Eres un normalizador de mallas curriculares de la UPC. Recibes el texto CRUDO de
UN ciclo de una malla, extraído de un PDF. El layout es impredecible: puede venir con las
columnas de cada curso pegadas en una sola línea, o con un dato por línea (vertical). Tu
trabajo es reescribirlo limpio y uniforme, SIN inventar ni omitir nada.

Estructura de cada fila de curso (en este orden): CÓDIGO (2-3 letras + números, p. ej.
DM290, CM36) · NOMBRE del curso · números de HORAS · número de CRÉDITOS · área (Carrera /
General / Electivo) · más números · al final, los REQUISITOS (otros cursos con formato
"código nombre" separados por ';', o condiciones como "120 Créditos cumplidos").

Devuelve EXACTAMENTE este formato y nada más:
<Carrera si aparece> — Ciclo <N> (<total> créditos)
- <CÓDIGO> <Nombre> — <créditos> créditos — Requisitos: <req1>; <req2>
- Electivo — <créditos> créditos — Requisitos: ninguno

Reglas estrictas:
- El curso del ciclo es el que EMPIEZA la fila (su código + nombre), o "Electivo". Lo que
  aparece al FINAL de la fila son REQUISITOS, NO cursos del ciclo: nunca pongas un
  requisito como si fuera un curso.
- CRÉDITOS de un curso: el número de créditos (NO las horas). La SUMA de los créditos de
  los cursos del ciclo debe coincidir con el total del ciclo (el número junto al encabezado
  "CICLO N"); úsalo para elegir bien cuál columna son los créditos.
- REQUISITOS: cópialos tal cual del final de la fila. Si la fila no termina en requisitos,
  escribe "Requisitos: ninguno". No inventes requisitos.
- NO inventes, NO agregues, NO quites cursos. Usa solo lo que está en el texto.
- Responde solo con el texto normalizado, sin explicaciones ni bloques de código."""


def _build_chat() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.openai_model,
        api_key=SecretStr(s.openai_api_key),
        temperature=0,
    )


def _content_to_str(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [p if isinstance(p, str) else str(p) for p in content]
        return "".join(parts)
    return str(content)


async def normalize_malla_chunks(chunks: list[LCDocument]) -> list[LCDocument]:
    """Reescribe los chunks de ciclo de una malla a filas limpias.

    Solo toca los chunks que parecen un ciclo (contienen "CICLO N"); el resto
    (preámbulo, docs no-malla) se devuelven igual → ningún costo para no-mallas.
    Ante error de la pasada LLM, conserva el texto crudo de ese chunk.
    """
    if not any(_CYCLE_HINT.search(c.page_content) for c in chunks):
        return chunks

    chat = _build_chat()
    out: list[LCDocument] = []
    for c in chunks:
        if _CYCLE_HINT.search(c.page_content) is None:
            out.append(c)
            continue
        try:
            resp = await chat.ainvoke(
                [SystemMessage(content=_SYSTEM), HumanMessage(content=c.page_content)]
            )
            text = _content_to_str(resp.content).strip()
            if not text:
                raise ValueError("empty normalization")
            out.append(
                LCDocument(
                    page_content=text,
                    metadata={**c.metadata, "normalized": True},
                )
            )
        except Exception:
            log.warning("malla_normalize_failed", chars=len(c.page_content))
            out.append(c)
    return out
