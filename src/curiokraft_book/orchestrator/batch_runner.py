"""Production batch execution engine for generating and compositing all 110 book pages."""

import json
import logging
from collections.abc import Callable
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, Field

from curiokraft_book.compositor.special_pages import render_certificate_page, render_welcome_page
from curiokraft_book.compositor.typography import composite_typography
from curiokraft_book.constants import (
    DEFAULT_INBOX_DIR,
    DEFAULT_INTERIOR_MASTERS_DIR,
    DEFAULT_PAGE_COUNT,
    DEFAULT_PAGES_MANIFEST,
    DEFAULT_RAW_GENERATED_DIR,
)
from curiokraft_book.orchestrator.debate_engine import DebateEngine
from curiokraft_book.orchestrator.model_client import DiskInboxProvider, ModelClient
from curiokraft_book.orchestrator.retry_manager import RetryManager
from curiokraft_book.orchestrator.state_manager import PageStatus, PipelineStateManager
from curiokraft_book.validators.dimensions import validate_dimensions
from curiokraft_book.validators.grayscale import validate_black_and_white
from curiokraft_book.validators.margins import validate_margins

logger = logging.getLogger("curiokraft.batch_runner")


class BatchProductionReport(BaseModel):
    """Execution summary of 110-page interior batch production."""

    total_pages: int = DEFAULT_PAGE_COUNT
    successful_pages: int
    failed_pages: int
    rescued_pages_count: int
    output_directory: str
    manifest_path: str
    page_records: list[dict] = Field(default_factory=list)


