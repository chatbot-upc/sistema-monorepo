"""Intent classifier — SBERT primary, LLM fallback.

Loads `Intent.active=True` rows once (lazy) and embeds each example phrase via SBERT.
At classify-time we encode the student message, score it against every example, and
take the max cosine sim per intent.

If the top score is below `settings.intent_sbert_threshold` (default 0.55) we fall
back to an LLM call with `prompts/v1/intent_classifier.md`. The LLM returns a single
intent name which we look up in the cached intents table.

Thesis metric: every call returns both the SBERT score and a `used_fallback` flag,
so we can log SBERT vs LLM accuracy directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import structlog
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.settings import get_settings
from chatbot_api.repositories.intent import intent_repository
from chatbot_api.services import sbert_service

log = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "v1"


class _IntentIndex:
    """Cached embeddings of every example, with a back-reference to its intent."""

    def __init__(
        self,
        intent_id_by_name: dict[str, int],
        example_intent_ids: list[int],
        example_matrix: np.ndarray,
    ) -> None:
        self.intent_id_by_name = intent_id_by_name
        self.example_intent_ids = example_intent_ids
        self.example_matrix = example_matrix  # (n_examples, dim)


_index: _IntentIndex | None = None


async def _build_index(db: AsyncSession) -> _IntentIndex:
    intents = await intent_repository.list_filtered(db, active=True, limit=200)
    intent_id_by_name: dict[str, int] = {}
    examples: list[str] = []
    example_intent_ids: list[int] = []
    for intent in intents:
        intent_id_by_name[intent.name] = intent.id
        for example in intent.examples or []:
            examples.append(str(example))
            example_intent_ids.append(intent.id)
    if not examples:
        log.warning("intent_classifier_no_examples")
        return _IntentIndex(intent_id_by_name, [], np.zeros((0, 384), dtype=np.float32))
    matrix = sbert_service.encode(examples)
    log.info(
        "intent_classifier_index_built",
        intents=len(intents),
        examples=len(examples),
    )
    return _IntentIndex(intent_id_by_name, example_intent_ids, matrix)


async def _get_index(db: AsyncSession) -> _IntentIndex:
    global _index
    if _index is None:
        _index = await _build_index(db)
    return _index


def reset_index() -> None:
    """Test/admin hook — force re-build on next classify (after intent CRUD)."""
    global _index
    _index = None


def _get_llm() -> ChatOpenAI:
    """Builds a fresh LLM per call. A cached ChatOpenAI holds an internal httpx
    client tied to the first event loop, so workers using `asyncio.run()` per
    task would crash from the second call onwards with "Event loop is closed".
    """
    s = get_settings()
    return ChatOpenAI(
        model=s.openai_model,
        api_key=SecretStr(s.openai_api_key),
        temperature=0,
    )


def _sbert_classify(
    text: str, index: _IntentIndex
) -> tuple[int | None, str | None, float]:
    """Return (intent_id, intent_name, confidence)."""
    if index.example_matrix.shape[0] == 0:
        return None, None, 0.0
    query = sbert_service.encode([text])[0]
    scores = sbert_service.cosine_similarity_matrix(query, index.example_matrix)
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    intent_id = index.example_intent_ids[best_idx]
    intent_name = next(
        (n for n, iid in index.intent_id_by_name.items() if iid == intent_id), None
    )
    return intent_id, intent_name, best_score


async def _llm_classify(text: str, index: _IntentIndex) -> tuple[int | None, str | None]:
    """Returns (intent_id, intent_name) or (None, None) if name not in catalog."""
    system_prompt = (_PROMPTS_DIR / "intent_classifier.md").read_text(encoding="utf-8")
    response = await _get_llm().ainvoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
    )
    raw = str(getattr(response, "content", "")).strip().lower()
    # Strip common decoration the LLM might add.
    raw = raw.strip("`'\"").splitlines()[0].strip().strip("`'\"") if raw else ""
    intent_id = index.intent_id_by_name.get(raw)
    if intent_id is None:
        return None, None
    return intent_id, raw


async def classify(*, db: AsyncSession, text: str) -> dict[str, Any]:
    """Classify a student message.

    Returns:
        {
            "intent_id": int | None,
            "intent_name": str | None,
            "confidence": float,        # SBERT cosine sim (or 1.0 on LLM fallback)
            "used_fallback": bool,
            "sbert_intent_name": str | None,  # SBERT pick before fallback (for tesis logging)
            "sbert_confidence": float,
        }
    """
    settings = get_settings()
    index = await _get_index(db)

    sbert_id, sbert_name, sbert_score = _sbert_classify(text, index)
    if sbert_id is not None and sbert_score >= settings.intent_sbert_threshold:
        return {
            "intent_id": sbert_id,
            "intent_name": sbert_name,
            "confidence": sbert_score,
            "used_fallback": False,
            "sbert_intent_name": sbert_name,
            "sbert_confidence": sbert_score,
        }

    llm_id, llm_name = await _llm_classify(text, index)
    return {
        "intent_id": llm_id,
        "intent_name": llm_name,
        "confidence": sbert_score if llm_id is None else 1.0,
        "used_fallback": True,
        "sbert_intent_name": sbert_name,
        "sbert_confidence": sbert_score,
    }
