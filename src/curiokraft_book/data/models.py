"""SQLAlchemy ORM models for CurioKraft relational data persistence.

Engineered to be 100% dialect-agnostic: functions identically on SQLite
(for offline No-Docker laptop workflows) and PostgreSQL (Neon/Supabase production).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class with JSON serialization helper."""

    pass


class BookModel(Base):
    """Database representation of a coloring book project."""

    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default_tenant", index=True)
    slug: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(255))
    subtitle: Mapped[str] = mapped_column(String(255), default="")
    volume: Mapped[str] = mapped_column(String(32), default="vol1")
    imprint: Mapped[str] = mapped_column(String(128), default="CurioKraft Publications")
    target_audience: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    layout: Mapped[str] = mapped_column(String(32), default="single_sided")
    bleed: Mapped[bool] = mapped_column(Boolean, default=False)
    trim_width_in: Mapped[float] = mapped_column(Float, default=8.5)
    trim_height_in: Mapped[float] = mapped_column(Float, default=11.0)
    spine_width_in: Mapped[float] = mapped_column(Float, default=0.248)
    page_count: Mapped[int] = mapped_column(Integer, default=110)
    visual_style: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    sync_status: Mapped[str] = mapped_column(String(32), default="pending_upload", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(
        String(64), default=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Mapped[str] = mapped_column(
        String(64), default=lambda: datetime.now(timezone.utc).isoformat()
    )

    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_tenant_book_slug"),)

    pages: Mapped[list[PageModel]] = relationship(
        "PageModel", back_populates="book", cascade="all, delete-orphan"
    )


class PageModel(Base):
    """Database representation of an individual page within a book."""

    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    page_id: Mapped[str] = mapped_column(String(32), index=True)  # e.g., P001
    page_number: Mapped[int] = mapped_column(Integer, index=True)
    section: Mapped[str] = mapped_column(String(64), default="General")
    canonical_object: Mapped[str] = mapped_column(String(128))
    display_label: Mapped[str] = mapped_column(String(128))
    page_type: Mapped[str] = mapped_column(String(32), default="coloring_page")
    cards: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    qa_score: Mapped[float] = mapped_column(Float, default=0.0)
    qa_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    violations: Mapped[list[str]] = mapped_column(JSON, default=list)
    positive_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rescued_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    composite_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(32), default="pending_upload", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    last_updated: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(
        String(64), default=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Mapped[str] = mapped_column(
        String(64), default=lambda: datetime.now(timezone.utc).isoformat()
    )

    __table_args__ = (
        UniqueConstraint("book_id", "page_id", name="uq_book_page_id"),
        Index("idx_page_book_num", "book_id", "page_number"),
    )

    book: Mapped[BookModel] = relationship("BookModel", back_populates="pages")


class PromptModel(Base):
    """Database representation of an AI generation prompt."""

    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    page_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    prompt_type: Mapped[str] = mapped_column(String(32), default="interior_page")
    positive_prompt: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    temperature: Mapped[float] = mapped_column(Float, default=0.5)
    top_p: Mapped[float] = mapped_column(Float, default=0.95)
    aspect_ratio: Mapped[str] = mapped_column(String(16), default="3:4")
    preset_name: Mapped[str] = mapped_column(
        String(128), default="CurioKraft - Interior Coloring Pages"
    )
    chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_status: Mapped[str] = mapped_column(String(32), default="pending_upload", index=True)
    created_at: Mapped[str] = mapped_column(
        String(64), default=lambda: datetime.now(timezone.utc).isoformat()
    )


class MediaAssetModel(Base):
    """Database representation of an image or PDF artifact with content-addressable hash."""

    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    page_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    asset_type: Mapped[str] = mapped_column(
        String(32)
    )  # raw_image, composite_master, cover_png, etc.
    storage_backend: Mapped[str] = mapped_column(String(32), default="local_disk")
    storage_key: Mapped[str] = mapped_column(String(512), index=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True)
    width_px: Mapped[int] = mapped_column(Integer, default=2550)
    height_px: Mapped[int] = mapped_column(Integer, default=3300)
    dpi: Mapped[int] = mapped_column(Integer, default=300)
    color_mode: Mapped[str] = mapped_column(String(16), default="L")
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str] = mapped_column(String(64), default="image/png")
    sync_status: Mapped[str] = mapped_column(String(32), default="pending_upload", index=True)
    created_at: Mapped[str] = mapped_column(
        String(64), default=lambda: datetime.now(timezone.utc).isoformat()
    )


class LogModel(Base):
    """Database representation of an execution log entry."""

    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    book_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[str] = mapped_column(String(16), default="INFO")
    component: Mapped[str] = mapped_column(String(64), default="pipeline")
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[str] = mapped_column(
        String(64), default=lambda: datetime.now(timezone.utc).isoformat()
    )


class OutboxEventModel(Base):
    """Outbox pattern table for offline-to-cloud change data capture (CDC)."""

    __tablename__ = "sync_outbox"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32))  # book, page, prompt, media_asset
    entity_id: Mapped[str] = mapped_column(String(128))
    operation: Mapped[str] = mapped_column(String(16))  # INSERT, UPDATE, DELETE
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    created_at: Mapped[str] = mapped_column(
        String(64), default=lambda: datetime.now(timezone.utc).isoformat()
    )
    processed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
