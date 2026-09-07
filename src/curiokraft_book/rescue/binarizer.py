"""Deterministic adaptive binarizer to eliminate gray noise and protect image generation quotas."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel


class RescueBinarizeResult(BaseModel):
    """Result of the deterministic binarization rescue process."""

    success: bool
    input_path: str
    output_path: str
    original_non_binary_pixels: int
    cleaned_pixels_count: int
    method_applied: str


def rescue_binarize(
    input_path: str | Path,
    output_path: str | Path | None = None,
    threshold_value: int = 200,
    use_otsu: bool = True,
) -> RescueBinarizeResult:
    """Clean minor antialiasing, compression artifacts, and light gray pixels from raw line art.

    Transforms raw generated illustrations into pure, stark 2D black-and-white line art without
    altering line continuity or thickness.

    Args:
        input_path: Path to the source raw image.
        output_path: Path to save the rescued binary image (if None, overwrites or creates _rescued suffix).
        threshold_value: Base grayscale threshold value (default: 200).
        use_otsu: If True, uses Otsu's adaptive thresholding for optimal global separation.

    Returns:
        RescueBinarizeResult with rescue metrics.
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

    # Measure non-binary pixels before cleanup (15 < pixel < 240)
    initial_gray_mask = (gray_arr > 15) & (gray_arr < 240)
    original_non_binary_count = int(np.sum(initial_gray_mask))

    # Apply Otsu thresholding or standard thresholding
    if use_otsu:
        # Otsu thresholding: automatically calculates optimal threshold
        _, binary = cv2.threshold(gray_arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        method = "OTSU_ADAPTIVE_BINARIZATION"
    else:
        _, binary = cv2.threshold(gray_arr, threshold_value, 255, cv2.THRESH_BINARY)
        method = f"FIXED_THRESHOLD_{threshold_value}"

    # Smooth binary edges slightly using Gaussian filter + thresholding to avoid harsh pixelation
    blurred = cv2.GaussianBlur(binary, (3, 3), 0)
    _, refined_binary = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)

    # Save as 300 DPI PNG
    out_p.parent.mkdir(parents=True, exist_ok=True)
    rescued_img = Image.fromarray(refined_binary, mode="L")
    rescued_img.save(out_p, dpi=(300, 300), format="PNG")

    # Re-measure cleaned pixels
    final_gray_mask = (refined_binary > 15) & (refined_binary < 240)
    cleaned_pixels = original_non_binary_count - int(np.sum(final_gray_mask))

    return RescueBinarizeResult(
        success=True,
        input_path=str(in_p),
        output_path=str(out_p),
        original_non_binary_pixels=original_non_binary_count,
        cleaned_pixels_count=cleaned_pixels,
        method_applied=method,
    )
