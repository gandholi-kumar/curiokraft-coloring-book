"""SQLAlchemy-based concrete repository implementation for PostgreSQL and SQLite.

Supports Neon, Supabase, local Docker PostgreSQL, and offline SQLite.
Handles automatic table creation, upsert operations, and connection pooling.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from curiokraft_book.data.base import (
    AssetRepository,
    BookRecord,
    BookRepository,
    LogRecord,
    LogRepository,
    MediaAssetRecord,
    PageRecord,
    PageRepository,
    PromptRecord,
    PromptRepository,
)
from curiokraft_book.data.models import (
    Base,
    BookModel,
    LogModel,
    MediaAssetModel,
    OutboxEventModel,
    PageModel,
    PromptModel,
)

logger = logging.getLogger("curiokraft.db")


class SQLDatabaseManager:
    """Manages database connection pool and schema lifecycle."""

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or os.environ.get("DATABASE_URL") or "sqlite:///output/curiokraft.db"

        # Normalize postgres:// to postgresql+psycopg:// if needed
        if self.db_url.startswith("postgres://"):
            self.db_url = self.db_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif self.db_url.startswith("postgresql://") and "+psycopg" not in self.db_url:
            self.db_url = self.db_url.replace("postgresql://", "postgresql+psycopg://", 1)

        connect_args = {}
        if self.db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            # Ensure parent directory exists for SQLite file
            db_path = self.db_url.replace("sqlite:///", "")
            if db_path and db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            self.db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.init_db()

    def init_db(self) -> None:
        """Create tables if they do not already exist and ensure schema compatibility."""
        try:
            Base.metadata.create_all(self.engine)
            if self.engine.dialect.name == "postgresql":
                with self.engine.connect() as conn:
                    conn.execute(
                        text(
                            """
                            ALTER TABLE sync_outbox ALTER COLUMN id TYPE VARCHAR(128);
                            ALTER TABLE sync_outbox ALTER COLUMN entity_id TYPE VARCHAR(128);
                            ALTER TABLE sync_outbox ALTER COLUMN created_at TYPE VARCHAR(64);
                            ALTER TABLE sync_outbox ALTER COLUMN processed_at TYPE VARCHAR(64);
                            ALTER TABLE books ALTER COLUMN created_at TYPE VARCHAR(64);
                            ALTER TABLE books ALTER COLUMN updated_at TYPE VARCHAR(64);
                            ALTER TABLE pages ALTER COLUMN created_at TYPE VARCHAR(64);
                            ALTER TABLE pages ALTER COLUMN updated_at TYPE VARCHAR(64);
                            ALTER TABLE pages ALTER COLUMN last_updated TYPE VARCHAR(64);
                            ALTER TABLE prompts ALTER COLUMN created_at TYPE VARCHAR(64);
                            ALTER TABLE media_assets ALTER COLUMN created_at TYPE VARCHAR(64);
                            ALTER TABLE execution_logs ALTER COLUMN timestamp TYPE VARCHAR(64);
                            """
                        )
                    )
                    conn.commit()
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional session scope."""
        sess: Session = self.session_factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()


