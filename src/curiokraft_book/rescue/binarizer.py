"""Deterministic adaptive binarizer and stroke hierarchy engine for coloring book artwork."""

from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel

from curiokraft_book.constants import (
    BINARIZE_THRESHOLD_VALUE,
    DEFAULT_BACKGROUND_STROKE_TONE,
    DEFAULT_PRESERVE_NATURAL_TONE,
    DEFAULT_USE_GENERATED_IMAGE_AS_IS,
    get_stroke_hierarchy_config,
)


class RescueBinarizeResult(BaseModel):
    """Result of the deterministic binarization / stroke processing rescue."""

    success: bool
    input_path: str
    output_path: str
    original_non_binary_pixels: int
    cleaned_pixels_count: int
    method_applied: str


def rescue_binarize(
    input_path: str | Path,
    output_path: str | Path | None = None,
    threshold_value: int = BINARIZE_THRESHOLD_VALUE,
    use_otsu: bool = True,
    use_as_is: bool | None = None,
    stroke_hierarchy: dict[str, Any] | None = None,
) -> RescueBinarizeResult:
    """Process raw line art respecting configuration: 'as-is' natural mode or stroke hierarchy.

    - When use_as_is=True:
        Preserves raw generated illustrations AS-IS without altering or binarizing strokes.
        Only cleans paper background (pixels > 225 -> 255) to eliminate scanner haze.
    - When stroke_hierarchy is enabled:
        Applies stroke hierarchy: primary subject outlines are rendered stark pitch-black (0),
        while background scenery (coral, kelp, bubbles) is rendered at a lighter tone (e.g. 110)
        so the subject pops forward and doesn't merge with the background.
    - Otherwise:
        Applies standard Otsu adaptive binarization to clean gray noise into binary line art.

    Args:
        input_path: Path to the source raw image.
        output_path: Path to save the processed image.
        threshold_value: Base grayscale threshold value for legacy binarization.
        use_otsu: If True, uses Otsu thresholding when standard binarization is needed.
        use_as_is: If True, bypasses stroke redrawing and keeps art as-is.
        stroke_hierarchy: Configuration dict for stroke hierarchy weights and tones.

    Returns:
        RescueBinarizeResult with processing metrics.
    """
    in_p = Path(input_path)
    if not in_p.exists():
        return RescueBinarizeResult(
            success=False,
            input_path=str(in_p),
            output_path="",
            original_non_binary_pixels=0,
            cleaned_pixels_count=0,
            method_applied="NONE",
        )

    out_p = Path(output_path) if output_path else in_p.parent / f"{in_p.stem}_rescued.png"

    # Read image in grayscale
    gray_arr = cv2.imread(str(in_p), cv2.IMREAD_GRAYSCALE)
    if gray_arr is None:
        return RescueBinarizeResult(
            success=False,
            input_path=str(in_p),
            output_path="",
            original_non_binary_pixels=0,
            cleaned_pixels_count=0,
            method_applied="READ_FAILURE",
        )

    # Determine mode from parameter or config
    hierarchy_cfg = stroke_hierarchy if stroke_hierarchy is not None else get_stroke_hierarchy_config()
    if use_as_is is None:
        use_as_is = bool(hierarchy_cfg.get("use_generated_image_as_is", False)) if stroke_hierarchy is not None else False

    # Measure non-binary pixels before cleanup (15 < pixel < 240)
    initial_gray_mask = (gray_arr > 15) & (gray_arr < 240)
    original_non_binary_count = int(np.sum(initial_gray_mask))

    if use_as_is:
        # MODE 1: As-Is with pristine paper white cleanup
        processed = gray_arr.copy()
        processed[processed > 225] = 255
        method = "AS_IS_NATURAL_PRESERVED"
    elif hierarchy_cfg.get("enabled", False):
        # MODE 2: Stroke Hierarchy & Tone Remapping
        bg_tone = int(hierarchy_cfg.get("background_stroke_tone", DEFAULT_BACKGROUND_STROKE_TONE))
        preserve_natural = bool(
            hierarchy_cfg.get("preserve_natural_tone", DEFAULT_PRESERVE_NATURAL_TONE)
        )

        fg_mask = gray_arr < 50
        bg_mask = (gray_arr >= 50) & (gray_arr < 225)

        processed_float = np.full_like(gray_arr, 255, dtype=np.float32)
        # Primary object: pure stark pitch-black
        processed_float[fg_mask] = 0.0

        # Background habitat lines: lighter tone
        if np.any(bg_mask):
            if preserve_natural:
                # Retain gradient dynamics scaled around bg_tone
                norm_bg = (gray_arr[bg_mask].astype(np.float32) - 50.0) / (225.0 - 50.0)
                half_spread = min(25.0, float(bg_tone) * 0.25)
                remapped = (bg_tone - half_spread) + norm_bg * (2.0 * half_spread)
                processed_float[bg_mask] = np.clip(remapped, 0.0, 240.0)
            else:
                processed_float[bg_mask] = float(bg_tone)

        processed = np.clip(processed_float, 0, 255).astype(np.uint8)
        method = f"STROKE_HIERARCHY_TONE_{bg_tone}"
    else:
        # MODE 3: Standard Otsu Adaptive Binarization
        if use_otsu:
            otsu_val, _ = cv2.threshold(gray_arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            effective_thresh = max(otsu_val, float(threshold_value))
            _, binary = cv2.threshold(gray_arr, effective_thresh, 255, cv2.THRESH_BINARY)
            method = "OTSU_ADAPTIVE_BINARIZATION"
        else:
            _, binary = cv2.threshold(gray_arr, threshold_value, 255, cv2.THRESH_BINARY)
            method = f"FIXED_THRESHOLD_{threshold_value}"

        blurred = cv2.GaussianBlur(binary, (3, 3), 0)
        _, refined_binary = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
        processed = refined_binary

    # Save as 300 DPI PNG
    out_p.parent.mkdir(parents=True, exist_ok=True)
    rescued_img = Image.fromarray(processed, mode="L")
    rescued_img.save(out_p, dpi=(300, 300), format="PNG")

    # Measure cleaned pixels
    final_gray_mask = (processed > 15) & (processed < 240)
    cleaned_pixels = original_non_binary_count - int(np.sum(final_gray_mask))

    return RescueBinarizeResult(
        success=True,
        input_path=str(in_p),
        output_path=str(out_p),
        original_non_binary_pixels=original_non_binary_count,
        cleaned_pixels_count=cleaned_pixels,
        method_applied=method,
    )
