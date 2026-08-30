"""Intelligent retry, prompt revision, and zero-waste failure escalation manager."""

import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from curiokraft_book.rescue.binarizer import rescue_binarize
from curiokraft_book.rescue.margin_fitter import fit_to_safe_margins
from curiokraft_book.validators.dimensions import validate_dimensions
from curiokraft_book.validators.margins import validate_margins
from curiokraft_book.validators.grayscale import validate_black_and_white

logger = logging.getLogger("curiokraft.retry_manager")


class RecoveryAction(BaseModel):
    """Action taken to recover a failing page."""
    action_type: str  # RESCUE_BINARIZE | RESCUE_MARGIN_FIT | REVISE_PROMPT | ESCALATE_HUMAN
    success: bool
    details: str
    revised_positive_prompt: Optional[str] = None
    revised_negative_prompt: Optional[str] = None


class RetryManager:
    """Manages failure recovery, programmatic rescue, prompt refinement, and human escalation."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def attempt_programmatic_rescue(
        self,
        raw_image_path: str | Path,
        output_rescued_path: str | Path
    ) -> tuple[bool, str, list[str]]:
        """Attempt deterministic code-level rescue on raw image before wasting an API call.
        
        Applies Otsu adaptive binarization and margin centering.
        
        Args:
            raw_image_path: Path to the raw generated image.
            output_rescued_path: Destination path for the rescued image.
            
        Returns:
            Tuple of (passed: bool, message: str, remaining_violations: list[str]).
        """
        raw_p = Path(raw_image_path)
        out_p = Path(output_rescued_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Executing deterministic rescue pipeline on: {raw_p.name}")

        # Step 1: Adaptive Binarization (cleans light gray, antialiasing, compression noise)
        bin_res = rescue_binarize(raw_p, output_path=out_p, use_otsu=True)
        if not bin_res.success:
            return False, "Failed to apply adaptive binarization.", ["RESCUE_BINARIZE_FAILED"]

        # Step 2: Auto-Margin Centering and Scaling to 0.50in boundary
        fit_res = fit_to_safe_margins(out_p, output_path=out_p, safe_margin_in=0.50)
        if not fit_res.success:
            return False, "Failed to fit artwork to safe margins.", ["RESCUE_MARGIN_FIT_FAILED"]

        # Step 3: Run Deterministic Validators to confirm rescue
        dim_res = validate_dimensions(out_p)
        margin_res = validate_margins(out_p)
        gray_res = validate_black_and_white(out_p)

        all_violations = dim_res.violations + margin_res.violations + gray_res.violations
        passed = dim_res.passed and margin_res.passed and gray_res.passed

        if passed:
            logger.info(f"Pristine deterministic rescue successful for {raw_p.name}! Saved image quota.")
            return True, "Deterministic rescue completely resolved all violations.", []
        else:
            logger.warning(f"Rescue partial. Remaining violations: {all_violations}")
            return False, "Code rescue could not fully resolve geometry/shading violations.", all_violations

    def formulate_revised_prompt(
        self,
        current_positive: str,
        current_negative: str,
        violations: list[str],
        attempt_number: int
    ) -> RecoveryAction:
        """Formulate fortified prompt tokens targeting the specific failure reasons."""
        if attempt_number >= self.max_retries:
            return RecoveryAction(
                action_type="ESCALATE_HUMAN",
                success=False,
                details=f"Exceeded maximum retry attempts ({self.max_retries}). Escalating to human review."
            )

        fortified_pos = current_positive
        fortified_neg = current_negative

        for v in violations:
            if "Gray" in v or "Shading" in v or "Color" in v:
                if "pure binary black and white line art" not in fortified_pos:
                    fortified_pos += ", stark pure binary black and white line art only, zero filled textures"
                fortified_neg += ", gray tones, shading, shadows, soft gradients, tones, textures, grayscale"

            if "Margin" in v or "Gutter" in v:
                if "centered strictly in middle" not in fortified_pos:
                    fortified_pos += ", compact centered object strictly in middle of white canvas with wide blank margins"
                fortified_neg += ", touching edges, border elements, bleed, panoramic, extended background"

            if "Multiple" in v or "Complexity" in v:
                fortified_pos += ", isolated single lone object, completely empty background"
                fortified_neg += ", multiple objects, scenery, landscape, secondary items"

        return RecoveryAction(
            action_type="REVISE_PROMPT",
            success=True,
            details=f"Fortified prompt for attempt {attempt_number + 1}.",
            revised_positive_prompt=fortified_pos,
            revised_negative_prompt=fortified_neg
        )
