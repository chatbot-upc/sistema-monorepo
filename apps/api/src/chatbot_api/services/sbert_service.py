"""SBERT (sentence-transformers) wrapper.

Lazy load of `paraphrase-multilingual-MiniLM-L12-v2` (~118MB) — bilingual ES/EN
and small enough for the t3.micro target. HuggingFace caches the weights under
`~/.cache/huggingface/hub` so the first call downloads once.

Module-level `_model` reference: the SentenceTransformer is heavy to construct,
so we keep one instance per process.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import structlog

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

log = structlog.get_logger()

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        log.info("sbert_loading_model", model=MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        log.info("sbert_model_ready", model=MODEL_NAME)
    return _model


def encode(texts: list[str]) -> np.ndarray:
    """Encode a batch of texts. Returns shape (n, dim) L2-normalized embeddings."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    embeddings = _get_model().encode(
        texts, convert_to_numpy=True, normalize_embeddings=True
    )
    return np.asarray(embeddings, dtype=np.float32)


def cosine_similarity_matrix(query: np.ndarray, refs: np.ndarray) -> np.ndarray:
    """Cosine sim for L2-normalized vectors collapses to a dot product.

    query: (d,) or (q, d); refs: (r, d). Returns (q, r) or (r,) accordingly.
    """
    if query.ndim == 1:
        return np.asarray(refs @ query, dtype=np.float32)
    return np.asarray(query @ refs.T, dtype=np.float32)
