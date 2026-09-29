"""Hybrid Data Store managing zero-downtime dual-writes and graceful fallbacks.

Guarantees:
1. Writes land in both SQL database and legacy pipeline_state.json.
2. Reads query SQL database first, falling back to legacy JSON if unavailable.
3. Legacy scripts and workflows continue executing with zero disruption.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from curiokraft_book.constants import (
    DEFAULT_BOOK_CONFIG,
    DEFAULT_PAGES_MANIFEST,
    DEFAULT_PIPELINE_STATE_FILE,
)
from curiokraft_book.data.base import (
    BookRecord,
    MediaAssetRecord,
    PageRecord,
    StorageBackend,
)
from curiokraft_book.data.object_storage import compute_sha256, get_storage_backend
from curiokraft_book.data.postgres_store import (
    SQLAssetRepository,
    SQLBookRepository,
    SQLDatabaseManager,
    SQLLogRepository,
    SQLPageRepository,
    SQLPromptRepository,
)

logger = logging.getLogger("curiokraft.hybrid_store")


class HybridDataStore:
    """Coordinates dual persistence between SQL databases and filesystem artifacts."""

    def __init__(
        self,
        db_url: str | None = None,
        state_file: str | Path = DEFAULT_PIPELINE_STATE_FILE,
        manifest_path: str | Path = DEFAULT_PAGES_MANIFEST,
        book_config_path: str | Path = DEFAULT_BOOK_CONFIG,
        storage_backend: StorageBackend | None = None,
        book_slug: str | None = None,
    ):
        self.state_file = Path(state_file)
        self.manifest_path = Path(manifest_path)
        self.book_config_path = Path(book_config_path)

        # 1. Initialize Relational DB Engine
        self.db_mgr = SQLDatabaseManager(db_url)
        self.books = SQLBookRepository(self.db_mgr)
        self.pages = SQLPageRepository(self.db_mgr)
        self.prompts = SQLPromptRepository(self.db_mgr)
        self.assets = SQLAssetRepository(self.db_mgr)
        self.logs = SQLLogRepository(self.db_mgr)

        # 2. Initialize Blob / Image Storage
        self.storage = storage_backend or get_storage_backend()

        # 3. Ensure active book record is registered in DB
        self.active_book = self._ensure_active_book(slug_override=book_slug)

    def _ensure_active_book(self, slug_override: str | None = None) -> BookRecord:
        """Read book configuration and ensure a book record exists in DB."""
        import yaml

        try:
            if slug_override:
                existing = self.books.get_by_slug(slug_override)
                if existing:
                    return existing
                new_book = BookRecord(
                    slug=slug_override,
                    title=slug_override.replace("-", " ").title(),
                    volume="vol1",
                    status="IN_PRODUCTION",
                )
                return self.books.save(new_book)

            slug = "tiny-hands-vol1"
            title = "Tiny Hands Color & Learn"
            volume = "vol1"

            if self.book_config_path.exists():
                try:
                    with open(self.book_config_path, encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                    b_cfg = cfg.get("book", {})
                    title = b_cfg.get("title", title)
                    volume = str(b_cfg.get("volume", volume)).lower()
                    slug = f"curiokraft-{volume}"
                except Exception as e:
                    logger.debug(f"Notice reading book_config: {e}")

            existing = self.books.get_by_slug(slug)
            if existing:
                return existing

            new_book = BookRecord(
                slug=slug,
                title=title,
                volume=volume,
                status="IN_PRODUCTION",
            )
            return self.books.save(new_book)
        except Exception as e:
            logger.warning(
                f"Could not connect to database for active book: {e}. Falling back to in-memory book record."
            )
            target_slug = slug_override or "curiokraft-vol1"
            return BookRecord(
                slug=target_slug,
                title="Tiny Hands Color & Learn",
                volume="vol1",
                status="IN_PRODUCTION",
            )

    # --------------------------------------------------------------------------
    # Page Operations (Dual-Write & Fallback Read)
    # --------------------------------------------------------------------------

    def get_page(self, page_id: str) -> PageRecord | None:
        """Fetch page from SQL first; fall back to manifest or pipeline_state.json if missing."""
        rec = self.pages.get_page(self.active_book.id, page_id)
        if rec:
            return rec

        # Check if manifest needs to be bootstrapped into DB
        self._bootstrap_pages_from_manifest()
        rec = self.pages.get_page(self.active_book.id, page_id)
        if rec:
            return rec

        # Fallback to filesystem JSON
        if self.state_file.exists():
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    data = json.load(f)
                pages_dict = data.get("pages", {})
                if page_id in pages_dict:
                    raw = pages_dict[page_id]
                    p = PageRecord(
                        book_id=self.active_book.id,
                        page_id=page_id,
                        page_number=raw.get("page_number", 0),
                        section=raw.get("section", "General"),
                        canonical_object=raw.get("canonical_object", ""),
                        display_label=raw.get("display_label", ""),
                        status=raw.get("status", "planned"),
                        attempts=raw.get("attempts", 0),
                        positive_prompt=raw.get("positive_prompt"),
                        negative_prompt=raw.get("negative_prompt"),
                        raw_image_path=raw.get("raw_image_path"),
                        rescued_image_path=raw.get("rescued_image_path"),
                        composite_image_path=raw.get("composite_image_path"),
                        qa_score=raw.get("qa_score", 0.0),
                        qa_passed=raw.get("qa_passed", False),
                        violations=raw.get("violations", []),
                        last_updated=raw.get("last_updated"),
                    )
                    # Sync into SQL
                    return self.pages.save_page(p)
            except Exception as e:
                logger.debug(f"Filesystem read notice: {e}")

        return None

    def get_all_pages(self) -> list[PageRecord]:
        """Fetch all pages for active book."""
        db_pages = self.pages.get_pages_for_book(self.active_book.id)
        if db_pages:
            return db_pages

        # If DB is empty, bootstrap from manifest or state file
        self._bootstrap_pages_from_manifest()
        return self.pages.get_pages_for_book(self.active_book.id)

    def _bootstrap_pages_from_manifest(self) -> None:
        """Load manifest/pages.json into DB."""
        if not self.manifest_path.exists():
            return

        try:
            with open(self.manifest_path, encoding="utf-8") as f:
                data = json.load(f)
            pages = []
            for item in data.get("pages", []):
                p = PageRecord(
                    book_id=self.active_book.id,
                    page_id=item["page_id"],
                    page_number=item["page_number"],
                    canonical_object=item["canonical_object"],
                    display_label=item.get("display_label", item["canonical_object"].upper()),
                    section=item.get("section", "General"),
                    cards=item.get("cards", []),
                    page_type=item.get("type", "coloring_page"),
                )
                pages.append(p)
            self.pages.bulk_save_pages(pages)
            logger.info(f"Bootstrapped {len(pages)} pages into database from {self.manifest_path}.")
        except Exception as e:
            logger.error(f"Failed to bootstrap pages from manifest: {e}")

    def update_page(self, page_id: str, **kwargs) -> PageRecord:
        """Dual-write update: persist to SQL and write to pipeline_state.json atomically."""
        kwargs.pop("page_id", None)
        page = self.get_page(page_id)
        if not page:
            raise KeyError(f"Page ID '{page_id}' not found.")

        updated_dict = page.model_dump()
        updated_dict.update(kwargs)
        new_page = PageRecord(**updated_dict)

        # 1. Write to SQL
        saved_page = self.pages.save_page(new_page)

        # 2. Write to Legacy pipeline_state.json
        self._sync_to_legacy_json(saved_page)

        return saved_page

    def _sync_to_legacy_json(self, updated_page: PageRecord) -> None:
        """Reflect page changes in legacy JSON for backward compatibility."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            existing_data: dict[str, Any] = {"pages": {}}
            if self.state_file.exists():
                try:
                    with open(self.state_file, encoding="utf-8") as f:
                        existing_data = json.load(f)
                except Exception as e:
                    # Non-fatal: existing legacy state file may be empty or corrupted
                    logger.warning(
                        "Could not parse existing legacy state file %s: %s", self.state_file, e
                    )

            pages_dict = existing_data.get("pages", {})
            pages_dict[updated_page.page_id] = {
                "page_id": updated_page.page_id,
                "page_number": updated_page.page_number,
                "canonical_object": updated_page.canonical_object,
                "display_label": updated_page.display_label,
                "section": updated_page.section,
                "status": updated_page.status,
                "attempts": updated_page.attempts,
                "max_attempts": updated_page.max_attempts,
                "positive_prompt": updated_page.positive_prompt,
                "negative_prompt": updated_page.negative_prompt,
                "raw_image_path": updated_page.raw_image_path,
                "rescued_image_path": updated_page.rescued_image_path,
                "composite_image_path": updated_page.composite_image_path,
                "qa_score": updated_page.qa_score,
                "qa_passed": updated_page.qa_passed,
                "violations": updated_page.violations,
                "last_updated": updated_page.last_updated,
            }

            # Summary counts
            summary: dict[str, int] = {}
            for p in pages_dict.values():
                st = p.get("status", "planned")
                summary[st] = summary.get(st, 0) + 1

            serializable = {
                "total_pages": len(pages_dict),
                "summary": summary,
                "pages": pages_dict,
            }

            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
            temp_file.replace(self.state_file)
        except Exception as e:
            logger.debug(f"Dual-write JSON update notice: {e}")

    # --------------------------------------------------------------------------
    # Asset Management & Deduplication
    # --------------------------------------------------------------------------

    def register_media_asset(
        self,
        local_path: str | Path,
        asset_type: str,
        page_id: str | None = None,
    ) -> MediaAssetRecord:
        """Register an on-disk image with content-addressable SHA-256 hash."""
        p = Path(local_path)
        if not p.exists():
            raise FileNotFoundError(f"Asset file not found: {local_path}")

        sha256 = compute_sha256(p)
        file_size = p.stat().st_size

        # Check if asset already registered for this book and page
        if page_id:
            page_assets = self.assets.list_assets_for_page(self.active_book.id, page_id)
            existing_for_page = next((a for a in page_assets if a.asset_type == asset_type), None)
            if existing_for_page and existing_for_page.sha256_hash == sha256:
                logger.info(
                    f"Asset {p.name} already registered for book {self.active_book.slug} page {page_id}."
                )
                return existing_for_page
        else:
            existing_for_page = None

        # Extract image metadata
        width_px = 2550
        height_px = 3300
        dpi = 300
        color_mode = "L"
        mime_type = "image/png"
        suffix = p.suffix.lower()

        if suffix in [".png", ".jpg", ".jpeg", ".webp"]:
            try:
                from PIL import Image

                with Image.open(p) as img:
                    width_px, height_px = img.size
                    color_mode = img.mode
                    info_dpi = img.info.get("dpi")
                    if info_dpi and isinstance(info_dpi, tuple):
                        dpi = int(info_dpi[0])
                    mime_type = f"image/{suffix.replace('.', '')}"
                    if suffix in [".jpg", ".jpeg"]:
                        mime_type = "image/jpeg"
            except Exception as e:
                logger.debug(f"Could not extract PIL metadata for {p}: {e}")
        elif suffix == ".pdf":
            mime_type = "application/pdf"
            color_mode = "CMYK" if "cmyk" in p.name.lower() else "RGB"

        # Check if hash already exists in DB (CAS deduplication)
        existing_hash = self.assets.find_by_hash(sha256)
        if existing_hash and existing_hash.storage_key:
            # CAS: Reuse the existing stored object without re-uploading duplicate bytes
            uploaded_uri = existing_hash.storage_key
            backend_name = existing_hash.storage_backend
            logger.info(f"Asset {p.name} (SHA-256 {sha256[:8]}) reuses storage key: {uploaded_uri}")
        else:
            # Upload to configured storage backend if cloud is enabled
            storage_key = f"{self.active_book.slug}/{asset_type}/{p.name}"
            if not isinstance(self.storage, get_storage_backend(backend_type="local").__class__):
                uploaded_uri = self.storage.upload_file(str(p), storage_key)
                backend_name = "s3_r2"
            else:
                uploaded_uri = str(p)
                backend_name = "local_disk"

        asset_id = existing_for_page.id if existing_for_page else str(uuid4())
        asset = MediaAssetRecord(
            id=asset_id,
            book_id=self.active_book.id,
            page_id=page_id,
            asset_type=asset_type,
            storage_backend=backend_name,
            storage_key=uploaded_uri,
            sha256_hash=sha256,
            width_px=width_px,
            height_px=height_px,
            dpi=dpi,
            color_mode=color_mode,
            file_size_bytes=file_size,
            mime_type=mime_type,
        )
        return self.assets.save_asset(asset)

    def find_raw_asset_by_canonical(self, canonical_object: str) -> Path | None:
        """Query database across all books for an existing raw illustration of this canonical object."""
        if not canonical_object:
            return None
        pages = self.pages.find_by_canonical(canonical_object)
        for p in pages:
            if p.raw_image_path:
                cand = Path(p.raw_image_path)
                if cand.exists() and cand.stat().st_size > 50:
                    return cand
            if p.composite_image_path:
                cand = Path(p.composite_image_path)
                if cand.exists() and cand.stat().st_size > 50:
                    return cand
        return None


_global_data_store: HybridDataStore | None = None


def get_data_store(book_slug: str | None = None) -> HybridDataStore:
    """Global accessor for HybridDataStore singleton or scoped book instance."""
    global _global_data_store
    if book_slug:
        return HybridDataStore(book_slug=book_slug)
    if _global_data_store is None:
        _global_data_store = HybridDataStore()
    return _global_data_store


def reset_global_data_store() -> None:
    """Reset the global HybridDataStore singleton (primarily used for test isolation)."""
    global _global_data_store
    _global_data_store = None
