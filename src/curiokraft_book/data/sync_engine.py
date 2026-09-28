"""Offline-to-Cloud Bi-Directional Synchronization Engine.

Enables seamless workflow:
1. Work offline (on local Docker or zero-dependency SQLite/Disk).
2. Changes accumulate in sync_outbox with pending_upload status.
3. When network is restored, `curiokraft-book db sync` pushes pending records
   to Neon PostgreSQL and uploads media binaries to Cloudflare R2.
4. Pulls down any remote changes made in other sessions.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select

from curiokraft_book.data.base import StorageBackend, SyncStatus
from curiokraft_book.data.hybrid_store import HybridDataStore
from curiokraft_book.data.models import (
    BookModel,
    MediaAssetModel,
    OutboxEventModel,
    PageModel,
    PromptModel,
)
from curiokraft_book.data.object_storage import S3StorageBackend
from curiokraft_book.data.postgres_store import SQLDatabaseManager

logger = logging.getLogger("curiokraft.sync")


class SyncReport(BaseModel):
    """Execution summary of synchronization run."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pushed_books: int = 0
    pushed_pages: int = 0
    pushed_prompts: int = 0
    pushed_assets: int = 0
    pulled_pages: int = 0
    conflicts_resolved: int = 0
    errors: list[str] = Field(default_factory=list)
    success: bool = True


