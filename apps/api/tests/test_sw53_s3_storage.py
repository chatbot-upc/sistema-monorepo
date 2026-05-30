"""SW-53 — S3Storage backend, tested in-memory with moto."""

from __future__ import annotations

import pytest
from moto import mock_aws

from chatbot_api.core.storage import LocalFileStorage, S3Storage, get_storage, reset_storage


@pytest.fixture
def aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide fake credentials so boto3 client builds happy under moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.mark.asyncio
async def test_s3_storage_save_get_delete_roundtrip(aws_env: None) -> None:
    bucket = "chatbot-upc-test"
    with mock_aws():
        import boto3

        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=bucket)
        storage = S3Storage(bucket=bucket, region="us-east-1")
        key = "docs/abc/example.pdf"
        body = b"%PDF-1.7 fake content"

        location = await storage.save(key, body)
        assert location == f"s3://{bucket}/{key}"

        got = await storage.get(key)
        assert got == body

        await storage.delete(key)
        # Reading after delete should error.
        from botocore.exceptions import ClientError
        with pytest.raises(ClientError):
            await storage.get(key)


def test_get_storage_selects_s3_when_bucket_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_S3_BUCKET", "chatbot-upc-test")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    from chatbot_api.core.settings import get_settings

    get_settings.cache_clear()
    reset_storage()
    storage = get_storage()
    try:
        assert isinstance(storage, S3Storage)
        assert storage.bucket == "chatbot-upc-test"
    finally:
        reset_storage()
        get_settings.cache_clear()


def test_get_storage_falls_back_to_local_when_no_bucket(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    monkeypatch.setenv("AWS_S3_BUCKET", "")
    monkeypatch.setenv("LOCAL_UPLOADS_DIR", str(tmp_path))
    from chatbot_api.core.settings import get_settings

    get_settings.cache_clear()
    reset_storage()
    storage = get_storage()
    try:
        assert isinstance(storage, LocalFileStorage)
    finally:
        reset_storage()
        get_settings.cache_clear()


def test_head_bucket_raises_on_missing_bucket(aws_env: None) -> None:
    from botocore.exceptions import ClientError
    with mock_aws():
        storage = S3Storage(bucket="does-not-exist", region="us-east-1")
        with pytest.raises(ClientError):
            storage.head_bucket()
