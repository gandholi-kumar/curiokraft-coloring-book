"""Object storage adapters for CurioKraft media assets.

Supports:
1. LocalFileSystemStorage: Zero-dependency local storage for offline development.
2. S3StorageBackend: S3-compatible cloud storage (Cloudflare R2, MinIO, AWS S3).
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import shutil
from pathlib import Path

from curiokraft_book.data.base import StorageBackend

logger = logging.getLogger("curiokraft.storage")


def compute_sha256(file_path_or_bytes: str | Path | bytes) -> str:
    """Compute SHA-256 hash for content-addressable storage and de-duplication."""
    hasher = hashlib.sha256()
    if isinstance(file_path_or_bytes, (str, Path)):
        p = Path(file_path_or_bytes)
        if not p.exists():
            return ""
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
    elif isinstance(file_path_or_bytes, bytes):
        hasher.update(file_path_or_bytes)
    return hasher.hexdigest()


class LocalFileStorageBackend(StorageBackend):
    """Local filesystem storage adapter (used in No-Docker offline mode)."""

    def __init__(self, base_dir: str | Path = "storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload_file(self, local_path: str, storage_key: str, mime_type: str = "image/png") -> str:
        src = Path(local_path)
        if not src.exists():
            raise FileNotFoundError(f"Source file does not exist: {local_path}")

        dest = self.base_dir / storage_key.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        logger.debug(f"Stored local asset {src} -> {dest}")
        return str(dest)

    def download_file(self, storage_key: str, destination_path: str) -> bool:
        src = self.base_dir / storage_key.lstrip("/")
        if not src.exists():
            return False
        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return True

    def exists(self, storage_key: str) -> bool:
        return (self.base_dir / storage_key.lstrip("/")).exists()

    def get_bytes(self, storage_key: str) -> bytes | None:
        p = self.base_dir / storage_key.lstrip("/")
        if p.exists():
            return p.read_bytes()
        return None


class S3StorageBackend(StorageBackend):
    """S3-compatible object storage adapter (Cloudflare R2, MinIO, AWS S3)."""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region_name: str = "auto",
    ):
        import boto3
        from botocore.config import Config

        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url or os.environ.get("S3_ENDPOINT_URL")
        key_id = access_key_id or os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = secret_access_key or os.environ.get("S3_SECRET_ACCESS_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY")

        config = Config(s3={"addressing_style": "path"}) if "localhost" in str(self.endpoint_url) or "127.0.0.1" in str(self.endpoint_url) else Config()

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=config,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except Exception:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Created S3/R2 bucket '{self.bucket_name}'.")
            except Exception as e:
                logger.debug(f"Bucket check/create notice: {e}")

    def upload_file(self, local_path: str, storage_key: str, mime_type: str = "image/png") -> str:
        clean_key = storage_key.lstrip("/")
        guess_type, _ = mimetypes.guess_type(local_path)
        content_type = mime_type or guess_type or "application/octet-stream"

        with open(local_path, "rb") as f:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=clean_key,
                Body=f,
                ContentType=content_type,
            )
        logger.info(f"Uploaded {local_path} to s3://{self.bucket_name}/{clean_key}")
        return f"s3://{self.bucket_name}/{clean_key}"

    def download_file(self, storage_key: str, destination_path: str) -> bool:
        clean_key = storage_key.replace(f"s3://{self.bucket_name}/", "").lstrip("/")
        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.s3_client.download_file(self.bucket_name, clean_key, str(dest))
            return True
        except Exception as e:
            logger.error(f"Failed downloading {clean_key} from {self.bucket_name}: {e}")
            return False

    def exists(self, storage_key: str) -> bool:
        clean_key = storage_key.replace(f"s3://{self.bucket_name}/", "").lstrip("/")
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=clean_key)
            return True
        except Exception:
            return False

    def get_bytes(self, storage_key: str) -> bytes | None:
        clean_key = storage_key.replace(f"s3://{self.bucket_name}/", "").lstrip("/")
        try:
            resp = self.s3_client.get_object(Bucket=self.bucket_name, Key=clean_key)
            return resp["Body"].read()
        except Exception as e:
            logger.error(f"Failed fetching bytes for {clean_key}: {e}")
            return None


def get_storage_backend(
    backend_type: str = "auto",
    bucket_name: str = "curiokraft-assets",
    local_dir: str = "storage",
) -> StorageBackend:
    """Factory creating the appropriate StorageBackend strategy."""
    mode = backend_type.lower()
    if mode == "auto":
        if os.environ.get("S3_ENDPOINT_URL") or os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID"):
            mode = "s3"
        else:
            mode = "local"

    if mode in ["s3", "r2", "minio"]:
        try:
            return S3StorageBackend(bucket_name=bucket_name)
        except Exception as e:
            logger.warning(f"Failed initializing S3 storage ({e}); falling back to local disk storage.")
            return LocalFileStorageBackend(base_dir=local_dir)

    return LocalFileStorageBackend(base_dir=local_dir)
