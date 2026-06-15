"""Utilidades de texto puras (sin DB ni I/O)."""

from __future__ import annotations

import re
import unicodedata

from .settings import get_settings

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Convierte un texto en slug URL-safe.

    "INGENIERIA DE SISTEMAS DE INFORMACIÓN" -> "ingenieria-de-sistemas-de-informacion"
    Quita acentos/ñ (NFKD -> ASCII), pasa a minúsculas y colapsa todo lo que no
    sea [a-z0-9] en guiones. Devuelve "doc" si no queda nada utilizable.
    """
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_STRIP.sub("-", ascii_only.lower()).strip("-")
    return slug or "doc"


def public_doc_url(document_id: int, title: str) -> str | None:
    """Link público y permanente a un PDF: <base>/docs/<id>/<slug>.pdf.

    El `id` es la llave real (lo que resuelve el endpoint); el slug es cosmético.
    Devuelve None si no hay `public_base_url` configurado (p. ej. en local) → el
    agente entonces cita solo el título, sin link.
    """
    base = get_settings().public_base_url.rstrip("/")
    if not base:
        return None
    return f"{base}/docs/{document_id}/{slugify(title)}.pdf"
