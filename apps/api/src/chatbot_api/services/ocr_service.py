"""OCR vía OpenAI Vision (gpt-4o-mini) — SW-22.

Usado por el loader de PDFs cuando una página no tiene texto digital extraíble.
Cliente OpenAI fresco por call: los workers Celery hacen `asyncio.run()` por task,
así que un cliente cacheado tendría su pool atado a un event loop muerto en la
segunda invocación (misma lección que `whatsapp_service` y `embeddings`).
"""

from __future__ import annotations

import base64

import structlog
from openai import AsyncOpenAI

from chatbot_api.core.settings import get_settings

log = structlog.get_logger()

_OCR_PROMPT = (
    "Extract all visible text from this image verbatim. "
    "Preserve structure: render tables as markdown, lists as bullets, "
    "and keep line breaks where meaningful. "
    "Output only the extracted text, no commentary, no preamble."
)


async def extract_text_from_image_bytes(png_bytes: bytes) -> str:
    """OCR de un PNG via OpenAI Vision. Devuelve texto plano (markdown si hay tablas).

    Si no hay API key configurada (dev/test sin OpenAI), devuelve "" y loguea
    para que el caller sepa que el OCR no se ejecutó.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        log.warning("ocr_dev_bypass_no_api_key")
        return ""

    b64 = base64.b64encode(png_bytes).decode("ascii")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        resp = await client.chat.completions.create(
            model=settings.openai_vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _OCR_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096,
        )
    finally:
        await client.close()

    text = (resp.choices[0].message.content or "").strip()
    usage = resp.usage
    log.info(
        "ocr_extracted",
        chars=len(text),
        input_tokens=usage.prompt_tokens if usage else None,
        output_tokens=usage.completion_tokens if usage else None,
        model=settings.openai_vision_model,
    )
    return text
