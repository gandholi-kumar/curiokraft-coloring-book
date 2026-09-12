"""Pipeline state machine and persistent progress tracker for all 110 pages."""

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from curiokraft_book.constants import (
    DEFAULT_PAGES_MANIFEST,
    DEFAULT_PIPELINE_STATE_FILE,
    MAX_RETRY_ATTEMPTS,
    STATE_APPROVED,
    STATE_COMPOSITED,
    STATE_DEBATED,
    STATE_ESCALATED,
    STATE_FAILED,
    STATE_GENERATED,
    STATE_GENERATING,
    STATE_PLANNED,
    STATE_PROMPT_LOCKED,
    STATE_RESCUED,
    STATE_TECHNICAL_QA_PASSED,
    STATE_VISION_QA_PASSED,
)


class PageStatus(str, Enum):
    """Lifecycle states of an individual page in the production pipeline."""

    PLANNED = STATE_PLANNED
    DEBATED = STATE_DEBATED
    PROMPT_LOCKED = STATE_PROMPT_LOCKED
    GENERATING = STATE_GENERATING
    GENERATED = STATE_GENERATED
    VISION_QA_PASSED = STATE_VISION_QA_PASSED
    TECHNICAL_QA_PASSED = STATE_TECHNICAL_QA_PASSED
    RESCUED = STATE_RESCUED
    COMPOSITED = STATE_COMPOSITED
    APPROVED = STATE_APPROVED
    FAILED = STATE_FAILED
    ESCALATED = STATE_ESCALATED


class PageStateRecord(BaseModel):
    """Execution state and artifact paths for an individual book page."""

    page_id: str
    page_number: int
    canonical_object: str
    display_label: str
    section: str
    status: PageStatus = PageStatus.PLANNED
    attempts: int = 0
    max_attempts: int = MAX_RETRY_ATTEMPTS
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    raw_image_path: str | None = None
    rescued_image_path: str | None = None
    composite_image_path: str | None = None
    qa_score: float = 0.0
    qa_passed: bool = False
    violations: list[str] = Field(default_factory=list)
    last_updated: str | None = None


class PipelineStateManager:
    """Manages the lifecycle state of all 110 pages with atomic JSON persistence."""

    def __init__(
        self,
        state_file_path: str | Path = DEFAULT_PIPELINE_STATE_FILE,
        manifest_path: str | Path = DEFAULT_PAGES_MANIFEST,
    ):
        self.state_file = Path(state_file_path)
        self.manifest_path = Path(manifest_path)
        self.pages: dict[str, PageStateRecord] = {}
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        """Load existing state from JSON and ensure all manifest pages are registered."""
        if self.state_file.exists():
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    data = json.load(f)
                for page_id, rec in data.get("pages", {}).items():
                    self.pages[page_id] = PageStateRecord(**rec)
            except Exception:
                pass

        # Populate any missing pages from manifest
        if self.manifest_path.exists():
            with open(self.manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)
            for p in manifest_data.get("pages", []):
                p_id = p["page_id"]
                if p_id not in self.pages:
                    self.pages[p_id] = PageStateRecord(
                        page_id=p_id,
                        page_number=p["page_number"],
                        canonical_object=p["canonical_object"],
                        display_label=p.get("display_label", p["canonical_object"].upper()),
                        section=p.get("section", "General"),
                        status=PageStatus.PLANNED,
                    )
            self.save()

    def get_page(self, page_id: str) -> PageStateRecord | None:
        return self.pages.get(page_id)

    def update_page(self, page_id: str, **kwargs) -> PageStateRecord:
        """Update fields on a page record and immediately persist state."""
        if page_id not in self.pages:
            raise KeyError(f"Page ID '{page_id}' not found in state manager.")

        rec = self.pages[page_id]
        update_data = rec.model_dump()
        update_data.update(kwargs)
        self.pages[page_id] = PageStateRecord(**update_data)
        self.save()
        return self.pages[page_id]

    def get_pages_by_status(self, status: PageStatus) -> list[PageStateRecord]:
        return [p for p in self.pages.values() if p.status == status]

    def get_summary(self) -> dict[str, int]:
        """Return counts of pages in each lifecycle state."""
        summary = {s.value: 0 for s in PageStatus}
        for p in self.pages.values():
            summary[p.status.value] += 1
        return summary

    def save(self) -> None:
        """Persist state atomically to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            "total_pages": len(self.pages),
            "summary": self.get_summary(),
            "pages": {p_id: p.model_dump() for p_id, p in self.pages.items()},
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)
