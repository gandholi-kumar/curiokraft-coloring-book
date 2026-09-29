"""Incremental Book Cloud Promotion Engine.

Promotes local Docker / offline books, pages, prompts, and media assets
to Neon Serverless PostgreSQL and Backblaze B2 S3 storage with:
1. O(1) Batch change detection (single SQL query per database, zero S3 calls).
2. Set-difference book and page delta querying.
3. Content-Addressable Storage (CAS) hash deduplication on Backblaze B2.
4. Zero billable S3 HEAD requests for already-synced books.
5. Atomic synchronization marking outbox events as PROCESSED.
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select, text

from curiokraft_book.data.base import SyncStatus
from curiokraft_book.data.hybrid_store import HybridDataStore, get_data_store
from curiokraft_book.data.models import (
    BookModel,
    MediaAssetModel,
    OutboxEventModel,
    PageModel,
    PromptModel,
)
from curiokraft_book.data.object_storage import S3StorageBackend
from curiokraft_book.data.postgres_store import SQLDatabaseManager

logger = logging.getLogger("curiokraft.promoter")


class PromotionReport(BaseModel):
    """Detailed summary of a book promotion run."""

    book_slug: str
    book_title: str = ""
    pushed_books: int = 0
    pushed_pages: int = 0
    pushed_prompts: int = 0
    pushed_assets: int = 0
    bytes_uploaded: int = 0
    skipped_assets_reused: int = 0
    dry_run: bool = False
    success: bool = True
    errors: list[str] = Field(default_factory=list)


class CloudPromoter:
    """Manages incremental, cost-effective promotion of local books to Neon and Backblaze B2."""

    def __init__(
        self,
        local_store: HybridDataStore | None = None,
        cloud_db_url: str | None = None,
        cloud_storage: S3StorageBackend | None = None,
    ):
        self.local_store = local_store or get_data_store()
        self.cloud_db_url = (
            cloud_db_url
            or os.environ.get("CLOUD_DATABASE_URL")
            or os.environ.get("REMOTE_DATABASE_URL")
        )
        self.cloud_db_mgr: SQLDatabaseManager | None = None
        if self.cloud_db_url:
            try:
                self.cloud_db_mgr = SQLDatabaseManager(self.cloud_db_url)
            except Exception as e:
                logger.warning(f"Could not connect to cloud database: {e}")

        # Cloud Object Storage (Backblaze B2)
        self.cloud_storage = cloud_storage
        bucket = os.environ.get("CLOUD_S3_BUCKET_NAME") or os.environ.get("S3_BUCKET_NAME", "curiokraft-assets")
        endpoint = os.environ.get("CLOUD_S3_ENDPOINT_URL") or os.environ.get("S3_ENDPOINT_URL")
        key_id = os.environ.get("CLOUD_S3_ACCESS_KEY_ID") or os.environ.get("S3_ACCESS_KEY_ID")
        secret_key = os.environ.get("CLOUD_S3_SECRET_ACCESS_KEY") or os.environ.get("S3_SECRET_ACCESS_KEY")
        region = os.environ.get("CLOUD_S3_REGION") or os.environ.get("S3_REGION", "us-east-005")

        if not self.cloud_storage and (endpoint or key_id):
            try:
                self.cloud_storage = S3StorageBackend(
                    bucket_name=bucket,
                    endpoint_url=endpoint,
                    access_key_id=key_id,
                    secret_access_key=secret_key,
                    region_name=region,
                )
            except Exception as e:
                logger.warning(f"Could not connect to cloud object storage: {e}")

    def is_cloud_configured(self) -> bool:
        """Check if cloud targets are configured."""
        return self.cloud_db_mgr is not None and self.cloud_storage is not None

    def get_catalog_diff(self) -> dict[str, Any]:
        """Compare local catalog with cloud catalog to identify pending books and pages.

        Executes in O(1) batch database queries with zero object storage calls.
        Scales effortlessly to hundreds of books without linear network latency.
        """
        if not self.cloud_db_mgr:
            raise RuntimeError("Cloud database connection is not configured.")

        local_books = self.local_store.books.list_books()

        # Batch count local pages per book in a single query
        with self.local_store.db_mgr.session() as local_s:
            local_page_counts = dict(
                local_s.execute(
                    select(PageModel.book_id, func.count(PageModel.id)).group_by(PageModel.book_id)
                ).all()
            )

        # Batch fetch all cloud books and page counts from Neon in a single session
        with self.cloud_db_mgr.session() as cloud_s:
            cloud_books = cloud_s.scalars(select(BookModel)).all()
            cloud_slug_map = {b.slug: b for b in cloud_books}
            cloud_page_counts = dict(
                cloud_s.execute(
                    select(PageModel.book_id, func.count(PageModel.id)).group_by(PageModel.book_id)
                ).all()
            )

        unpromoted_books = []
        in_sync_books = []
        partial_books = []

        for lb in local_books:
            if lb.slug not in cloud_slug_map:
                unpromoted_books.append(lb)
            else:
                cb = cloud_slug_map[lb.slug]
                l_cnt = local_page_counts.get(lb.id, 0)
                c_cnt = cloud_page_counts.get(cb.id, 0)
                if l_cnt != c_cnt:
                    partial_books.append((lb, l_cnt, c_cnt))
                else:
                    in_sync_books.append(lb)

        return {
            "local_total": len(local_books),
            "cloud_total": len(cloud_slug_map),
            "unpromoted": unpromoted_books,
            "in_sync": in_sync_books,
            "partial": partial_books,
        }

    def promote_book(
        self,
        slug: str,
        dry_run: bool = False,
        force_upload: bool = False,
    ) -> PromotionReport:
        """Promote a single book by slug to Neon and Backblaze B2.

        Uses batch queries for entities and Content-Addressable Storage (CAS) hash
        lookup in Neon to avoid billable S3 HEAD requests on Backblaze B2.
        """
        report = PromotionReport(book_slug=slug, dry_run=dry_run)

        if not self.cloud_db_mgr:
            report.errors.append("Cloud database (Neon) not configured or unreachable.")
            report.success = False
            return report

        if not self.cloud_storage:
            report.errors.append("Cloud object storage (Backblaze B2) not configured or unreachable.")
            report.success = False
            return report

        local_book = self.local_store.books.get_by_slug(slug)
        if not local_book:
            report.errors.append(f"Book with slug '{slug}' not found in local database.")
            report.success = False
            return report

        report.book_title = local_book.title
        logger.info(f"Promoting book '{local_book.title}' ({slug}) to cloud (dry_run={dry_run})...")

        # 1-4. Execute all Neon operations inside a single, unified database transaction
        with self.cloud_db_mgr.session() as cloud_s:
            # 1. Upsert Book Entity in Neon
            cloud_b = cloud_s.scalars(select(BookModel).where(BookModel.slug == slug)).first()
            book_data = local_book.model_dump()
            book_data["sync_status"] = SyncStatus.SYNCED.value
            book_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            if not dry_run:
                if cloud_b:
                    for k, v in book_data.items():
                        if k != "id":
                            setattr(cloud_b, k, v)
                    remote_book_id = cloud_b.id
                else:
                    new_b = BookModel(**book_data)
                    cloud_s.add(new_b)
                    cloud_s.flush()
                    remote_book_id = new_b.id
                report.pushed_books += 1
            else:
                remote_book_id = cloud_b.id if cloud_b else local_book.id

            # 2. Promote Pages (Batch Upsert)
            local_pages = self.local_store.pages.get_pages_for_book(local_book.id)
            existing_pages = {
                p.page_id: p
                for p in cloud_s.scalars(
                    select(PageModel).where(PageModel.book_id == remote_book_id)
                ).all()
            }
            for p in local_pages:
                p_data = p.model_dump()
                p_data["book_id"] = remote_book_id
                p_data["sync_status"] = SyncStatus.SYNCED.value
                p_data["updated_at"] = datetime.now(timezone.utc).isoformat()

                if not dry_run:
                    if p.page_id in existing_pages:
                        existing_p = existing_pages[p.page_id]
                        for k, v in p_data.items():
                            if k != "id":
                                setattr(existing_p, k, v)
                    else:
                        cloud_s.add(PageModel(**p_data))
                report.pushed_pages += 1

            # 3. Promote Prompts (Batch Upsert)
            local_prompts = self.local_store.prompts.list_prompts_for_book(local_book.id)
            existing_prompts = {
                (pr.page_id, pr.prompt_type): pr
                for pr in cloud_s.scalars(
                    select(PromptModel).where(PromptModel.book_id == remote_book_id)
                ).all()
            }
            for pr in local_prompts:
                pr_data = pr.model_dump()
                pr_data["book_id"] = remote_book_id
                pr_data["sync_status"] = SyncStatus.SYNCED.value

                if not dry_run:
                    key = (pr.page_id, pr.prompt_type)
                    if key in existing_prompts:
                        existing_pr = existing_prompts[key]
                        if not existing_pr.is_locked:
                            for k, v in pr_data.items():
                                if k != "id":
                                    setattr(existing_pr, k, v)
                    else:
                        cloud_s.add(PromptModel(**pr_data))
                report.pushed_prompts += 1

            # 4. Promote Media Assets (CAS Deduplication & Backblaze B2 Upload)
            local_assets = self.local_store.assets.list_assets_for_book(local_book.id)
            remote_assets = cloud_s.scalars(
                select(MediaAssetModel).where(MediaAssetModel.book_id == remote_book_id)
            ).all()
            known_cloud_hashes = {a.sha256_hash for a in remote_assets if a.sha256_hash}
            existing_remote_by_id = {a.id: a for a in remote_assets}

            for a in local_assets:
                clean_key = a.storage_key.replace(f"s3://{self.cloud_storage.bucket_name}/", "").lstrip("/")

                # Fast path: If hash is already known in Neon and not force_upload,
                # the binary already exists in Backblaze B2. No billable S3 HEAD query needed!
                if not force_upload and a.sha256_hash and a.sha256_hash in known_cloud_hashes:
                    report.skipped_assets_reused += 1
                else:
                    # Upload binary from local storage backend to Backblaze B2
                    if not dry_run:
                        raw_bytes = None
                        try:
                            raw_bytes = self.local_store.storage.get_bytes(a.storage_key)
                        except Exception as ex:
                            logger.debug(f"Local storage fetch failed for {a.storage_key}: {ex}")

                        if raw_bytes:
                            actual_hash = hashlib.sha256(raw_bytes).hexdigest()
                            if a.sha256_hash and actual_hash != a.sha256_hash:
                                report.errors.append(f"Hash mismatch on {clean_key}: {actual_hash} != {a.sha256_hash}")
                                continue

                            guess_type, _ = mimetypes.guess_type(clean_key)
                            content_type = guess_type or "application/octet-stream"

                            self.cloud_storage.s3_client.put_object(
                                Bucket=self.cloud_storage.bucket_name,
                                Key=clean_key,
                                Body=raw_bytes,
                                ContentType=content_type,
                            )
                            report.bytes_uploaded += len(raw_bytes)
                            known_cloud_hashes.add(actual_hash)
                        else:
                            # Try reading from disk fallback if local storage did not find bytes
                            cand_disk = Path(clean_key)
                            if cand_disk.exists():
                                self.cloud_storage.upload_file(str(cand_disk), clean_key)
                                report.bytes_uploaded += cand_disk.stat().st_size
                                if a.sha256_hash:
                                    known_cloud_hashes.add(a.sha256_hash)
                            else:
                                report.errors.append(f"Cannot locate source binary for {clean_key}")
                                continue

                # Upsert asset record in Neon
                if not dry_run:
                    a_data = a.model_dump()
                    a_data["book_id"] = remote_book_id
                    a_data["sync_status"] = SyncStatus.SYNCED.value
                    if a.id in existing_remote_by_id:
                        existing_remote = existing_remote_by_id[a.id]
                        for k, v in a_data.items():
                            if k != "id":
                                setattr(existing_remote, k, v)
                    else:
                        cloud_s.add(MediaAssetModel(**a_data))

                report.pushed_assets += 1

            # 5. Mark cloud outbox events for this book as PROCESSED
            if not dry_run:
                now_iso = datetime.now(timezone.utc).isoformat()
                cloud_s.execute(
                    text(
                        """
                        UPDATE sync_outbox 
                        SET status = 'PROCESSED', processed_at = :now 
                        WHERE status = 'PENDING' AND (
                            entity_id = :book_id OR entity_id LIKE :book_prefix
                        );
                        """
                    ),
                    {"now": now_iso, "book_id": remote_book_id, "book_prefix": f"{remote_book_id}:%"},
                )

        # 6. Mark local database outbox events as PROCESSED
        if not dry_run:
            now_iso = datetime.now(timezone.utc).isoformat()
            try:
                with self.local_store.db_mgr.session() as local_s:
                    local_s.execute(
                        text(
                            """
                            UPDATE sync_outbox 
                            SET status = 'PROCESSED', processed_at = :now 
                            WHERE status = 'PENDING' AND (
                                entity_id = :book_id OR entity_id LIKE :book_prefix
                            );
                            """
                        ),
                        {"now": now_iso, "book_id": local_book.id, "book_prefix": f"{local_book.id}:%"},
                    )
                    local_book.sync_status = SyncStatus.SYNCED
                    self.local_store.books.save(local_book)
            except Exception as e:
                logger.warning(f"Could not update local outbox (docker may be offline): {e}")

        logger.info(
            f"Promotion finished for '{slug}': {report.pushed_pages} pages, "
            f"{report.pushed_assets} assets ({report.bytes_uploaded / (1024*1024):.1f} MB uploaded). "
            f"Success={report.success}."
        )
        return report

    def promote_all_pending(
        self,
        dry_run: bool = False,
        force_upload: bool = False,
    ) -> list[PromotionReport]:
        """Promote all un-promoted books or books with pending changes in order."""
        diff = self.get_catalog_diff()
        reports = []
        targets = diff["unpromoted"] + [b for b, _, _ in diff["partial"]]

        for book in targets:
            rep = self.promote_book(slug=book.slug, dry_run=dry_run, force_upload=force_upload)
            reports.append(rep)

        return reports