class SQLBookRepository(BookRepository):
    """SQL repository for books."""

    def __init__(self, db_mgr: SQLDatabaseManager):
        self.db_mgr = db_mgr

    def get_by_id(self, book_id: str) -> BookRecord | None:
        with self.db_mgr.session() as s:
            m = s.get(BookModel, book_id)
            if not m:
                return None
            return BookRecord(**{k: getattr(m, k) for k in BookRecord.model_fields})

    def get_by_slug(self, slug: str) -> BookRecord | None:
        with self.db_mgr.session() as s:
            stmt = select(BookModel).where(BookModel.slug == slug)
            m = s.scalars(stmt).first()
            if not m:
                return None
            return BookRecord(**{k: getattr(m, k) for k in BookRecord.model_fields})

    def save(self, book: BookRecord) -> BookRecord:
        with self.db_mgr.session() as s:
            existing = s.get(BookModel, book.id)
            book.updated_at = datetime.now(timezone.utc).isoformat()
            data = book.model_dump()
            data["sync_status"] = book.sync_status.value

            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                existing.version += 1
            else:
                new_m = BookModel(**data)
                s.add(new_m)

            # Record outbox event for sync
            outbox = OutboxEventModel(
                id=f"outbox_book_{book.id}_{uuid4().hex[:12]}",
                entity_type="book",
                entity_id=book.id,
                operation="UPDATE" if existing else "INSERT",
                payload=data,
            )
            s.add(outbox)

        return book

    def list_books(self, tenant_id: str = "default_tenant") -> list[BookRecord]:
        with self.db_mgr.session() as s:
            stmt = select(BookModel).where(BookModel.tenant_id == tenant_id)
            models = s.scalars(stmt).all()
            return [BookRecord(**{k: getattr(m, k) for k in BookRecord.model_fields}) for m in models]


class SQLPageRepository(PageRepository):
    """SQL repository for book pages."""

    def __init__(self, db_mgr: SQLDatabaseManager):
        self.db_mgr = db_mgr

    def get_page(self, book_id: str, page_id: str) -> PageRecord | None:
        with self.db_mgr.session() as s:
            stmt = select(PageModel).where(PageModel.book_id == book_id, PageModel.page_id == page_id)
            m = s.scalars(stmt).first()
            if not m:
                return None
            return PageRecord(**{k: getattr(m, k) for k in PageRecord.model_fields})

    def get_pages_for_book(self, book_id: str) -> list[PageRecord]:
        with self.db_mgr.session() as s:
            stmt = select(PageModel).where(PageModel.book_id == book_id).order_by(PageModel.page_number)
            models = s.scalars(stmt).all()
            return [PageRecord(**{k: getattr(m, k) for k in PageRecord.model_fields}) for m in models]

    def save_page(self, page: PageRecord) -> PageRecord:
        with self.db_mgr.session() as s:
            stmt = select(PageModel).where(PageModel.book_id == page.book_id, PageModel.page_id == page.page_id)
            existing = s.scalars(stmt).first()

            page.updated_at = datetime.now(timezone.utc).isoformat()
            data = page.model_dump()
            data["sync_status"] = page.sync_status.value

            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                existing.version += 1
            else:
                new_m = PageModel(**data)
                s.add(new_m)

            outbox = OutboxEventModel(
                id=f"outbox_page_{page.page_id}_{uuid4().hex[:12]}",
                entity_type="page",
                entity_id=f"{page.book_id}:{page.page_id}",
                operation="UPDATE" if existing else "INSERT",
                payload=data,
            )
            s.add(outbox)

        return page

    def bulk_save_pages(self, pages: list[PageRecord]) -> None:
        for p in pages:
            self.save_page(p)

    def find_by_canonical(self, canonical_object: str) -> list[PageRecord]:
        with self.db_mgr.session() as s:
            stmt = (
                select(PageModel)
                .where(func.lower(PageModel.canonical_object) == canonical_object.strip().lower())
                .order_by(PageModel.updated_at.desc())
            )
            models = s.scalars(stmt).all()
            return [PageRecord(**{k: getattr(m, k) for k in PageRecord.model_fields}) for m in models]


