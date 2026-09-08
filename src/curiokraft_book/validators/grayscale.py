"""Grayscale, intentional gray shading, and color detector for coloring book pages."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

from curiokraft_book.constants import (
    BLACK_THRESHOLD,
    COLOR_TOLERANCE,
    MAX_GRAY_CLUSTER_SIZE_PX,
    WHITE_THRESHOLD,
)


class GrayscaleValidationResult(BaseModel):
    """Result of binary black-and-white purity validation."""

    passed: bool
    image_path: str
    is_pure_black_and_white: bool
    has_unauthorized_color: bool
    total_pixels: int
    pure_black_pixel_count: int
    pure_white_pixel_count: int
    non_binary_pixel_count: int
    non_binary_pixel_percentage: float
    max_gray_cluster_size_px: int
    gray_cluster_count: int
    violations: list[str] = Field(default_factory=list)


def validate_black_and_white(
    image_path: str | Path,
    black_threshold: int = BLACK_THRESHOLD,
    white_threshold: int = WHITE_THRESHOLD,
    max_gray_cluster_size_px: int = MAX_GRAY_CLUSTER_SIZE_PX,
    color_tolerance: int = COLOR_TOLERANCE,
) -> GrayscaleValidationResult:
    """Analyze image to verify binary black-and-white purity and detect prohibited gray shading.

    Differentiates valid anti-aliasing on 1-2px vector edges from intentional gray shading or fills.

    Args:
        image_path: Path to the image file.
        black_threshold: Intensity below which pixels are considered pure black (default: 20).
        white_threshold: Intensity above which pixels are considered pure white (default: 235).
        max_gray_cluster_size_px: Maximum contiguous gray pixel cluster permitted before flagging
                                   as intentional shading (default: 60 px).
        color_tolerance: Max permitted variance between R, G, B channels before flagging color (default: 6).

    Returns:
        GrayscaleValidationResult with detailed cluster metrics and violation reports.
    """
    path = Path(image_path)
    if not path.exists():
        return GrayscaleValidationResult(
            passed=False,
            image_path=str(path),
            is_pure_black_and_white=False,
            has_unauthorized_color=False,
            total_pixels=0,
            pure_black_pixel_count=0,
            pure_white_pixel_count=0,
            non_binary_pixel_count=0,
            non_binary_pixel_percentage=0.0,
            max_gray_cluster_size_px=0,
            gray_cluster_count=0,
            violations=[f"Image file does not exist: {path}"],
        )

    with Image.open(path) as img:
        img_rgb = img.convert("RGB")
        rgb_arr = np.array(img_rgb)
        gray_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2GRAY)

    total_pixels = gray_arr.size
    violations = []

    # 1. Color Check: Ensure R, G, B channels are identical within tolerance
    diff_rg = np.abs(rgb_arr[:, :, 0].astype(np.int16) - rgb_arr[:, :, 1].astype(np.int16))
    diff_gb = np.abs(rgb_arr[:, :, 1].astype(np.int16) - rgb_arr[:, :, 2].astype(np.int16))
    diff_rb = np.abs(rgb_arr[:, :, 0].astype(np.int16) - rgb_arr[:, :, 2].astype(np.int16))

    color_pixels = np.sum(
        (diff_rg > color_tolerance) | (diff_gb > color_tolerance) | (diff_rb > color_tolerance)
    )
    has_color = bool(color_pixels > 50)  # Allow slight noise margin
    if has_color:
        violations.append(
            f"Color Detected: Image contains {color_pixels} non-monochromatic color pixels. Interior must be pure black and white."
        )

    # 2. Pixel Category Counts
    pure_black_mask = gray_arr <= black_threshold
    pure_white_mask = gray_arr >= white_threshold
    gray_mask = (~pure_black_mask) & (~pure_white_mask)

    pure_black_count = int(np.sum(pure_black_mask))
    pure_white_count = int(np.sum(pure_white_mask))
    non_binary_count = int(np.sum(gray_mask))
    non_binary_pct = round((non_binary_count / total_pixels) * 100, 3)

    # 3. Connected Component Analysis for Gray Shading Clusters
    # We convert gray_mask to uint8 binary image (255 for gray, 0 for pure black/white)
    gray_binary = (gray_mask.astype(np.uint8)) * 255
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        gray_binary, connectivity=8
    )

    # stats format: [x, y, width, height, area]
    # Label 0 is background (pure black/white pixels)
    gray_cluster_count = 0
    max_cluster_size = 0
    large_clusters = []

    for i in range(1, num_labels):
        cluster_area = int(stats[i, cv2.CC_STAT_AREA])
        if cluster_area > max_cluster_size:
            max_cluster_size = cluster_area
        if cluster_area > max_gray_cluster_size_px:
            gray_cluster_count += 1
            x = int(stats[i, cv2.CC_STAT_LEFT])
            y = int(stats[i, cv2.CC_STAT_TOP])
            w = int(stats[i, cv2.CC_STAT_WIDTH])
            h = int(stats[i, cv2.CC_STAT_HEIGHT])
            large_clusters.append((cluster_area, (x, y, w, h)))

    is_pure_bw = True
    if gray_cluster_count > 0:
        is_pure_bw = False
        violations.append(
            f"Intentional Gray Shading Detected: Found {gray_cluster_count} gray pixel clusters exceeding the "
            f"{max_gray_cluster_size_px}px threshold (Largest cluster: {max_cluster_size}px)."
        )

    # Global non-binary pixel threshold (if gray pixels exceed 4% of total canvas)
    if non_binary_pct > 4.0:
        is_pure_bw = False
        violations.append(
            f"Excessive Grayscale Content: {non_binary_pct}% of canvas consists of gray transition pixels (Threshold: <= 4.0%)."
        )

    passed = not has_color and is_pure_bw

    return GrayscaleValidationResult(
        passed=passed,
        image_path=str(path),
        is_pure_black_and_white=is_pure_bw,
        has_unauthorized_color=has_color,
        total_pixels=total_pixels,
        pure_black_pixel_count=pure_black_count,
        pure_white_pixel_count=pure_white_count,
        non_binary_pixel_count=non_binary_count,
        non_binary_pixel_percentage=non_binary_pct,
        max_gray_cluster_size_px=max_cluster_size,
        gray_cluster_count=gray_cluster_count,
        violations=violations,
    )
