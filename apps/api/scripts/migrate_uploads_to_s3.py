"""One-shot migration: walk LOCAL_UPLOADS_DIR and upload every file to S3
under the same relative key. Idempotent (uses PutObject; overwrites).

Usage:
    uv run python scripts/migrate_uploads_to_s3.py
    uv run python scripts/migrate_uploads_to_s3.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from chatbot_api.core.settings import get_settings
from chatbot_api.core.storage import S3Storage


async def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate ./uploads → S3")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.aws_s3_bucket:
        print("AWS_S3_BUCKET not set — abort.")
        return

    base = Path(settings.local_uploads_dir).resolve()
    if not base.exists():
        print(f"Uploads dir {base} does not exist — nothing to migrate.")
        return

    s3 = S3Storage(
        bucket=settings.aws_s3_bucket,
        region=settings.aws_region,
        access_key_id=settings.aws_access_key_id,
        secret_access_key=settings.aws_secret_access_key,
    )

    # Sanity check connectivity before walking.
    s3.head_bucket()
    print(f"Bucket reachable: {settings.aws_s3_bucket}")

    files = sorted(p for p in base.rglob("*") if p.is_file())
    print(f"Found {len(files)} file(s) under {base}\n")

    uploaded = 0
    skipped = 0
    for path in files:
        key = str(path.relative_to(base))
        size_kb = path.stat().st_size / 1024
        if args.dry_run:
            print(f"  [dry] {key}  ({size_kb:.1f} KB)")
            skipped += 1
            continue
        try:
            content = path.read_bytes()
            await s3.save(key, content)
            print(f"  ok   {key}  ({size_kb:.1f} KB)")
            uploaded += 1
        except Exception as exc:
            print(f"  ERR  {key}: {exc}")

    print(f"\nDone. Uploaded={uploaded}  Skipped={skipped}  Total={len(files)}")


if __name__ == "__main__":
    asyncio.run(main())
