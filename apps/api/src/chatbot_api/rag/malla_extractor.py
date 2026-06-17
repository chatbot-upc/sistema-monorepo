"""Extracción de mallas a un ESQUEMA (RAG estructurado, format-agnostic).

El texto de las mallas se extrae del PDF en layouts impredecibles (una fila por
línea, un dato por línea, o una tabla plana con columna de ciclo). Parsear "según
el formato" se rompe con cada layout nuevo. En vez de eso, una sola pasada por
documento con un LLM + salida estructurada lee CUALQUIER layout y devuelve filas
canónicas `{ciclo, código, nombre, créditos, requisitos}`. Con esas filas se
arman chunks limpios por ciclo (`build_malla_chunks`).

Una llamada por documento (no por ciclo). Modelo configurable
(`OPENAI_NORMALIZER_MODEL`, default gpt-5-mini) con `reasoning_effort` bajo para
no disparar costo/latencia en razonadores.
"""

import re
from collections import defaultdict
from typing import Any

import structlog
from langchain_core.documents import Document as LCDocument
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from chatbot_api.core.settings import get_settings

log = structlog.get_logger()

# Una malla tiene MUCHOS códigos de curso (2-3 letras + números). Reglamentos,
# calendarios o becas no. Sirve para no gastar una llamada LLM en no-mallas.
_CODE_RE = re.compile(r"\b[A-Z]{2,3}\d{2,4}\b")
_MIN_CODES = 8


class CourseRow(BaseModel):
    """Un curso de la malla, ya separado de sus requisitos."""

    ciclo: int = Field(description="Número de ciclo al que pertenece el curso.")
    codigo: str = Field(
        default="", description="Código del curso (p. ej. PS498); vacío si no tiene."
    )
    nombre: str = Field(description="Nombre del curso.")
    creditos: float = Field(description="Número de CRÉDITOS del curso (no las horas).")
    requisitos: list[str] = Field(
        default_factory=list,
        description=(
            "Requisitos del curso: otros cursos 'código nombre' o condiciones como "
            "'61 créditos aprobados'. Vacío si no tiene requisitos."
        ),
    )


class MallaExtraction(BaseModel):
    """Resultado de extraer una malla completa."""

    is_malla: bool = Field(description="True solo si el documento es una malla curricular.")
    cursos: list[CourseRow] = Field(default_factory=list)


_SYSTEM = """Eres un extractor de mallas curriculares de la UPC. Te doy el texto de una malla
extraído de un PDF, en CUALQUIER layout: agrupada por encabezados "CICLO N", una fila por
línea, un dato por línea (vertical), o una tabla plana con una COLUMNA de ciclo. Extrae TODOS
los cursos a la lista estructurada, sin inventar, duplicar ni omitir.

REGLA CLAVE — el ÁREA es el separador de cada fila de curso:
- Antes del área ("Carrera", "General" o "Electivo") está EL CURSO: su código, nombre y
  créditos.
- Después del área están los REQUISITOS de ESE curso: otros cursos "código nombre" o
  condiciones como "61 créditos aprobados".
- Un código que aparece como requisito NUNCA es un curso del ciclo por sí mismo (aparecerá
  como curso en SU propio ciclo). Ej.: en "SI704 Arquitectura de Negocio ... Carrera ... SI385
  IHC y Tecnologías Móviles", el curso es SI704; SI385 es su requisito, NO un curso aparte.

CICLO de cada curso: si la malla está agrupada por "CICLO N", es ese N; si hay una columna de
ciclo, es el número de esa columna.

CRÉDITOS: el número de créditos del curso, NO las horas. La suma de créditos de un ciclo debe
cuadrar con el total que muestre la malla para ese ciclo (úsalo para validar).

REQUISITOS: cópialos tal cual. "No tiene requisitos" → lista vacía. No inventes requisitos.

Si el documento NO es una malla curricular, devuelve is_malla=false y cursos vacío."""


def _build_chat() -> ChatOpenAI:
    s = get_settings()
    kwargs: dict[str, Any] = {
        "model": s.openai_normalizer_model,
        "api_key": SecretStr(s.openai_api_key),
        "temperature": 0,
    }
    # Modelos de razonamiento (gpt-5*, o-series) son lentos/caros por defecto
    # (esfuerzo medium). Para un parseo con esquema, un esfuerzo bajo basta. Un
    # modelo NO-razonador rechazaría este parámetro, por eso es condicional.
    if s.openai_normalizer_model.startswith(("gpt-5", "o1", "o3", "o4")):
        kwargs["reasoning_effort"] = s.openai_normalizer_reasoning_effort
    return ChatOpenAI(**kwargs)


def looks_like_malla(text: str) -> bool:
    """Heurística format-agnostic: una malla tiene muchos códigos de curso."""
    return len(set(_CODE_RE.findall(text))) >= _MIN_CODES


async def extract_malla_rows(full_text: str, title: str | None = None) -> list[CourseRow]:
    """Extrae los cursos de una malla a filas estructuradas (1 llamada LLM).

    Devuelve [] si el LLM dice que no es malla o si la llamada falla (la ingesta
    cae entonces al chunking normal, nunca rompe).
    """
    chat = _build_chat()
    structured = chat.with_structured_output(MallaExtraction)
    human = f"Carrera: {title}\n\n{full_text}" if title else full_text
    try:
        result: Any = await structured.ainvoke(
            [SystemMessage(content=_SYSTEM), HumanMessage(content=human)]
        )
    except Exception:
        log.warning("malla_extract_failed", title=title, chars=len(full_text))
        return []

    if isinstance(result, MallaExtraction):
        ext = result
    elif isinstance(result, dict):
        ext = MallaExtraction.model_validate(result)
    else:
        return []
    return ext.cursos if ext.is_malla else []


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def build_malla_chunks(
    rows: list[CourseRow], title: str | None = None
) -> list[LCDocument]:
    """Arma un chunk limpio por ciclo a partir de las filas extraídas."""
    by_cycle: dict[int, list[CourseRow]] = defaultdict(list)
    for r in rows:
        by_cycle[r.ciclo].append(r)

    base = f"{title} — " if title else ""
    chunks: list[LCDocument] = []
    for ciclo in sorted(by_cycle):
        cursos = by_cycle[ciclo]
        total = sum(c.creditos for c in cursos)
        lines = [f"{base}Ciclo {ciclo} ({_fmt(total)} créditos)"]
        for c in cursos:
            code = f"{c.codigo} " if c.codigo else ""
            reqs = "; ".join(c.requisitos) if c.requisitos else "ninguno"
            lines.append(
                f"- {code}{c.nombre} — {_fmt(c.creditos)} créditos — Requisitos: {reqs}"
            )
        chunks.append(
            LCDocument(
                page_content="\n".join(lines),
                metadata={"section": "malla", "ciclo": ciclo, "normalized": True},
            )
        )
    return chunks
