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
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from chatbot_api.core.settings import get_settings

log = structlog.get_logger()

# Un chunk es "de ciclo" si menciona "CICLO N". El preámbulo (créditos generales,
# requisito de inglés…) no lo es y se deja crudo.
_CYCLE_HINT = re.compile(r"(?i)\bCICLO\s+\d+\b")

_SYSTEM = """Eres un normalizador de mallas curriculares de la UPC. Recibes el texto CRUDO de
UN ciclo de una malla, extraído de un PDF. El layout es impredecible: puede venir con las
columnas de cada curso en una sola línea (horizontal), o con un dato por línea (vertical).
Tu trabajo es reescribirlo limpio y uniforme, SIN inventar, omitir ni duplicar nada.

Estructura de una fila de curso (de izquierda a derecha): CÓDIGO (2-3 letras + números, p.
ej. DM290, CM36) · NOMBRE del curso · números de HORAS · número de CRÉDITOS · ÁREA (la
palabra "Carrera", "General" o "Electivo") · a veces más números · al final los REQUISITOS.

LA REGLA MÁS IMPORTANTE — el ÁREA es el separador:
- Todo lo que está ANTES del área (Carrera/General/Electivo) es EL CURSO: su código,
  nombre, horas y créditos.
- Todo lo que está DESPUÉS del área son los REQUISITOS de ESE curso: otros cursos con
  formato "código nombre" (separados por ';') o condiciones como "120 Créditos cumplidos".
- Los códigos que aparecen DESPUÉS del área son REQUISITOS, NUNCA cursos nuevos del ciclo,
  AUNQUE parezcan cursos (mismo formato código+nombre, p. ej. "SI385 IHC y Tecnologías
  Móviles"). Jamás los conviertas en una fila de curso aparte.

Cómo separar las filas:
- Formato horizontal (una fila por línea): CADA LÍNEA no vacía es EXACTAMENTE UN curso. El
  curso es el código+nombre al inicio de esa línea; sus requisitos son lo que esté después
  del área en ESA MISMA línea.
- Formato vertical (un dato por línea): una fila nueva empieza cuando aparece un CÓDIGO solo
  en su línea; acumula las líneas siguientes (nombre, números, área, requisitos) hasta el
  próximo código que abre línea.

Devuelve EXACTAMENTE este formato y nada más (la primera línea lleva la CARRERA —que
aparece al inicio del texto— y el ciclo):
<Carrera> — Ciclo <N> (<total> créditos)
- <CÓDIGO> <Nombre> — <créditos> créditos — Requisitos: <req1>; <req2>
- Electivo — <créditos> créditos — Requisitos: ninguno

Reglas finales:
- CRÉDITOS: el número de créditos del curso (NO las horas). La SUMA de los créditos de los
  cursos debe coincidir con el total del ciclo (el número junto a "CICLO N"); úsalo para
  validar que no agregaste ni perdiste cursos ni elegiste mal la columna de créditos.
- REQUISITOS: cópialos tal cual del final de la fila. Si no hay nada después del área,
  escribe "Requisitos: ninguno". No inventes requisitos.
- Responde solo con el texto normalizado, sin explicaciones ni bloques de código."""

# Few-shot con el caso exacto que falló: requisitos (SI385, SI400) idénticos en formato a
# cursos. Le enseña que lo que va tras el área es requisito, y que # de cursos = # de líneas.
_EXAMPLE_IN = "\n".join(
    [
        "Ingeniería de Sistemas de Información",
        "5",
        "▸▸ CICLO 5  21",
        "MA642 Estadística Aplicada I 64 4 4 3.0 1.0 4 General 1 MA262 Cálculo I",
        "SI704 Arquitectura de Negocio 64 4 4 4 Carrera 2 2 SI385 IHC y Tecnologias Moviles",
        "MA263 Cálculo II 96 6 6 4.0 2.0 6 Carrera 2 MA262 Cálculo I",
        "SI393 Fundamentos de Sistemas de Información 32 32 3 3 2.0 1.0 3 Carrera 2 1 "
        "SI400 Diseño De Base De Datos",
        "Electivo 64 4 4 4 Electivo",
    ]
)

_EXAMPLE_OUT = "\n".join(
    [
        "Ingeniería de Sistemas de Información — Ciclo 5 (21 créditos)",
        "- MA642 Estadística Aplicada I — 4 créditos — Requisitos: MA262 Cálculo I",
        "- SI704 Arquitectura de Negocio — 4 créditos — Requisitos: "
        "SI385 IHC y Tecnologías Móviles",
        "- MA263 Cálculo II — 6 créditos — Requisitos: MA262 Cálculo I",
        "- SI393 Fundamentos de Sistemas de Información — 3 créditos — Requisitos: "
        "SI400 Diseño De Base De Datos",
        "- Electivo — 4 créditos — Requisitos: ninguno",
    ]
)


def _build_chat() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.openai_normalizer_model,
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
                [
                    SystemMessage(content=_SYSTEM),
                    HumanMessage(content=_EXAMPLE_IN),
                    AIMessage(content=_EXAMPLE_OUT),
                    HumanMessage(content=c.page_content),
                ]
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