class SQLPromptRepository(PromptRepository):
    """SQL repository for generation prompts."""

    def __init__(self, db_mgr: SQLDatabaseManager):
        self.db_mgr = db_mgr

    def get_prompt(self, book_id: str, page_id: str | None, prompt_type: str) -> PromptRecord | None:
        with self.db_mgr.session() as s:
            stmt = select(PromptModel).where(
                PromptModel.book_id == book_id,
                PromptModel.page_id == page_id,
                PromptModel.prompt_type == prompt_type,
            )
            m = s.scalars(stmt).first()
            if not m:
                return None
            return PromptRecord(**{k: getattr(m, k) for k in PromptRecord.model_fields})

    def save_prompt(self, prompt: PromptRecord) -> PromptRecord:
        with self.db_mgr.session() as s:
            existing = s.get(PromptModel, prompt.id)
            data = prompt.model_dump()
            data["sync_status"] = prompt.sync_status.value

            if existing:
                if existing.is_locked:
                    logger.warning(f"Prompt {prompt.id} is locked; skipping overwrite.")
                    return prompt
                for k, v in data.items():
                    setattr(existing, k, v)
                existing.version += 1
            else:
                s.add(PromptModel(**data))

            outbox = OutboxEventModel(
                id=f"outbox_prompt_{prompt.id}_{uuid4().hex[:12]}",
                entity_type="prompt",
                entity_id=prompt.id,
                operation="UPDATE" if existing else "INSERT",
                payload=data,
            )
            s.add(outbox)

        return prompt

    def list_prompts_for_book(self, book_id: str) -> list[PromptRecord]:
        with self.db_mgr.session() as s:
            stmt = select(PromptModel).where(PromptModel.book_id == book_id)
            models = s.scalars(stmt).all()
            return [PromptRecord(**{k: getattr(m, k) for k in PromptRecord.model_fields}) for m in models]


class SQLAssetRepository(AssetRepository):
    """SQL repository for media asset metadata and content-addressable hash lookups."""

    def __init__(self, db_mgr: SQLDatabaseManager):
        self.db_mgr = db_mgr

    def get_asset(self, asset_id: str) -> MediaAssetRecord | None:
        with self.db_mgr.session() as s:
            m = s.get(MediaAssetModel, asset_id)
            if not m:
                return None
            return MediaAssetRecord(**{k: getattr(m, k) for k in MediaAssetRecord.model_fields})

    def find_by_hash(self, sha256_hash: str) -> MediaAssetRecord | None:
        with self.db_mgr.session() as s:
            stmt = select(MediaAssetModel).where(MediaAssetModel.sha256_hash == sha256_hash)
            m = s.scalars(stmt).first()
            if not m:
                return None
            return MediaAssetRecord(**{k: getattr(m, k) for k in MediaAssetRecord.model_fields})

    def save_asset(self, asset: MediaAssetRecord) -> MediaAssetRecord:
        with self.db_mgr.session() as s:
            existing = s.get(MediaAssetModel, asset.id)
            data = asset.model_dump()
            data["sync_status"] = asset.sync_status.value

            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                s.add(MediaAssetModel(**data))

            outbox = OutboxEventModel(
                id=f"outbox_asset_{asset.id}_{uuid4().hex[:12]}",
                entity_type="media_asset",
                entity_id=asset.id,
                operation="UPDATE" if existing else "INSERT",
                payload=data,
            )
            s.add(outbox)

        return asset

    def list_assets_for_page(self, book_id: str, page_id: str) -> list[MediaAssetRecord]:
        with self.db_mgr.session() as s:
            stmt = select(MediaAssetModel).where(
                MediaAssetModel.book_id == book_id, MediaAssetModel.page_id == page_id
            )
            models = s.scalars(stmt).all()
            return [MediaAssetRecord(**{k: getattr(m, k) for k in MediaAssetRecord.model_fields}) for m in models]

    def list_assets_for_book(self, book_id: str) -> list[MediaAssetRecord]:
        with self.db_mgr.session() as s:
            stmt = select(MediaAssetModel).where(MediaAssetModel.book_id == book_id)
            models = s.scalars(stmt).all()
            return [MediaAssetRecord(**{k: getattr(m, k) for k in MediaAssetRecord.model_fields}) for m in models]


class SQLLogRepository(LogRepository):
    """SQL repository for audit logs."""

    def __init__(self, db_mgr: SQLDatabaseManager):
        self.db_mgr = db_mgr

    def log(self, record: LogRecord) -> None:
        try:
            with self.db_mgr.session() as s:
                s.add(LogModel(**record.model_dump()))
        except Exception as e:
            logger.debug(f"Silent log failure: {e}")