class SyncEngine:
    """Orchestrates bi-directional data and asset sync between local and remote stores."""

    def __init__(
        self,
        local_store: HybridDataStore,
        remote_db_url: str | None = None,
        remote_storage: StorageBackend | None = None,
    ):
        self.local_store = local_store
        self.remote_db_url = remote_db_url or os.environ.get("REMOTE_DATABASE_URL")
        self.remote_db_mgr: SQLDatabaseManager | None = None

        if self.remote_db_url:
            try:
                self.remote_db_mgr = SQLDatabaseManager(self.remote_db_url)
            except Exception as e:
                logger.warning(f"Could not connect to remote database: {e}")

        # Cloudflare R2 / S3 client
        self.remote_storage = remote_storage
        self._book_id_map: dict[str, str] = {}
        bucket = os.environ.get("S3_BUCKET_NAME", "curiokraft-assets")
        if not self.remote_storage and (
            os.environ.get("S3_ENDPOINT_URL") or os.environ.get("S3_ACCESS_KEY_ID")
        ):
            try:
                self.remote_storage = S3StorageBackend(bucket_name=bucket)
            except Exception as e:
                logger.warning(f"Could not connect to remote R2/S3 storage: {e}")

    def sync(self) -> SyncReport:
        """Execute bi-directional sync."""
        report = SyncReport()

        if not self.remote_db_mgr:
            report.errors.append(
                "Remote database URL not configured or unreachable (REMOTE_DATABASE_URL)."
            )
            report.success = False
            return report

        logger.info("Starting Offline-to-Cloud synchronization...")

        # 1. Process Outbox: Push Local Changes to Remote
        try:
            self._push_outbox_events(report)
        except Exception as e:
            msg = f"Outbox push error: {e}"
            logger.error(msg)
            report.errors.append(msg)
            report.success = False

        # 2. Pull Remote Updates to Local
        try:
            self._pull_remote_updates(report)
        except Exception as e:
            msg = f"Remote pull error: {e}"
            logger.error(msg)
            report.errors.append(msg)
            report.success = False

        logger.info(
            f"Sync finished: pushed {report.pushed_pages} pages, {report.pushed_assets} assets. Success={report.success}."
        )
        return report

    def _resolve_remote_book_id(self, local_book_id: str, remote_s: Any) -> str:
        """Resolve corresponding remote book ID if local and remote differ."""
        if local_book_id in self._book_id_map:
            return self._book_id_map[local_book_id]
        if remote_s.get(BookModel, local_book_id):
            self._book_id_map[local_book_id] = local_book_id
            return local_book_id
        local_book = self.local_store.books.get_by_id(local_book_id)
        if local_book and local_book.slug:
            remote_b = remote_s.scalars(
                select(BookModel).where(BookModel.slug == local_book.slug)
            ).first()
            if remote_b:
                self._book_id_map[local_book_id] = remote_b.id
                return remote_b.id
        return local_book_id

    def _push_outbox_events(self, report: SyncReport) -> None:
        """Iterate pending events in local sync_outbox and apply to remote database."""
        if not self.remote_db_mgr:
            return

        with self.local_store.db_mgr.session() as local_s:
            stmt = select(OutboxEventModel).where(OutboxEventModel.status == "PENDING")
            pending_events = local_s.scalars(stmt).all()

            if not pending_events:
                logger.info("No pending local outbox events to sync.")
                return

            with self.remote_db_mgr.session() as remote_s:
                for ev in pending_events:
                    try:
                        if ev.entity_type == "book":
                            self._sync_book_to_remote(ev.payload, remote_s)
                            report.pushed_books += 1
                        elif ev.entity_type == "page":
                            self._sync_page_to_remote(ev.payload, remote_s)
                            report.pushed_pages += 1
                        elif ev.entity_type == "prompt":
                            self._sync_prompt_to_remote(ev.payload, remote_s)
                            report.pushed_prompts += 1
                        elif ev.entity_type == "media_asset":
                            self._sync_asset_to_remote(ev.payload, remote_s)
                            report.pushed_assets += 1

                        ev.status = "PROCESSED"
                        ev.processed_at = datetime.now(timezone.utc).isoformat()
                    except Exception as ev_err:
                        logger.error(f"Failed syncing event {ev.id}: {ev_err}")
                        ev.status = "FAILED"
                        report.errors.append(str(ev_err))

    def _sync_book_to_remote(self, payload: dict[str, Any], remote_s: Any) -> None:
        b_id = payload["id"]
        remote_m = remote_s.get(BookModel, b_id)
        if not remote_m and "slug" in payload:
            remote_m = remote_s.scalars(
                select(BookModel).where(BookModel.slug == payload["slug"])
            ).first()
        payload["sync_status"] = SyncStatus.SYNCED.value
        if remote_m:
            self._book_id_map[b_id] = remote_m.id
            for k, v in payload.items():
                if k != "id":
                    setattr(remote_m, k, v)
        else:
            self._book_id_map[b_id] = b_id
            remote_s.add(BookModel(**payload))

    def _sync_page_to_remote(self, payload: dict[str, Any], remote_s: Any) -> None:
        if "book_id" in payload:
            payload["book_id"] = self._resolve_remote_book_id(payload["book_id"], remote_s)
        p_id = payload["id"]
        remote_m = remote_s.get(PageModel, p_id)
        payload["sync_status"] = SyncStatus.SYNCED.value
        if remote_m:
            # Conflict check: Last-Write-Wins based on updated_at
            remote_updated = remote_m.updated_at or ""
            local_updated = payload.get("updated_at", "")
            if local_updated >= remote_updated:
                for k, v in payload.items():
                    setattr(remote_m, k, v)
        else:
            remote_s.add(PageModel(**payload))

    def _sync_prompt_to_remote(self, payload: dict[str, Any], remote_s: Any) -> None:
        if "book_id" in payload:
            payload["book_id"] = self._resolve_remote_book_id(payload["book_id"], remote_s)
        pr_id = payload["id"]
        remote_m = remote_s.get(PromptModel, pr_id)
        payload["sync_status"] = SyncStatus.SYNCED.value
        if remote_m:
            if not remote_m.is_locked:
                for k, v in payload.items():
                    setattr(remote_m, k, v)
        else:
            remote_s.add(PromptModel(**payload))

    def _sync_asset_to_remote(self, payload: dict[str, Any], remote_s: Any) -> None:
        if "book_id" in payload:
            payload["book_id"] = self._resolve_remote_book_id(payload["book_id"], remote_s)
        # If remote storage is available, ensure the binary is uploaded to Cloudflare R2
        storage_key = payload.get("storage_key", "")
        if self.remote_storage and storage_key:
            local_path = Path(storage_key)
            if local_path.exists():
                r2_key = f"{payload.get('book_id', 'book')}/{payload.get('asset_type', 'assets')}/{local_path.name}"
                cloud_uri = self.remote_storage.upload_file(str(local_path), r2_key)
                payload["storage_key"] = cloud_uri
                payload["storage_backend"] = "s3_r2"

        a_id = payload["id"]
        remote_m = remote_s.get(MediaAssetModel, a_id)
        payload["sync_status"] = SyncStatus.SYNCED.value
        if remote_m:
            for k, v in payload.items():
                setattr(remote_m, k, v)
        else:
            remote_s.add(MediaAssetModel(**payload))

    def _pull_remote_updates(self, report: SyncReport) -> None:
        """Fetch remote page states and pull into local database."""
        if not self.remote_db_mgr:
            return

        with self.remote_db_mgr.session() as remote_s:
            local_book = self.local_store.active_book
            stmt_book = select(BookModel).where(
                (BookModel.id == local_book.id) | (BookModel.slug == local_book.slug)
            )
            remote_book = remote_s.scalars(stmt_book).first()
            if not remote_book:
                return

            stmt = select(PageModel).where(PageModel.book_id == remote_book.id)
            remote_pages = remote_s.scalars(stmt).all()

            with self.local_store.db_mgr.session() as local_s:
                for rp in remote_pages:
                    stmt_local_p = select(PageModel).where(
                        PageModel.book_id == local_book.id, PageModel.page_id == rp.page_id
                    )
                    local_p = local_s.scalars(stmt_local_p).first()
                    if not local_p:
                        # Add missing remote page to local
                        data = {col.name: getattr(rp, col.name) for col in rp.__table__.columns}
                        data["book_id"] = local_book.id
                        data["sync_status"] = SyncStatus.SYNCED.value
                        local_s.add(PageModel(**data))
                        report.pulled_pages += 1
                    elif (rp.updated_at or "") > (local_p.updated_at or ""):
                        # Remote is newer: update local
                        for col in rp.__table__.columns:
                            if col.name not in ("id", "book_id"):
                                setattr(local_p, col.name, getattr(rp, col.name))
                        local_p.sync_status = SyncStatus.SYNCED.value
                        report.pulled_pages += 1
                        report.conflicts_resolved += 1
