"""Bulk-ingest PDFs from scrapping/upc_documents/ con dedupe sha256.

Asegúrate de tener Postgres + Redis corriendo + worker Celery activo
(uv run celery -A chatbot_api.core.celery_app worker --loglevel=info).

Uso:
    uv run python scripts/bulk_ingest.py --category becas --limit 10
    uv run python scripts/bulk_ingest.py --all
"""

import argparse
import asyncio
import hashlib
from pathlib import Path

from sqlalchemy import select

from chatbot_api.core.db import get_session_factory
from chatbot_api.core.storage import get_storage
from chatbot_api.models import Document
from chatbot_api.models.enums import DocumentSourceType, DocumentStatus

SCRAPING_BASE = (
    Path(__file__).resolve().parent.parent.parent.parent / "scrapping" / "upc_documents"
)


async def _ingest_one(filepath: Path) -> tuple[str, int | None]:
    content = filepath.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()

    factory = get_session_factory()
    async with factory() as db:
        existing = await db.execute(select(Document).where(Document.sha256 == sha256))
        if existing.scalars().first():
            return "skipped", None

        storage_key = f"docs/{sha256}/{filepath.name}"
        await get_storage().save(storage_key, content)

        doc = Document(
            title=filepath.stem,
            source_type=DocumentSourceType.scraped,
            source_url=None,
            s3_key=storage_key,
            sha256=sha256,
            status=DocumentStatus.pending,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        from chatbot_api.workers.ingest import ingest_document

        ingest_document.delay(doc.id)
        return "queued", doc.id


async def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk ingest UPC PDFs")
    parser.add_argument(
        "--category",
        choices=["becas", "reglamentos", "matricula", "pregrado", "otros"],
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--all", action="store_true", help="Ingest todos los PDFs")
    args = parser.parse_args()

    pdfs_dir = SCRAPING_BASE / "pdfs"
    if not pdfs_dir.exists():
        print(f"Error: {pdfs_dir} no existe.")
        return

    if args.all:
        paths = list(pdfs_dir.rglob("*.pdf"))
    elif args.category:
        paths = sorted((pdfs_dir / args.category).glob("*.pdf"))[: args.limit]
    else:
        print("Pasa --category <nombre> --limit N o --all")
        return

    print(f"Ingesting {len(paths)} PDFs from {pdfs_dir}...")
    queued = 0
    skipped = 0
    for p in paths:
        try:
            status, doc_id = await _ingest_one(p)
            if status == "queued":
                queued += 1
                print(f"  queued (id={doc_id}): {p.name}")
            else:
                skipped += 1
                print(f"  skipped (dup): {p.name}")
        except Exception as exc:
            print(f"  error {p.name}: {exc}")

    print(f"\nTotal: {queued} queued, {skipped} skipped (dedupe).")
    print(
        "Verifica progreso con: docker exec chatbot-postgres "
        "psql -U chatbot -d chatbot -c "
        "'SELECT status, count(*) FROM documents GROUP BY status;'"
    )


if __name__ == "__main__":
    asyncio.run(main())
