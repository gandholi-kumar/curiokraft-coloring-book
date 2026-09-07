"""Deterministic auto-margin and centering fitter for coloring book artwork."""

from pathlib import Path

import numpy as np
from PIL import Image
from pydantic import BaseModel


class MarginFitResult(BaseModel):
    """Result of margin fitting and auto-centering."""

    success: bool
    input_path: str
    output_path: str
    original_bbox: tuple[int, int, int, int]
    new_bbox: tuple[int, int, int, int]
    scale_factor: float
    target_canvas_size: tuple[int, int]
    top_margin_px: int
    bottom_margin_px: int
    left_margin_px: int
    right_margin_px: int


def fit_to_safe_margins(
    input_path: str | Path,
    output_path: str | Path | None = None,
    canvas_width: int = 2550,
    canvas_height: int = 3300,
    dpi: int = 300,
    safe_margin_in: float = 0.50,
    header_reservation_in: float = 1.20,
    target_coverage_ratio: float = 0.72,
    is_spread: bool = False,
) -> MarginFitResult:
    """Crop artwork to its tight bounding box, center, scale, and place on a pristine 300 DPI canvas.

    Guarantees that artwork strictly satisfies KDP inside/outside margins. For standard pages,
    preserves the top header space for vector typography rendering. For spreads, uses the entire
    safe area (>= 0.50 in safe margins on all 4 sides) with zero header reservation.

    Args:
        input_path: Path to the source image.
        output_path: Path to save the fitted image (if None, overwrites or creates _fitted suffix).
        canvas_width: Target master width in pixels (default: 2550).
        canvas_height: Target master height in pixels (default: 3300).
        dpi: Target DPI resolution (default: 300).
        safe_margin_in: Safe margin boundary in inches (default: 0.50 in = 150 px).
        header_reservation_in: Top margin reserved for typography in inches (default: 1.20 in = 360 px).
        target_coverage_ratio: Target coverage of the usable artwork zone (default: 0.72).
        is_spread: If True, bypasses header reservation and uses full safe margin canvas.

    Returns:
        MarginFitResult with repositioning coordinates and scale factor.
    """
    in_p = Path(input_path)
    if not in_p.exists():
        return MarginFitResult(
            success=False,
            input_path=str(in_p),
            output_path="",
            original_bbox=(0, 0, 0, 0),
            new_bbox=(0, 0, 0, 0),
            scale_factor=1.0,
            target_canvas_size=(canvas_width, canvas_height),
            top_margin_px=0,
            bottom_margin_px=0,
            left_margin_px=0,
            right_margin_px=0,
        )

    out_p = Path(output_path) if output_path else in_p.parent / f"{in_p.stem}_fitted.png"

    with Image.open(in_p) as img:
        img_gray = img.convert("L")
        arr = np.array(img_gray)

    # Detect ink pixels (pixels < 240)
    ink_mask = arr < 240
    if not np.any(ink_mask):
        return MarginFitResult(
            success=False,
            input_path=str(in_p),
            output_path="",
            original_bbox=(0, 0, 0, 0),
            new_bbox=(0, 0, 0, 0),
            scale_factor=1.0,
            target_canvas_size=(canvas_width, canvas_height),
            top_margin_px=0,
            bottom_margin_px=0,
            left_margin_px=0,
            right_margin_px=0,
        )

    y_indices, x_indices = np.where(ink_mask)
    min_x, max_x = int(np.min(x_indices)), int(np.max(x_indices))
    min_y, max_y = int(np.min(y_indices)), int(np.max(y_indices))
    orig_bbox = (min_x, min_y, max_x, max_y)

    # Crop tight bounding box
    cropped_img = img_gray.crop((min_x, min_y, max_x + 1, max_y + 1))
    crop_w, crop_h = cropped_img.size

    # Define usable artwork envelope
    margin_px = int(safe_margin_in * dpi)
    if is_spread or header_reservation_in <= 0.0:
        header_px = 0
        usable_w = canvas_width - (2 * margin_px)
        usable_h = canvas_height - (2 * margin_px)
        eff_coverage = 1.0 if target_coverage_ratio == 0.72 else target_coverage_ratio
        max_upscale = 3.5
    else:
        header_px = int(header_reservation_in * dpi)
        usable_w = canvas_width - (2 * margin_px)
        usable_h = canvas_height - (margin_px + header_px)
        eff_coverage = target_coverage_ratio
        max_upscale = 1.25

    # Calculate optimal uniform scale factor
    scale_w = (usable_w * eff_coverage) / crop_w if crop_w > 0 else 1.0
    scale_h = (usable_h * eff_coverage) / crop_h if crop_h > 0 else 1.0
    scale_factor = min(scale_w, scale_h, max_upscale)

    new_w = max(1, int(round(crop_w * scale_factor)))
    new_h = max(1, int(round(crop_h * scale_factor)))

    # Resize cropped artwork with high-quality Lanczos resampling
    resized_artwork = cropped_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Create pristine pure white canvas (#FFFFFF)
    canvas = Image.new("L", (canvas_width, canvas_height), 255)

    # Calculate centered position within usable zone
    pos_x = margin_px + (usable_w - new_w) // 2
    if header_px > 0:
        pos_y = header_px + (usable_h - new_h) // 2
    else:
        pos_y = margin_px + (usable_h - new_h) // 2

    canvas.paste(resized_artwork, (pos_x, pos_y))

    # Save as 300 DPI master PNG
    out_p.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_p, dpi=(dpi, dpi), format="PNG")

    new_bbox = (pos_x, pos_y, pos_x + new_w, pos_y + new_h)

    return MarginFitResult(
        success=True,
        input_path=str(in_p),
        output_path=str(out_p),
        original_bbox=orig_bbox,
        new_bbox=new_bbox,
        scale_factor=round(scale_factor, 3),
        target_canvas_size=(canvas_width, canvas_height),
        top_margin_px=pos_y,
        bottom_margin_px=canvas_height - (pos_y + new_h),
        left_margin_px=pos_x,
        right_margin_px=canvas_width - (pos_x + new_w),
    )
