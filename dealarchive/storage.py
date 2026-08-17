"""Raw flyer file storage.

Local disk for now, behind a narrow interface so swapping in S3 later only
touches this module.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from dealarchive.config import settings


def save_flyer_file(content: bytes, original_filename: str) -> str:
    """Persist the raw flyer bytes and return a storage path (relative)."""
    storage_dir = Path(settings.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_filename).suffix or ".bin"
    key = f"{uuid.uuid4().hex}{suffix}"
    (storage_dir / key).write_bytes(content)
    return key


def read_flyer_file(storage_path: str) -> bytes:
    return (Path(settings.storage_dir) / storage_path).read_bytes()


def flyer_file_path(storage_path: str) -> Path:
    return Path(settings.storage_dir) / storage_path
