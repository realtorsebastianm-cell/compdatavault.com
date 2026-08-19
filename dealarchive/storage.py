"""Raw flyer file storage -- Cloudflare R2 (S3-compatible object storage).

This used to write to local disk (./storage), which was silently deleting
every flyer anyone had ever forwarded on each Render redeploy -- Render's
filesystem is ephemeral, it doesn't survive a deploy or an instance
restart. R2 is durable object storage instead, and since the exact-match
inbound-email setup already lives on Cloudflare, this keeps flyer storage
in the same place rather than adding a third vendor.

The interface stays narrow (save/read, both keyed by an opaque storage
path) so nothing outside this module needs to know it's R2 under the hood.
"""
from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.config import Config

from dealarchive.config import settings


@lru_cache
def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def save_flyer_file(content: bytes, original_filename: str) -> str:
    """Upload the raw flyer bytes to R2 and return its object key."""
    suffix = Path(original_filename).suffix or ".bin"
    key = f"{uuid.uuid4().hex}{suffix}"
    _client().put_object(Bucket=settings.r2_bucket_name, Key=key, Body=content)
    return key


def read_flyer_file(storage_path: str) -> bytes:
    """Download the raw flyer bytes for a stored object key.

    Raises botocore.exceptions.ClientError (404-ish) if the key doesn't
    exist -- callers should catch that and turn it into an HTTP 404 rather
    than letting it propagate as a 500.
    """
    obj = _client().get_object(Bucket=settings.r2_bucket_name, Key=storage_path)
    return obj["Body"].read()
