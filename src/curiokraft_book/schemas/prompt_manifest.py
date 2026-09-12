"""Pydantic Schema for CurioKraft Prompt Manifest (JSON export).

Defines strongly-typed data structures for automated image generation engines
like Playwright to consume without missing values or ambiguity.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class PromptDefaults(BaseModel):
    """Global default parameters for Google AI Studio generation."""

    aspect_ratio: str = Field(default="3:4", description="Aspect ratio (e.g. 3:4 portrait)")
    output_format: str = Field(default="Images only", description="Google AI Studio output format")
    top_p: float = Field(default=0.95, description="Top P sampling parameter")


class PromptItem(BaseModel):
    """Individual prompt instruction ready for automated generation."""

    id: str = Field(
        ..., description="Unique prompt identifier (e.g. COVER_FRONT, COVER_BACK, P001, P006)"
    )
    page_number: int | None = Field(
        default=None, description="Page number for interior pages, null for covers"
    )
    label: str = Field(..., description="Descriptive title or object name")
    type: Literal["front_cover", "back_cover", "interior_page", "special_asset"] = Field(
        ..., description="Asset type category"
    )
    section: str = Field(
        default="General",
        description="Book section (e.g. Covers, A-Z Alphabet, Fruits & Vegetables)",
    )
    drop_target: str = Field(
        ...,
        description="Target file path relative to publications root, e.g. inbox/raw_pages/raw_p006_banana.png",
    )
    preset_name: Literal[
        "CurioKraft - Interior Coloring Pages", "CurioKraft - Cover Art Master"
    ] = Field(..., description="Google AI Studio saved System Instructions preset name to select")
    aspect_ratio: str = Field(default="3:4", description="Aspect ratio for AI Studio sidebar")
    output_format: str = Field(
        default="Images only", description="Output format for AI Studio sidebar"
    )
    temperature: float = Field(
        ..., description="Sampling temperature (0.5 for interior line art, 0.9 for covers)"
    )
    top_p: float = Field(default=0.95, description="Top P parameter")
    positive_prompt: str = Field(..., description="Full synthesized positive prompt text")
    negative_prompt: str = Field(..., description="Full negative prompt text")
    chat_id: str | None = Field(
        default=None, description="Captured Google AI Studio session/chat ID from URL"
    )
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"] = Field(
        default="pending", description="Execution status for batch orchestration"
    )
    error: str | None = Field(default=None, description="Error message if generation failed")


class CurioKraftPromptManifest(BaseModel):
    """Complete exported manifest containing all book illustration prompts."""

    manifest_version: str = Field(default="1.0.0", description="Schema version")
    book_title: str = Field(..., description="Title of the book")
    book_id: str = Field(..., description="Unique identifier for the book/volume")
    volume: str = Field(default="vol1", description="Volume identifier, e.g. vol1, vol2")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 generation timestamp",
    )
    total_prompts: int = Field(..., description="Total count of prompts in this manifest")
    defaults: PromptDefaults = Field(default_factory=PromptDefaults, description="Default settings")
    prompts: list[PromptItem] = Field(default_factory=list, description="Array of prompt items")
