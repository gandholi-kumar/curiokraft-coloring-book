"""Data access, repository abstractions, and storage backends for CurioKraft."""

from curiokraft_book.data.base import (
    AssetRepository,
    BookRecord,
    BookRepository,
    LogRepository,
    MediaAssetRecord,
    PageRecord,
    PageRepository,
    PromptRecord,
    PromptRepository,
    StorageBackend,
)

__all__ = [
    "BookRecord",
    "PageRecord",
    "PromptRecord",
    "MediaAssetRecord",
    "BookRepository",
    "PageRepository",
    "PromptRepository",
    "AssetRepository",
    "LogRepository",
    "StorageBackend",
]
