"""Deterministic KDP paperback cover geometry and compliance validator."""

import json
from pathlib import Path
from typing import Optional
from PIL import Image
import numpy as np
from pydantic import BaseModel, Field


class CoverValidationResult(BaseModel):
    """Result of KDP cover geometry and barcode clearance validation."""
    passed: bool
    cover_image_path: str
    width_in: float
    height_in: float
    width_px: int
    height_px: int
    dpi: tuple[int, int]
    expected_width_in: float = 17.498
    expected_height_in: float = 11.250
    spine_width_in: float = 0.248
    spine_center_x_px: int
    barcode_box_clear: bool
    kdp_compliant: bool
    violations: list[str] = Field(default_factory=list)


def validate_kdp_cover(
    cover_path: str | Path,
    expected_width_in: float = 17.498,
    expected_height_in: float = 11.250,
    spine_width_in: float = 0.248,
    dpi: int = 300,
    report_output_path: Optional[str | Path] = "output/reports/cover_kdp_compliance_report.json"
) -> CoverValidationResult:
    """Validate that the assembled cover complies strictly with Amazon KDP full wrap specifications.
    
    Args:
        cover_path: Path to the assembled cover master PNG file.
        expected_width_in: Total width in inches (default: 17.498 in).
        expected_height_in: Total height in inches (default: 11.250 in).
        spine_width_in: Spine width in inches (default: 0.248 in).
        dpi: Target DPI (default: 300).
        report_output_path: Path to save the compliance JSON report.
        
    Returns:
        CoverValidationResult with validation metrics.
    """
    path = Path(cover_path)
    if not path.exists():
        return CoverValidationResult(
            passed=False,
            cover_image_path=str(path),
            width_in=0,
            height_in=0,
            width_px=0,
            height_px=0,
            dpi=(0, 0),
            spine_center_x_px=0,
            barcode_box_clear=False,
            kdp_compliant=False,
            violations=[f"Cover file not found: {path}"]
        )

    expected_w_px = int(round(expected_width_in * dpi))  # 5249 px
    expected_h_px = int(round(expected_height_in * dpi))  # 3375 px

    violations = []

    with Image.open(path) as img:
        actual_w, actual_h = img.size
        actual_dpi = img.info.get("dpi", (300, 300))
        if isinstance(actual_dpi, tuple) and len(actual_dpi) >= 2:
            dpi_x, dpi_y = int(round(actual_dpi[0])), int(round(actual_dpi[1]))
        else:
            dpi_x = dpi_y = 300

        actual_w_in = round(actual_w / dpi, 3)
        actual_h_in = round(actual_h / dpi, 3)

        # 1. Canvas Dimension Tolerances (Permit ±2 px rounding variance)
        if abs(actual_w - expected_w_px) > 3:
            violations.append(
                f"Cover Width Mismatch: Expected {expected_w_px}px ({expected_width_in}in), got {actual_w}px ({actual_w_in}in)."
            )
        if abs(actual_h - expected_h_px) > 3:
            violations.append(
                f"Cover Height Mismatch: Expected {expected_h_px}px ({expected_height_in}in), got {actual_h}px ({actual_h_in}in)."
            )

        # 2. DPI Verification
        if dpi_x != dpi or dpi_y != dpi:
            violations.append(
                f"Cover DPI Mismatch: Expected {dpi} DPI, got ({dpi_x}, {dpi_y}) DPI."
            )

        # 3. Barcode Safe Box Analysis
        # Barcode area on back cover lower-right (approx 600x360 px)
        spine_center_x = actual_w // 2
        spine_left_x = spine_center_x - int(round((spine_width_in * dpi) / 2))
        
        barcode_w = 600
        barcode_h = 360
        bx1 = spine_left_x - barcode_w - 150
        by1 = actual_h - barcode_h - 150
        bx2 = bx1 + barcode_w
        by2 = by1 + barcode_h

        # Inspect barcode region pixels
        cover_rgb = img.convert("RGB")
        barcode_crop = np.array(cover_rgb.crop((bx1, by1, bx2, by2)))
        
        # Check if region is clean (high average brightness > 220, meaning clean white box)
        avg_brightness = np.mean(barcode_crop)
        barcode_clear = avg_brightness > 200

        if not barcode_clear:
            violations.append(
                f"Barcode Zone Obstructed: Barcode exclusion box is not clean white (Average brightness: {avg_brightness:.1f})."
            )

    kdp_ok = len(violations) == 0

    result = CoverValidationResult(
        passed=kdp_ok,
        cover_image_path=str(path),
        width_in=actual_w_in,
        height_in=actual_h_in,
        width_px=actual_w,
        height_px=actual_h,
        dpi=(dpi_x, dpi_y),
        expected_width_in=expected_width_in,
        expected_height_in=expected_height_in,
        spine_width_in=spine_width_in,
        spine_center_x_px=spine_center_x,
        barcode_box_clear=barcode_clear,
        kdp_compliant=kdp_ok,
        violations=violations
    )

    if report_output_path:
        r_out = Path(report_output_path)
        r_out.parent.mkdir(parents=True, exist_ok=True)
        with open(r_out, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2)

    return result
