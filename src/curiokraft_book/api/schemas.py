"""Pydantic request and response schemas for the CurioKraft Publishing Studio API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from curiokraft_book.constants import (
    CANVAS_DPI,
    DEFAULT_AGE_GROUPS,
    DEFAULT_TRIM_SIZES,
    DEFAULT_WORKFLOW_MODES,
    calculate_spine_width,
)
from curiokraft_book.schemas.prompt_manifest import PromptDefaults, PromptItem


# ------------------------------------------------------------------------------
# System & Health Schemas
# ------------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="ok", description="Overall service status")
    version: str = Field(..., description="CurioKraft software version")
    db_status: str = Field(..., description="Database connection status ('connected' or 'degraded')")
    storage_backend: str = Field(..., description="Active storage backend (e.g. local_disk, s3_r2, minio)")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )


class SystemConfigResponse(BaseModel):
    """Runtime system configurations and standard options for UI dropdowns."""

    version: str
    dpi: int = CANVAS_DPI
    default_trim_sizes: list[str] = Field(default_factory=lambda: DEFAULT_TRIM_SIZES)
    default_age_groups: list[str] = Field(default_factory=lambda: DEFAULT_AGE_GROUPS)
    workflow_modes: list[str] = Field(default_factory=lambda: DEFAULT_WORKFLOW_MODES)


# ------------------------------------------------------------------------------
# Book Schemas
# ------------------------------------------------------------------------------


class BookCreateRequest(BaseModel):
    """Payload to initialize a new coloring book project."""

    title: str = Field(..., min_length=2, max_length=200, description="Book title")
    subtitle: str = Field(default="", max_length=300, description="Optional subtitle")
    slug: str | None = Field(default=None, description="Unique slug; auto-generated if omitted")
    volume: str = Field(default="vol1", description="Volume identifier, e.g. vol1, vol2")
    imprint: str = Field(default="CurioKraft Publications", description="Publishing imprint")
    target_audience: dict[str, Any] = Field(
        default_factory=lambda: {"age_range": "4-8", "category": "preschool_kindergarten"},
        description="Target audience metadata",
    )
    trim_width_in: float = Field(default=8.5, description="Trim width in inches")
    trim_height_in: float = Field(default=11.0, description="Trim height in inches")
    spine_width_in: float | None = Field(default=None, description="Calculated spine width")
    page_count: int = Field(default=110, ge=10, le=400, description="Total interior page count")
    bleed: bool = Field(default=False, description="Whether interior bleed is enabled")
    layout: str = Field(default="single_sided", description="Page layout (single_sided or double_sided)")
    visual_style: dict[str, Any] = Field(
        default_factory=lambda: {
            "style_preset": "bold_clean_line_art",
            "stroke_thickness": "heavy",
            "shading": "none",
        },
        description="Visual style guidelines",
    )


class BookResponse(BaseModel):
    """Serialized book entity returned to the frontend."""

    id: str
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
    sync_status: str = "pending_upload"
    version: int = 1
    created_at: str
    updated_at: str


class BookUpdateRequest(BaseModel):
    """Payload to update book configuration."""

    title: str | None = None
    subtitle: str | None = None
    trim_width_in: float | None = None
    trim_height_in: float | None = None
    page_count: int | None = None
    bleed: bool | None = None
    layout: str | None = None
    visual_style: dict[str, Any] | None = None
    target_audience: dict[str, Any] | None = None
    status: str | None = None


# ------------------------------------------------------------------------------
# Page Schemas
# ------------------------------------------------------------------------------


class PageResponse(BaseModel):
    """Serialized book page entity."""

    id: str
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
    sync_status: str = "pending_upload"
    version: int = 1
    created_at: str
    updated_at: str


# ------------------------------------------------------------------------------
# Prompt Schemas
# ------------------------------------------------------------------------------


class PromptSynthesizeRequest(BaseModel):
    """Request to synthesize illustration prompts via the multi-agent debate engine."""

    theme: str | None = Field(default=None, description="Optional theme override (e.g. 'Animals', 'Vehicles')")
    include_covers: bool = Field(default=True, description="Whether to include Front & Back cover prompts")
    include_special_pages: bool = Field(default=True, description="Whether to include Welcome & Certificate prompts")
    pages_csv_path: str | None = Field(default=None, description="Optional custom CSV manifest path")
    book_config_path: str | None = Field(default=None, description="Optional custom book YAML config path")


class PromptManifestResponse(BaseModel):
    """Prompt synthesis result manifest."""

    manifest_version: str = "1.0.0"
    book_title: str
    book_id: str
    volume: str = "vol1"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_prompts: int
    defaults: PromptDefaults = Field(default_factory=PromptDefaults)
    prompts: list[PromptItem] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Pipeline & Production Status Schemas
# ------------------------------------------------------------------------------


class PipelineStageStatus(BaseModel):
    """Status for an individual stage in the 6-stage wizard."""

    stage_id: str  # blueprint, prompts, ingestion, masters, preflight, kdp
    title: str
    status: Literal["pending", "in_progress", "completed", "failed", "warning"] = "pending"
    progress_percentage: float = 0.0
    completed_items: int = 0
    total_items: int = 0
    error_message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class BookProductionStatusResponse(BaseModel):
    """Aggregated status of all 6 production stages for a book."""

    book_id: str
    book_title: str
    overall_progress: float = 0.0
    active_stage: str = "blueprint"
    stages: list[PipelineStageStatus] = Field(default_factory=list)
    page_stats: dict[str, int] = Field(
        default_factory=lambda: {
            "total_pages": 0,
            "planned": 0,
            "inbox_received": 0,
            "rescued": 0,
            "qa_passed": 0,
            "composited": 0,
        }
    )


class TelemetryLogEvent(BaseModel):
    """Console telemetry log entry broadcast to the UI drawer."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    component: str = "pipeline"
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class IngestUploadResponse(BaseModel):
    """Result of raw image ingestion and rescue."""

    total_files: int
    matched_pages: int
    rescued_count: int
    unmatched_files: list[str] = Field(default_factory=list)
    processed_pages: list[PageResponse] = Field(default_factory=list)
    message: str = "Ingestion completed successfully"

