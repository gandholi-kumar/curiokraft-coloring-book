"""Master image dimension and DPI validator for Amazon KDP specifications."""

from pathlib import Path
from typing import Optional
from PIL import Image
from pydantic import BaseModel, Field


class DimensionValidationResult(BaseModel):
    """Result of image dimension and DPI validation."""
    passed: bool = Field(description="Whether the image meets all dimension and DPI requirements")
    image_path: str
    actual_width_px: int
    actual_height_px: int
    expected_width_px: int
    expected_height_px: int
    actual_dpi: tuple[int, int]
    expected_dpi: int
    aspect_ratio: float
    violations: list[str] = Field(default_factory=list)


def validate_dimensions(
    image_path: str | Path,
    expected_width: int = 2550,
    expected_height: int = 3300,
    expected_dpi: int = 300,
    allowed_dpi_tolerance: int = 0
) -> DimensionValidationResult:
    """Validate that an image strictly conforms to the required pixel dimensions and 300 DPI target.
    
    Args:
        image_path: Path to the image file.
        expected_width: Expected width in pixels (default: 2550 for 8.5" at 300 DPI).
        expected_height: Expected height in pixels (default: 3300 for 11.0" at 300 DPI).
        expected_dpi: Expected DPI resolution (default: 300).
        allowed_dpi_tolerance: Permitted DPI variance (default: 0).
        
    Returns:
        DimensionValidationResult with detailed metrics and pass/fail flag.
    """
    path = Path(image_path)
    if not path.exists():
        return DimensionValidationResult(
            passed=false,
            image_path=str(path),
            actual_width_px=0,
            actual_height_px=0,
            expected_width_px=expected_width,
            expected_height_px=expected_height,
            actual_dpi=(0, 0),
            expected_dpi=expected_dpi,
            aspect_ratio=0.0,
            violations=[f"Image file does not exist: {path}"]
        )

    with Image.open(path) as img:
        actual_width, actual_height = img.size
        dpi_info = img.info.get("dpi", (300, 300))
        
        # Normalize DPI tuple
        if isinstance(dpi_info, (int, float)):
            dpi_x = dpi_y = int(round(dpi_info))
        elif isinstance(dpi_info, tuple) and len(dpi_info) >= 2:
            dpi_x, dpi_y = int(round(dpi_info[0])), int(round(dpi_info[1]))
        else:
            dpi_x = dpi_y = 300

        aspect_ratio = round(actual_width / actual_height, 4) if actual_height > 0 else 0.0
        expected_aspect_ratio = round(expected_width / expected_height, 4)

        violations = []

        if actual_width != expected_width:
            violations.append(
                f"Width mismatch: Expected {expected_width}px, got {actual_width}px (Difference: {actual_width - expected_width}px)"
            )

        if actual_height != expected_height:
            violations.append(
                f"Height mismatch: Expected {expected_height}px, got {actual_height}px (Difference: {actual_height - expected_height}px)"
            )

        if abs(dpi_x - expected_dpi) > allowed_dpi_tolerance or abs(dpi_y - expected_dpi) > allowed_dpi_tolerance:
            violations.append(
                f"DPI mismatch: Expected {expected_dpi} DPI, got ({dpi_x}, {dpi_y}) DPI"
            )

        passed = len(violations) == 0

        return DimensionValidationResult(
            passed=passed,
            image_path=str(path),
            actual_width_px=actual_width,
            actual_height_px=actual_height,
            expected_width_px=expected_width,
            expected_height_px=expected_height,
            actual_dpi=(dpi_x, dpi_y),
            expected_dpi=expected_dpi,
            aspect_ratio=aspect_ratio,
            violations=violations
        )