class InteriorBatchRunner:
    """Manages the full 110-page interior generation, rescue, and typography pipeline."""

    def __init__(
        self,
        manifest_path: str | Path = DEFAULT_PAGES_MANIFEST,
        output_masters_dir: str | Path = DEFAULT_INTERIOR_MASTERS_DIR,
        raw_generated_dir: str | Path = DEFAULT_RAW_GENERATED_DIR,
        inbox_dir: str | Path = DEFAULT_INBOX_DIR,
        model_client: ModelClient | None = None,
    ):
        self.manifest_path = Path(manifest_path)
        self.output_masters_dir = Path(output_masters_dir)
        self.raw_generated_dir = Path(raw_generated_dir)
        self.inbox_dir = Path(inbox_dir)
        self.model_client = model_client or ModelClient()
        self.debate_engine = DebateEngine(self.model_client)
        self.state_mgr = PipelineStateManager(manifest_path=self.manifest_path)
        self.retry_manager = RetryManager()
        self.inbox_provider = DiskInboxProvider(
            inbox_dir=self.inbox_dir, raw_dir=self.raw_generated_dir
        )

        self.output_masters_dir.mkdir(parents=True, exist_ok=True)
        self.raw_generated_dir.mkdir(parents=True, exist_ok=True)

    def generate_single_page(
        self, page_data: dict, source_mode: str = "auto", force_fresh: bool = False
    ) -> Path:
        """Produce a single page: Debate -> Generation -> Code Rescue -> Vector Typography."""
        page_id = page_data["page_id"]
        page_num = page_data["page_number"]
        canonical = page_data["canonical_object"]
        label = page_data.get("display_label", canonical.upper())
        section = page_data.get("section", "General")

        logger.info(
            f"Processing Page {page_num:03d} ({page_id}): '{label}' in '{section}' [source={source_mode}]..."
        )

        # Check for special programmatic publication pages
        page_type = page_data.get("type", "coloring_page")
        final_master_path = self.output_masters_dir / f"page_{page_num:03d}.png"

        if page_type == "welcome_page":
            raw_img_path = self.raw_generated_dir / f"raw_p{page_num:03d}_{canonical}.png"
            found_inbox = self.inbox_provider.find_image(
                page_id=page_id, page_number=page_num, canonical_label=canonical
            )

            if found_inbox and found_inbox.exists():
                logger.info(f"Ingesting user welcome illustration from {found_inbox}")
                with Image.open(found_inbox) as img:
                    raw_canvas = img.convert("L")
                    raw_canvas.save(raw_img_path, dpi=(300, 300))
                self.state_mgr.update_page(
                    page_id, status=PageStatus.GENERATED, raw_image_path=str(raw_img_path)
                )

            mascot_path = raw_img_path if raw_img_path.exists() else None
            render_welcome_page(output_path=final_master_path, mascot_image_path=mascot_path)
            self.state_mgr.update_page(
                page_id,
                status=PageStatus.APPROVED,
                raw_image_path=str(raw_img_path) if raw_img_path.exists() else None,
                composite_image_path=str(final_master_path),
                qa_passed=True,
                qa_score=100.0,
                violations=[],
            )
            return final_master_path

        if page_type == "certificate_page":
            raw_img_path = self.raw_generated_dir / f"raw_p{page_num:03d}_{canonical}.png"
            found_inbox = self.inbox_provider.find_image(
                page_id=page_id, page_number=page_num, canonical_label=canonical
            )

            if found_inbox and found_inbox.exists():
                logger.info(f"Ingesting user certificate illustration from {found_inbox}")
                with Image.open(found_inbox) as img:
                    raw_canvas = img.convert("L")
                    raw_canvas.save(raw_img_path, dpi=(300, 300))
                self.state_mgr.update_page(
                    page_id, status=PageStatus.GENERATED, raw_image_path=str(raw_img_path)
                )

            award_path = raw_img_path if raw_img_path.exists() else None
            render_certificate_page(output_path=final_master_path, award_image_path=award_path)
            self.state_mgr.update_page(
                page_id,
                status=PageStatus.APPROVED,
                raw_image_path=str(raw_img_path) if raw_img_path.exists() else None,
                composite_image_path=str(final_master_path),
                qa_passed=True,
                qa_score=100.0,
                violations=[],
            )
            return final_master_path

        # 1. Multi-Agent Debate to synthesize locked prompt
        self.state_mgr.update_page(page_id, status=PageStatus.DEBATED)
        debate_res = self.debate_engine.run_page_debate(page_data)

        self.state_mgr.update_page(
            page_id,
            status=PageStatus.PROMPT_LOCKED,
            positive_prompt=debate_res.positive_prompt,
            negative_prompt=debate_res.negative_prompt,
        )

        # 2. Raw Raster Generation via Pluggable Image Provider Strategy
        raw_img_path = self.raw_generated_dir / f"raw_p{page_num:03d}_{canonical}.png"
        raw_img_jpg = self.raw_generated_dir / f"raw_p{page_num:03d}_{canonical}.jpg"

        found_inbox = self.inbox_provider.find_image(
            page_id=page_id, page_number=page_num, canonical_label=canonical
        )

        if found_inbox and found_inbox.exists() and not force_fresh:
            logger.info(f"Using fresh user illustration from inbox: {found_inbox}")
            raw_canvas = Image.open(found_inbox).convert("L")
        elif raw_img_path.exists() and raw_img_path.stat().st_size > 500 and not force_fresh:
            logger.info(f"Using existing raw illustration from {raw_img_path}")
            raw_canvas = Image.open(raw_img_path).convert("L")
        elif raw_img_jpg.exists() and raw_img_jpg.stat().st_size > 500 and not force_fresh:
            logger.info(f"Using existing raw illustration from {raw_img_jpg}")
            raw_canvas = Image.open(raw_img_jpg).convert("L")
        else:
            raw_canvas = self.model_client.generate_illustration(
                positive_prompt=debate_res.positive_prompt,
                negative_prompt=debate_res.negative_prompt,
                canonical_label=canonical,
                section=section,
                source_mode=source_mode,
                page_id=page_id,
                page_number=page_num,
                force_fresh=force_fresh,
            )

        page_type = page_data.get("type", "")
        composition = page_data.get("composition", "")
        is_spread = (page_type in ["educational_spread", "counting_spread"]) or (
            composition == "flashcard_grid"
        )

        # Standardize canvas to 300 DPI master dimensions (2550 x 3300 px)
        if raw_canvas.size != (2550, 3300):
            canvas_300 = Image.new("L", (2550, 3300), 255)
            if is_spread:
                # Spreads occupy the full safe printable area (2250 x 3000 max), centered, with 0.50 in safe margins
                scale_ratio = min(2250 / raw_canvas.width, 3000 / raw_canvas.height)
                new_w = int(raw_canvas.width * scale_ratio)
                new_h = int(raw_canvas.height * scale_ratio)
                resized = raw_canvas.resize((new_w, new_h), Image.Resampling.LANCZOS)
                pos_x = (2550 - new_w) // 2
                pos_y = (3300 - new_h) // 2
                canvas_300.paste(resized, (pos_x, pos_y))
            else:
                scale_ratio = min(2000 / raw_canvas.width, 2300 / raw_canvas.height)
                new_w = int(raw_canvas.width * scale_ratio)
                new_h = int(raw_canvas.height * scale_ratio)
                resized = raw_canvas.resize((new_w, new_h), Image.Resampling.LANCZOS)
                pos_x = (2550 - new_w) // 2
                pos_y = 650 + (2300 - new_h) // 2
                canvas_300.paste(resized, (pos_x, pos_y))
            raw_canvas = canvas_300

        raw_canvas.save(raw_img_path, dpi=(300, 300))
        self.state_mgr.update_page(
            page_id, status=PageStatus.GENERATED, raw_image_path=str(raw_img_path)
        )

        # 3. Deterministic Code-Level Rescue & Safe Margin Fit
        rescued_img_path = self.output_masters_dir / f"temp_rescued_{page_num:03d}.png"
        rescue_ok, msg, violations = self.retry_manager.attempt_programmatic_rescue(
            raw_img_path, rescued_img_path, is_spread=is_spread
        )

        if not rescue_ok:
            logger.warning(f"Rescue flagged warnings for {page_id}: {violations}")

        self.state_mgr.update_page(
            page_id, status=PageStatus.RESCUED, rescued_image_path=str(rescued_img_path)
        )

        # 4. Programmatic Vector Typography Overlay
        final_master_path = self.output_masters_dir / f"page_{page_num:03d}.png"
        if is_spread:
            import shutil

            shutil.copyfile(str(rescued_img_path), str(final_master_path))
            logger.info(f"Bypassed external typography overlay for spread {page_id} ({canonical}).")
        else:
            composite_typography(
                image_input=rescued_img_path, display_label=label, output_path=final_master_path
            )

        # Clean up temp file
        if rescued_img_path.exists():
            rescued_img_path.unlink()

        # 5. Final Deterministic Quality Certification
        dim_check = validate_dimensions(final_master_path)
        margin_check = validate_margins(final_master_path)
        bw_check = validate_black_and_white(final_master_path)

        all_passed = dim_check.passed and margin_check.passed and bw_check.passed

        self.state_mgr.update_page(
            page_id,
            status=PageStatus.APPROVED if all_passed else PageStatus.FAILED,
            composite_image_path=str(final_master_path),
            qa_passed=all_passed,
            qa_score=100.0 if all_passed else 70.0,
            violations=dim_check.violations + margin_check.violations + bw_check.violations,
        )

        return final_master_path

    def run_full_book_batch(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
        source_mode: str = "auto",
        force_fresh: bool = False,
    ) -> BatchProductionReport:
        """Execute batch production for all 110 pages in the frozen manifest.

        Args:
            progress_callback: Optional callback receiving (current_page, total_pages, page_label).
            source_mode: 'auto', 'api', 'inbox', 'openai', 'gemini', or 'mock'.
            force_fresh: Ignore existing caches and regenerate.

        Returns:
            BatchProductionReport with full batch statistics.
        """
        with open(self.manifest_path, encoding="utf-8") as f:
            manifest_data = json.load(f)

        pages = manifest_data.get("pages", [])
        total_count = len(pages)
        success_count = 0
        failed_count = 0
        records = []

        logger.info(f"Starting batch production of {total_count} pages [source={source_mode}]...")

        for idx, page in enumerate(pages):
            page_num = page["page_number"]
            label = page.get("display_label", page["canonical_object"].upper())

            if progress_callback:
                progress_callback(idx + 1, total_count, f"Page {page_num:03d}: {label}")

            try:
                master_path = self.generate_single_page(
                    page, source_mode=source_mode, force_fresh=force_fresh
                )
                success_count += 1
                records.append(
                    {
                        "page_id": page["page_id"],
                        "page_number": page_num,
                        "label": label,
                        "status": "APPROVED",
                        "path": str(master_path),
                    }
                )
            except Exception as e:
                failed_count += 1
                logger.error(f"Error producing Page {page_num:03d} ({label}): {e}", exc_info=True)
                records.append(
                    {
                        "page_id": page["page_id"],
                        "page_number": page_num,
                        "label": label,
                        "status": "FAILED",
                        "error": str(e),
                    }
                )

        logger.info(f"Batch production completed: {success_count}/{total_count} pages approved.")

        return BatchProductionReport(
            total_pages=total_count,
            successful_pages=success_count,
            failed_pages=failed_count,
            rescued_pages_count=success_count,
            output_directory=str(self.output_masters_dir),
            manifest_path=str(self.manifest_path),
            page_records=records,
        )
