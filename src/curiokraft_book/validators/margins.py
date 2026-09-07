"""Margin and safe-zone bounding box validator for Amazon KDP interior printing."""

from pathlib import Path

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field


class MarginMetrics(BaseModel):
    """Calculated margin distances from artwork bounding box to canvas edges."""

    left_margin_in: float
    right_margin_in: float
    top_margin_in: float
    bottom_margin_in: float
    left_margin_px: int
    right_margin_px: int
    top_margin_px: int
    bottom_margin_px: int


class MarginValidationResult(BaseModel):
    """Result of margin and safe-zone validation."""

    passed: bool
    image_path: str
    bounding_box_px: tuple[int, int, int, int] = Field(
        description="Bounding box of artwork ink (min_x, min_y, max_x, max_y)"
    )
    artwork_width_px: int
    artwork_height_px: int
    canvas_width_px: int
    canvas_height_px: int
    canvas_coverage_ratio: float
    margins: MarginMetrics
    kdp_compliant: bool
    project_safe_zone_compliant: bool
    violations: list[str] = Field(default_factory=list)


def validate_margins(
    image_path: str | Path,
    dpi: int = 300,
    safe_margin_in: float = 0.50,
    kdp_min_gutter_in: float = 0.375,
    kdp_min_outside_in: float = 0.250,
    ink_threshold: int = 240,
    is_left_page: bool = False,
) -> MarginValidationResult:
    """Validate that all artwork ink remains strictly inside KDP and project safe boundaries.

    Args:
        image_path: Path to the image file.
        dpi: Target resolution in dots per inch (default: 300).
        safe_margin_in: Project target safe margin in inches (default: 0.50 in = 150 px).
        kdp_min_gutter_in: Authoritative KDP hard minimum inside gutter margin (default: 0.375 in).
        kdp_min_outside_in: Authoritative KDP hard minimum outside margin (default: 0.250 in).
        ink_threshold: Grayscale pixel value below which pixels are considered ink (default: 240).
        is_left_page: True if this is an even (left-hand) page where gutter is on the right.

    Returns:
        MarginValidationResult with bounding box and margin clearance metrics.
    """
    path = Path(image_path)
    if not path.exists():
        empty_metrics = MarginMetrics(
            left_margin_in=0,
            right_margin_in=0,
            top_margin_in=0,
            bottom_margin_in=0,
            left_margin_px=0,
            right_margin_px=0,
            top_margin_px=0,
            bottom_margin_px=0,
        )
        return MarginValidationResult(
            passed=False,
            image_path=str(path),
            bounding_box_px=(0, 0, 0, 0),
            artwork_width_px=0,
            artwork_height_px=0,
            canvas_width_px=0,
            canvas_height_px=0,
            canvas_coverage_ratio=0.0,
            margins=empty_metrics,
            kdp_compliant=False,
            project_safe_zone_compliant=False,
            violations=[f"Image file does not exist: {path}"],
        )

    with Image.open(path) as img:
        img_gray = img.convert("L")
        arr = np.array(img_gray)

    canvas_height, canvas_width = arr.shape
    ink_mask = arr < ink_threshold

    # If image is pure white (no ink)
    if not np.any(ink_mask):
        empty_metrics = MarginMetrics(
            left_margin_in=canvas_width / dpi,
            right_margin_in=canvas_width / dpi,
            top_margin_in=canvas_height / dpi,
            bottom_margin_in=canvas_height / dpi,
            left_margin_px=canvas_width,
            right_margin_px=canvas_width,
            top_margin_px=canvas_height,
            bottom_margin_px=canvas_height,
        )
        return MarginValidationResult(
            passed=False,
            image_path=str(path),
            bounding_box_px=(0, 0, 0, 0),
            artwork_width_px=0,
            artwork_height_px=0,
            canvas_width_px=canvas_width,
            canvas_height_px=canvas_height,
            canvas_coverage_ratio=0.0,
            margins=empty_metrics,
            kdp_compliant=False,
            project_safe_zone_compliant=False,
            violations=["Image contains no printable ink pixels (blank white canvas)."],
        )

    # Find bounding box coordinates of all ink pixels
    y_indices, x_indices = np.where(ink_mask)
    min_x, max_x = int(np.min(x_indices)), int(np.max(x_indices))
    min_y, max_y = int(np.min(y_indices)), int(np.max(y_indices))

    artwork_width = max_x - min_x + 1
    artwork_height = max_y - min_y + 1

    left_margin_px = min_x
    right_margin_px = canvas_width - 1 - max_x
    top_margin_px = min_y
    bottom_margin_px = canvas_height - 1 - max_y

    left_margin_in = round(left_margin_px / dpi, 3)
    right_margin_in = round(right_margin_px / dpi, 3)
    top_margin_in = round(top_margin_px / dpi, 3)
    bottom_margin_in = round(bottom_margin_px / dpi, 3)

    margins = MarginMetrics(
        left_margin_in=left_margin_in,
        right_margin_in=right_margin_in,
        top_margin_in=top_margin_in,
        bottom_margin_in=bottom_margin_in,
        left_margin_px=left_margin_px,
        right_margin_px=right_margin_px,
        top_margin_px=top_margin_px,
        bottom_margin_px=bottom_margin_px,
    )

    # Determine inside gutter vs outside margin based on page side
    if is_left_page:
        gutter_margin_in = right_margin_in
        outside_margin_in = left_margin_in
    else:
        gutter_margin_in = left_margin_in
        outside_margin_in = right_margin_in

    violations = []

    # KDP Hard Boundary Checks
    kdp_compliant = True
    if gutter_margin_in < kdp_min_gutter_in:
        kdp_compliant = False
        violations.append(
            f"KDP Gutter Violation: Inside gutter margin is {gutter_margin_in}in (KDP hard minimum is {kdp_min_gutter_in}in)"
        )
    if outside_margin_in < kdp_min_outside_in:
        kdp_compliant = False
        violations.append(
            f"KDP Outside Margin Violation: Outside margin is {outside_margin_in}in (KDP hard minimum is {kdp_min_outside_in}in)"
        )
    if top_margin_in < kdp_min_outside_in:
        kdp_compliant = False
        violations.append(
            f"KDP Top Margin Violation: Top margin is {top_margin_in}in (KDP hard minimum is {kdp_min_outside_in}in)"
        )
    if bottom_margin_in < kdp_min_outside_in:
        kdp_compliant = False
        violations.append(
            f"KDP Bottom Margin Violation: Bottom margin is {bottom_margin_in}in (KDP hard minimum is {kdp_min_outside_in}in)"
        )

    # Project Safe Zone Target Checks (0.50 in)
    project_safe_compliant = True
    min_safe_px = int(safe_margin_in * dpi)
    if (
        min_x < min_safe_px
        or right_margin_px < min_safe_px
        or min_y < min_safe_px
        or bottom_margin_px < min_safe_px
    ):
        project_safe_compliant = False
        if kdp_compliant:
            violations.append(
                f"Project Safe Zone Target Breached: Content extends into the {safe_margin_in}in conservative safety boundary."
            )

    # Calculate usable canvas coverage
    usable_width = canvas_width - (2 * min_safe_px)
    usable_height = canvas_height - (2 * min_safe_px)
    usable_area = usable_width * usable_height
    artwork_area = artwork_width * artwork_height
    coverage_ratio = round(artwork_area / usable_area, 3) if usable_area > 0 else 0.0

    passed = kdp_compliant and project_safe_compliant

    return MarginValidationResult(
        passed=passed,
        image_path=str(path),
        bounding_box_px=(min_x, min_y, max_x, max_y),
        artwork_width_px=artwork_width,
        artwork_height_px=artwork_height,
        canvas_width_px=canvas_width,
        canvas_height_px=canvas_height,
        canvas_coverage_ratio=coverage_ratio,
        margins=margins,
        kdp_compliant=kdp_compliant,
        project_safe_zone_compliant=project_safe_compliant,
        violations=violations,
    )
