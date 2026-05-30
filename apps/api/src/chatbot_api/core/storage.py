"""Storage abstraction.

Two backends:
- `LocalFileStorage`: filesystem under `LOCAL_UPLOADS_DIR`. Default in dev.
- `S3Storage`: AWS S3 via boto3. Used in any environment where
  `AWS_S3_BUCKET` is set.

`get_storage()` returns the right backend based on settings. boto3 calls are
sync, so we offload them with `asyncio.to_thread` to keep async semantics in
the worker without making code paths conditional.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import structlog

from .settings import get_settings

log = structlog.get_logger()


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


class S3Storage(Storage):
    """S3 backend. Builds the boto3 client lazily so workers can fork safely."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self._access_key_id = access_key_id or None
        self._secret_access_key = secret_access_key or None
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3

            kwargs: dict[str, Any] = {"region_name": self.region}
            if self._access_key_id and self._secret_access_key:
                kwargs["aws_access_key_id"] = self._access_key_id
                kwargs["aws_secret_access_key"] = self._secret_access_key
            self._client = boto3.client("s3", **kwargs)
        return self._client

    async def save(self, key: str, content: bytes) -> str:
        def _put() -> None:
            self._get_client().put_object(
                Bucket=self.bucket, Key=key, Body=content
            )

        await asyncio.to_thread(_put)
        return f"s3://{self.bucket}/{key}"

    async def get(self, key: str) -> bytes:
        def _get() -> bytes:
            resp = self._get_client().get_object(Bucket=self.bucket, Key=key)
            return bytes(resp["Body"].read())

        return await asyncio.to_thread(_get)

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            self._get_client().delete_object(Bucket=self.bucket, Key=key)

        await asyncio.to_thread(_delete)

    def head_bucket(self) -> None:
        """Sync probe used by scripts/verify_s3.py and lifespan checks."""
        self._get_client().head_bucket(Bucket=self.bucket)


_storage: Storage | None = None


def get_storage() -> Storage:
    """Return cached storage backend (S3 if configured, local filesystem else)."""
    global _storage
    if _storage is None:
        settings = get_settings()
        if settings.aws_s3_bucket:
            _storage = S3Storage(
                bucket=settings.aws_s3_bucket,
                region=settings.aws_region,
                access_key_id=settings.aws_access_key_id,
                secret_access_key=settings.aws_secret_access_key,
            )
            log.info(
                "storage_backend_selected",
                backend="s3",
                bucket=settings.aws_s3_bucket,
                region=settings.aws_region,
            )
        else:
            _storage = LocalFileStorage(settings.local_uploads_dir)
            log.info(
                "storage_backend_selected",
                backend="local",
                path=str(settings.local_uploads_dir),
            )
    return _storage


def reset_storage() -> None:
    """Test helper — clear cached storage instance."""
    global _storage
    _storage = None
