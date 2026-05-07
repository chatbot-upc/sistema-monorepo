"""OpenAI embeddings con cache filesystem para evitar re-embedding."""

from pathlib import Path

from langchain_classic.embeddings.cache import CacheBackedEmbeddings
from langchain_classic.storage import LocalFileStore
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from chatbot_api.core.settings import get_settings

_embeddings: CacheBackedEmbeddings | None = None


def get_embeddings() -> CacheBackedEmbeddings:
    global _embeddings
    if _embeddings is None:
        s = get_settings()
        underlying = OpenAIEmbeddings(
            model=s.openai_embedding_model,
            openai_api_key=SecretStr(s.openai_api_key),
        )
        store = LocalFileStore(str(Path("./.cache/embeddings")))
        _embeddings = CacheBackedEmbeddings.from_bytes_store(
            underlying,
            store,
            namespace=s.openai_embedding_model,
        )
    return _embeddings


def reset_embeddings() -> None:
    """Test helper — clear cached embeddings instance."""
    global _embeddings
    _embeddings = None
