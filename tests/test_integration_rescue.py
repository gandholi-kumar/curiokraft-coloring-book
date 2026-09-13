"""Integration test: deterministic rescue pipeline (binarize -> margin fit -> certify).

The rescue stage runs on the *raw* page, before the typography overlay.  Two
details of the real pipeline are pinned here because they are easy to get wrong:

* ``rescue_binarize`` output is pure binary, but ``fit_to_safe_margins`` rescales
  the cropped artwork with LANCZOS, which re-introduces thin gray transition
  ramps along every edge.  The gray validator therefore still reports
  "Intentional Gray Shading" on the rescue artifact.
* ``composite_typography`` thresholds the artwork as part of compositing, so the
  final master is pure black-and-white again — which is why the batch pipeline
  approves pages that the rescue stage itself reported as partial.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from curiokraft_book.compositor.typography import composite_typography
from curiokraft_book.orchestrator.providers import MockImageProvider
from curiokraft_book.orchestrator.retry_manager import RetryManager
from curiokraft_book.rescue.binarizer import rescue_binarize
from curiokraft_book.rescue.margin_fitter import fit_to_safe_margins
from curiokraft_book.validators.dimensions import validate_dimensions
from curiokraft_book.validators.grayscale import validate_black_and_white
from curiokraft_book.validators.margins import validate_margins

pytestmark = pytest.mark.integration

_CANVAS = (2550, 3300)
_SAFE_MARGIN_PX = 150  # 0.50 in @ 300 DPI


def _raw_page(directory: Path, section: str = "Animals") -> Path:
    """Write the offline mock raster to disk, exactly as the batch runner does."""
    path = directory / "raw_p005_apple.png"
    MockImageProvider().generate("prompt", "", "Apple", section).save(path)
    return path


def _noisy_page(directory: Path) -> Path:
    """Line art contaminated with a light gray wash — a 'not pure binary' defect."""
    path = directory / "raw_p006_banana.png"
    img = Image.new("L", (2550, 3300), 255)
    draw = ImageDraw.Draw(img)
    draw.rectangle((500, 700, 2050, 2600), outline=0, width=26)
    draw.ellipse((1000, 1200, 1600, 1800), fill=205, outline=0, width=20)
    img.save(path)
    return path


def test_rescue_binarize_cleans_gray_noise(tmp_path: Path):
    raw = _noisy_page(tmp_path)
    out = tmp_path / "rescued.png"

    result = rescue_binarize(raw, output_path=out, use_otsu=True)

    assert result.success is True
    assert result.method_applied == "OTSU_ADAPTIVE_BINARIZATION"
    assert result.original_non_binary_pixels > 0
    assert Path(result.output_path) == out
    assert out.exists()

    with Image.open(out) as img:
        assert img.mode == "L"
        # Every pixel is now pure black or pure white
        assert set(np.unique(np.array(img)).tolist()) <= {0, 255}


def test_rescue_binarize_missing_input_reports_failure(tmp_path: Path):
    result = rescue_binarize(tmp_path / "does_not_exist.png")

    assert result.success is False
    assert result.method_applied == "NONE"
    assert result.cleaned_pixels_count == 0


def test_margin_fit_centers_artwork_within_safe_margins(tmp_path: Path):
    out = tmp_path / "fitted.png"

    result = fit_to_safe_margins(_raw_page(tmp_path), output_path=out)

    assert result.success is True
    assert result.target_canvas_size == _CANVAS
    assert result.left_margin_px >= _SAFE_MARGIN_PX
    assert result.right_margin_px >= _SAFE_MARGIN_PX
    assert result.top_margin_px >= _SAFE_MARGIN_PX
    assert result.bottom_margin_px >= _SAFE_MARGIN_PX
    # Non-spread pages cap upscaling so the header zone stays usable
    assert result.scale_factor <= 1.25

    with Image.open(out) as img:
        assert img.size == _CANVAS


def test_margin_fit_rejects_blank_artwork(tmp_path: Path):
    blank = tmp_path / "blank.png"
    Image.new("L", (600, 600), 255).save(blank)

    result = fit_to_safe_margins(blank, output_path=tmp_path / "out.png")

    assert result.success is False
    assert result.original_bbox == (0, 0, 0, 0)


def test_programmatic_rescue_recovers_geometry_from_a_real_raw_page(tmp_path: Path):
    """Rescue repairs size and margins in-code, without spending an API call."""
    raw = _raw_page(tmp_path)
    rescued = tmp_path / "temp_rescued_005.png"

    passed, message, violations = RetryManager().attempt_programmatic_rescue(raw, rescued)

    assert rescued.exists()
    with Image.open(rescued) as img:
        assert img.size == _CANVAS
        assert img.mode == "L"

    # Geometry is fully repaired ...
    assert validate_dimensions(rescued).passed is True
    assert validate_margins(rescued).passed is True

    # ... but LANCZOS rescaling leaves gray ramps on the resampled edges, so the
    # rescue stage reports itself as partial rather than pristine.
    assert passed is False
    assert "could not fully resolve" in message
    assert any("Gray Shading" in v for v in violations)


def test_programmatic_rescue_escalates_on_missing_input(tmp_path: Path):
    passed, message, violations = RetryManager().attempt_programmatic_rescue(
        tmp_path / "absent.png", tmp_path / "out.png"
    )

    assert passed is False
    assert violations == ["RESCUE_BINARIZE_FAILED"]
    assert "binarization" in message.lower()


def test_typography_overlay_repairs_the_rescue_grays(tmp_path: Path):
    """The compositor re-thresholds the artwork, so the published master is pure B&W."""
    rescued = tmp_path / "temp_rescued_005.png"
    RetryManager().attempt_programmatic_rescue(_raw_page(tmp_path), rescued)
    assert validate_black_and_white(rescued).passed is False  # gray ramps remain

    master = tmp_path / "page_005.png"
    composite_typography(image_input=rescued, display_label="APPLE", output_path=master)

    assert validate_dimensions(master).passed is True
    assert validate_margins(master).passed is True
    assert validate_black_and_white(master).passed is True
