"""Abstract repository interfaces and core data records for CurioKraft.

Adheres strictly to the Dependency Inversion Principle (DIP): high-level pipeline
components depend on these abstractions rather than concrete database engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    """Synchronization lifecycle for offline-to-cloud operations."""

    SYNCED = "synced"
    PENDING_UPLOAD = "pending_upload"
    CONFLICT = "conflict"


class BookRecord(BaseModel):
    """Normalized book metadata entity."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = "default_tenant"
    slug: str
    title: str
    subtitle: str = ""
    volume: str = "vol1"
    imprint: str = "CurioKraft Publications"
    target_audience: dict[str, Any] = Field(default_factory=dict)
    layout: str = "single_sided"
    bleed: bool = False
    trim_width_in: float = 8.5
    trim_height_in: float = 11.0
    spine_width_in: float = 0.248
    page_count: int = 110
    visual_style: dict[str, Any] = Field(default_factory=dict)
    status: str = "DRAFT"
    sync_status: SyncStatus = SyncStatus.PENDING_UPLOAD
    version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PageRecord(BaseModel):
    """Execution state and artifact linkage for an individual book page."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    book_id: str
    page_id: str
    page_number: int
    section: str = "General"
    canonical_object: str
    display_label: str
    page_type: str = "coloring_page"
    cards: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "planned"
    attempts: int = 0
    max_attempts: int = 3
    qa_score: float = 0.0
    qa_passed: bool = False
    violations: list[str] = Field(default_factory=list)
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    raw_image_path: str | None = None
    rescued_image_path: str | None = None
    composite_image_path: str | None = None
    sync_status: SyncStatus = SyncStatus.PENDING_UPLOAD
    version: int = 1
    last_updated: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PromptRecord(BaseModel):
    """Persisted generation prompt instruction and configuration."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    book_id: str
    page_id: str | None = None
    prompt_type: str = "interior_page"
    positive_prompt: str
    negative_prompt: str = ""
    temperature: float = 0.5
    top_p: float = 0.95
    aspect_ratio: str = "3:4"
    preset_name: str = "CurioKraft - Interior Coloring Pages"
    chat_id: str | None = None
    version: int = 1
    is_locked: bool = False
    sync_status: SyncStatus = SyncStatus.PENDING_UPLOAD
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MediaAssetRecord(BaseModel):
    """Metadata catalog record for an image or document binary."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    book_id: str
    page_id: str | None = None
    asset_type: (
        str  # raw_image, rescued_image, composite_master, cover_png, cover_pdf, interior_pdf
    )
    storage_backend: str = "local_disk"  # local_disk, s3_r2, minio
    storage_key: str  # Path or S3 URI
    sha256_hash: str
    width_px: int = 2550
    height_px: int = 3300
    dpi: int = 300
    color_mode: str = "L"
    file_size_bytes: int = 0
    mime_type: str = "image/png"
    sync_status: SyncStatus = SyncStatus.PENDING_UPLOAD
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LogRecord(BaseModel):
    """Structured audit and pipeline event log."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    book_id: str | None = None
    session_id: str = ""
    level: str = "INFO"
    component: str = "pipeline"
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ==============================================================================
# Abstract Repository Interfaces
# ==============================================================================


class BookRepository(ABC):
    """Abstract contract for book persistence."""

    @abstractmethod
    def get_by_id(self, book_id: str) -> BookRecord | None:
        pass

    @abstractmethod
    def get_by_slug(self, slug: str) -> BookRecord | None:
        pass

    @abstractmethod
    def save(self, book: BookRecord) -> BookRecord:
        pass

    @abstractmethod
    def list_books(self, tenant_id: str = "default_tenant") -> list[BookRecord]:
        pass


class PageRepository(ABC):
    """Abstract contract for page state persistence."""

    @abstractmethod
    def get_page(self, book_id: str, page_id: str) -> PageRecord | None:
        pass

    @abstractmethod
    def get_pages_for_book(self, book_id: str) -> list[PageRecord]:
        pass

    @abstractmethod
    def save_page(self, page: PageRecord) -> PageRecord:
        pass

    @abstractmethod
    def bulk_save_pages(self, pages: list[PageRecord]) -> None:
        pass

    @abstractmethod
    def find_by_canonical(self, canonical_object: str) -> list[PageRecord]:
        pass


class PromptRepository(ABC):
    """Abstract contract for prompt persistence and locking."""

    @abstractmethod
    def get_prompt(
        self, book_id: str, page_id: str | None, prompt_type: str
    ) -> PromptRecord | None:
        pass

    @abstractmethod
    def save_prompt(self, prompt: PromptRecord) -> PromptRecord:
        pass

    @abstractmethod
    def list_prompts_for_book(self, book_id: str) -> list[PromptRecord]:
        pass


class AssetRepository(ABC):
    """Abstract contract for media asset cataloging and CAS lookup."""

    @abstractmethod
    def get_asset(self, asset_id: str) -> MediaAssetRecord | None:
        pass

    @abstractmethod
    def find_by_hash(self, sha256_hash: str) -> MediaAssetRecord | None:
        pass

    @abstractmethod
    def save_asset(self, asset: MediaAssetRecord) -> MediaAssetRecord:
        pass

    @abstractmethod
    def list_assets_for_page(self, book_id: str, page_id: str) -> list[MediaAssetRecord]:
        pass

    @abstractmethod
    def list_assets_for_book(self, book_id: str) -> list[MediaAssetRecord]:
        pass


class LogRepository(ABC):
    """Abstract contract for structured logging."""

    @abstractmethod
    def log(self, record: LogRecord) -> None:
        pass


class StorageBackend(ABC):
    """Abstract contract for physical binary blob storage (S3 / R2 / MinIO / Local Disk)."""

    @abstractmethod
    def upload_file(self, local_path: str, storage_key: str, mime_type: str = "image/png") -> str:
        """Upload local file to storage and return its canonical storage key/URI."""
        pass

    @abstractmethod
    def download_file(self, storage_key: str, destination_path: str) -> bool:
        """Download binary from storage to local file path."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Verify existence of blob in storage."""
        pass

    @abstractmethod
    def get_bytes(self, storage_key: str) -> bytes | None:
        """Fetch raw bytes directly from storage."""
        pass
