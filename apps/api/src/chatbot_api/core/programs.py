"""Normalización de carrera/programa a un slug canónico para scopear el RAG.

La MISMA función se aplica a dos lados:
  - al título de la malla, cuando se taggea el documento (`documents.program`);
  - a la carrera del alumno (perfil), al recibir un mensaje.

Si ambos describen la misma carrera, caen al mismo slug → el filtro de
retrieval (`documents.program IS NULL OR = :program`) hace match exacto y el bot
solo busca en la malla del alumno. Si no casan, fail-open: no se filtra
(búsqueda global, como sin perfil) → nunca empeora el comportamiento actual.

El match es por IGUALDAD del slug (no por solapamiento) a propósito: comparar por
"contiene" mezclaría carreras (p. ej. "administracion" calzaría con
"administracion-marketing", "administracion-finanzas", …). Los pocos casos donde
la normalización no casa se resuelven taggeando el documento a mano en el panel.
"""

from __future__ import annotations

import re
import unicodedata

# Palabras que no identifican la carrera: grado, modalidad, conectores. Se
# descartan para que el título de la malla y la carrera del alumno converjan.
_FILLER = {
    "ING",
    "INGENIERIA",
    "PREGRADO",
    "MW",
    "FDM",
    "PRESENCIAL",
    "SEMIPRESENCIAL",
    "PROFESIONAL",
    "MALLA",
    "DE",
    "DEL",
    "LA",
    "LAS",
    "LOS",
    "Y",
    "EN",
    "EL",
    "P",
}


def canonical_program(text: str | None) -> str | None:
    """Reduce un texto de carrera/título a un slug comparable.

    Pasos: quita acentos → mayúsculas → todo lo no-alfanumérico a espacio →
    descarta palabras de relleno y números sueltos → une con guiones.

    Devuelve None si el texto es vacío o solo queda relleno (→ fail-open).

    >>> canonical_program("Ing. de Sistemas de Información")
    'sistemas-informacion'
    >>> canonical_program("INGENIERIA DE SISTEMAS DE INFORMACION PREGRADO MW FDM")
    'sistemas-informacion'
    >>> canonical_program("   ") is None
    True
    """
    if not text:
        return None
    ascii_text = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    cleaned = re.sub(r"[^A-Za-z0-9 ]", " ", ascii_text).upper()
    tokens = [
        w for w in cleaned.split() if w not in _FILLER and not w.isdigit()
    ]
    return "-".join(tokens).lower() or None
