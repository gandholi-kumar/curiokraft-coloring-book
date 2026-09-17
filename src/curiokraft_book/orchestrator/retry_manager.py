"""Intelligent retry, prompt revision, and zero-waste failure escalation manager."""

import logging
from pathlib import Path

from pydantic import BaseModel

from curiokraft_book.constants import (
    HEADER_RESERVATION_IN,
    SAFE_BOTTOM_IN,
    SAFE_GUTTER_IN,
    SAFE_MARGIN_IN,
    SAFE_OUTSIDE_IN,
    TARGET_COVERAGE_RATIO,
    get_stroke_hierarchy_config,
)
from curiokraft_book.rescue.binarizer import rescue_binarize
from curiokraft_book.rescue.margin_fitter import fit_to_safe_margins
from curiokraft_book.validators.dimensions import validate_dimensions
from curiokraft_book.validators.grayscale import validate_black_and_white
from curiokraft_book.validators.margins import validate_margins

logger = logging.getLogger("curiokraft.retry_manager")


class RecoveryAction(BaseModel):
    """Action taken to recover a failing page."""

    action_type: str  # RESCUE_BINARIZE | RESCUE_MARGIN_FIT | REVISE_PROMPT | ESCALATE_HUMAN
    success: bool
    details: str
    revised_positive_prompt: str | None = None
    revised_negative_prompt: str | None = None


class RetryManager:
    """Manages failure recovery, programmatic rescue, prompt refinement, and human escalation."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def attempt_programmatic_rescue(
        self,
        raw_image_path: str | Path,
        output_rescued_path: str | Path,
        is_spread: bool = False,
        is_left_page: bool = False,
    ) -> tuple[bool, str, list[str]]:
        """Attempt deterministic code-level rescue on raw image before wasting an API call.

        Applies Otsu adaptive binarization and margin centering.

        Args:
            raw_image_path: Path to the raw generated image.
            output_rescued_path: Destination path for the rescued image.
            is_spread: Whether the page is a spread (bypasses top header reservation).
            is_left_page: True if even verso page where gutter is on the right.

        Returns:
            Tuple of (passed: bool, message: str, remaining_violations: list[str]).
        """
        raw_p = Path(raw_image_path)
        out_p = Path(output_rescued_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Executing deterministic rescue pipeline on: {raw_p.name} (spread={is_spread}, is_left={is_left_page})"
        )

        # Step 1: Ingestion Stroke Pipeline (as-is mode or stroke hierarchy mode)
        h_cfg = get_stroke_hierarchy_config()
        use_as_is = h_cfg.get("use_generated_image_as_is", True)
        bin_res = rescue_binarize(raw_p, output_path=out_p, use_as_is=use_as_is, stroke_hierarchy=h_cfg)
        if not bin_res.success:
            return False, "Failed to apply adaptive binarization.", ["RESCUE_BINARIZE_FAILED"]

        # Step 2: Auto-Margin Centering and Scaling to safe margin boundary
        header_res = 0.0 if is_spread else HEADER_RESERVATION_IN
        coverage = 1.0 if is_spread else TARGET_COVERAGE_RATIO
        fit_res = fit_to_safe_margins(
            out_p,
            output_path=out_p,
            safe_margin_in=SAFE_MARGIN_IN,
            header_reservation_in=header_res,
            target_coverage_ratio=coverage,
            is_spread=is_spread,
            is_left_page=is_left_page,
            inside_gutter_in=SAFE_GUTTER_IN,
            outside_margin_in=SAFE_OUTSIDE_IN,
            bottom_margin_in=SAFE_BOTTOM_IN,
        )
        if not fit_res.success:
            return False, "Failed to fit artwork to safe margins.", ["RESCUE_MARGIN_FIT_FAILED"]

        # Step 3: Run Deterministic Validators to confirm rescue
        dim_res = validate_dimensions(out_p)
        margin_res = validate_margins(out_p, is_left_page=is_left_page)
        gray_res = validate_black_and_white(out_p)

        all_violations = dim_res.violations + margin_res.violations + gray_res.violations
        passed = dim_res.passed and margin_res.passed and gray_res.passed

        if passed:
            logger.info(
                f"Pristine deterministic rescue successful for {raw_p.name}! Saved image quota."
            )
            return True, "Deterministic rescue completely resolved all violations.", []
        else:
            logger.warning(f"Rescue partial. Remaining violations: {all_violations}")
            return (
                False,
                "Code rescue could not fully resolve geometry/shading violations.",
                all_violations,
            )

    def formulate_revised_prompt(
        self,
        current_positive: str,
        current_negative: str,
        violations: list[str],
        attempt_number: int,
    ) -> RecoveryAction:
        """Formulate fortified prompt tokens targeting the specific failure reasons."""
        if attempt_number >= self.max_retries:
            return RecoveryAction(
                action_type="ESCALATE_HUMAN",
                success=False,
                details=f"Exceeded maximum retry attempts ({self.max_retries}). Escalating to human review.",
            )

        fortified_pos = current_positive
        fortified_neg = current_negative

        for v in violations:
            if "Gray" in v:
                if "stark pure binary black and white line art only" not in fortified_pos:
                    fortified_pos += ", stark pure binary black and white line art only"
                if "gray tones" not in fortified_neg:
                    fortified_neg += ", gray tones"
            if "Shading" in v:
                if "stark pure binary black and white line art only" not in fortified_pos:
                    fortified_pos += ", stark pure binary black and white line art only"
                if "shading" not in fortified_neg:
                    fortified_neg += ", shading"
            if "Color" in v:
                if "stark pure binary black and white line art only" not in fortified_pos:
                    fortified_pos += ", stark pure binary black and white line art only"
                if "grayscale" not in fortified_neg:
                    fortified_neg += ", grayscale"

            if "Margin" in v:
                if "centered strictly in middle" not in fortified_pos:
                    fortified_pos += ", centered strictly in middle"
                if "touching edges" not in fortified_neg:
                    fortified_neg += ", touching edges"
            if "Gutter" in v:
                if "centered strictly in middle" not in fortified_pos:
                    fortified_pos += ", centered strictly in middle"
                if "border elements" not in fortified_neg:
                    fortified_neg += ", border elements"

            if "Multiple" in v or "Complexity" in v:
                if "isolated single lone object" not in fortified_pos:
                    fortified_pos += ", isolated single lone object"
                if "multiple objects, scenery, landscape" not in fortified_neg:
                    fortified_neg += ", multiple objects, scenery, landscape"

        return RecoveryAction(
            action_type="REVISE_PROMPT",
            success=True,
            details=f"Fortified prompt for attempt {attempt_number + 1}.",
            revised_positive_prompt=fortified_pos,
            revised_negative_prompt=fortified_neg,
        )
