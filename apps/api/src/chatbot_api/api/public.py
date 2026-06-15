"""Rutas públicas (sin auth) servidas en la raíz, no bajo /api/v1.

`GET /docs/{id}/{slug}.pdf` — link permanente y legible a un PDF de la base de
conocimiento. Es un proxy de lectura al S3 PRIVADO: el bucket nunca se expone, el
backend descarga el objeto y lo devuelve. El `id` es la llave real; el `slug` es
cosmético (para que la URL se lea bonita) y se ignora.

Lo usa el agente: al citar una fuente en su respuesta comparte esta URL.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.db import get_session
from chatbot_api.core.text import slugify
from chatbot_api.services import document_service

router = APIRouter(tags=["public"])


@router.get("/docs/{document_id}/{slug}.pdf")
async def get_public_pdf(
    document_id: int,
    slug: str,  # cosmético: parte legible de la URL, no se usa para resolver
    db: AsyncSession = Depends(get_session),
) -> Response:
    content, title = await document_service.get_public_file(db, document_id)
    filename = f"{slugify(title)}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            # Permanente e inmutable: el contenido de un id no cambia.
            "Cache-Control": "public, max-age=31536000, immutable",
        },
    )
