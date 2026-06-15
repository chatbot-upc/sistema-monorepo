"""Backfill de documents.program para las mallas ya indexadas (fix SW-46).

Setea el slug canónico de carrera SOLO en documentos que parecen mallas (título
con PREGRADO/FDM/MALLA), derivándolo del título con core.programs.canonical_program.
Los docs generales (fechas, becas, reglamentos) se dejan en NULL → visibles a
todas las carreras.

Idempotente y seguro: por defecto corre en DRY-RUN (solo muestra el plan). Pasá
--apply para escribir. Solo toca filas con program IS NULL (no pisa tags manuales).

    uv run python scripts/backfill_document_program.py            # dry-run
    uv run python scripts/backfill_document_program.py --apply    # escribe
"""

import argparse
import asyncio
import re

from sqlalchemy import select

from chatbot_api.core.db import get_session_factory
from chatbot_api.core.programs import canonical_program
from chatbot_api.models import Document

# Marcadores de que un documento es una malla curricular (vs doc general).
_MALLA_MARKERS = re.compile(r"PREGRADO|FDM|MALLA", re.IGNORECASE)


def _is_malla(title: str) -> bool:
    return bool(_MALLA_MARKERS.search(title or ""))


async def run(apply: bool) -> None:
    factory = get_session_factory()
    async with factory() as db:
        rows = (
            await db.execute(
                select(Document).where(Document.program.is_(None))
            )
        ).scalars().all()

        tagged = 0
        skipped_general = 0
        skipped_empty = 0
        print(f"{'APLICANDO' if apply else 'DRY-RUN'} — {len(rows)} docs sin program\n")
        for doc in rows:
            if not _is_malla(doc.title):
                skipped_general += 1
                continue
            slug = canonical_program(doc.title)
            if slug is None:
                skipped_empty += 1
                print(f"  ?  [{doc.id}] {doc.title[:55]!r} -> (sin slug, queda NULL)")
                continue
            print(f"  ✓  [{doc.id}] {doc.title[:55]!r} -> {slug}")
            if apply:
                doc.program = slug
            tagged += 1

        if apply:
            await db.commit()

        print(
            f"\nResumen: {tagged} mallas {'taggeadas' if apply else 'a taggear'} · "
            f"{skipped_general} generales (NULL) · {skipped_empty} sin slug"
        )
        if not apply:
            print("\n(dry-run — nada escrito. Corré con --apply para confirmar.)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Escribe los cambios (sin esto: dry-run).",
    )
    args = parser.parse_args()
    asyncio.run(run(args.apply))


if __name__ == "__main__":
    main()
