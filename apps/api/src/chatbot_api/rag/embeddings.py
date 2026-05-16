"""OpenAI embeddings con cache filesystem para evitar re-embedding.

`OpenAIEmbeddings` mantiene un httpx client interno atado al event loop que lo
crea. Como los workers Celery hacen `asyncio.run()` por task, cachear el
wrapper a nivel de proceso crashea desde la segunda task ("Event loop is closed").
Por eso `get_embeddings()` construye un wrapper fresco por call; el cache de
disco (LocalFileStore) sí persiste — es filesystem sync y no se ve afectado.
"""

from pathlib import Path

from langchain_classic.embeddings.cache import CacheBackedEmbeddings
from langchain_classic.storage import LocalFileStore
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from chatbot_api.core.settings import get_settings

_STORE_PATH = Path("./.cache/embeddings")


def get_embeddings() -> CacheBackedEmbeddings:
    s = get_settings()
    underlying = OpenAIEmbeddings(
        model=s.openai_embedding_model,
        openai_api_key=SecretStr(s.openai_api_key),
    )
    store = LocalFileStore(str(_STORE_PATH))
    return CacheBackedEmbeddings.from_bytes_store(
        underlying,
        store,
        namespace=s.openai_embedding_model,
    )


def reset_embeddings() -> None:
    """Test helper kept for API compatibility — no module-level cache to clear."""
    return None
