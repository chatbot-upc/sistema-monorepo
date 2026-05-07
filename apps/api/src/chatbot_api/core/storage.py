"""Storage abstraction. Fase 3: LocalFileStorage. Fase 5: agregar S3Storage."""

from abc import ABC, abstractmethod
from pathlib import Path

from .settings import get_settings


class Storage(ABC):
    @abstractmethod
    async def save(self, key: str, content: bytes) -> str: ...

    @abstractmethod
    async def get(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class LocalFileStorage(Storage):
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, key: str, content: bytes) -> str:
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    async def get(self, key: str) -> bytes:
        return (self.base_dir / key).read_bytes()

    async def delete(self, key: str) -> None:
        (self.base_dir / key).unlink(missing_ok=True)


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = LocalFileStorage(get_settings().local_uploads_dir)
    return _storage


def reset_storage() -> None:
    """Test helper — clear cached storage instance."""
    global _storage
    _storage = None
