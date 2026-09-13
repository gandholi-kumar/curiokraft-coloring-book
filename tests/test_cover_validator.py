"""Unit tests for ``validators/cover_validator.py`` (KDP full-wrap cover check).

The module was previously untested. These tests pin each of its four checks
independently, plus the two early-return / report-writing branches.

Note the real API: ``dpi`` on the result is a ``tuple[int, int]``, and the
default ``report_output_path`` is a *relative* path, so every call here passes
an explicit ``tmp_path`` location to stay isolated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from curiokraft_book.validators.cover_validator import (
    CoverValidationResult,
    validate_kdp_cover,
)

DPI = 300
WIDTH_PX = 5249  # round(17.498 * 300)
HEIGHT_PX = 3375  # round(11.250 * 300)
SPINE_WIDTH_IN = 0.248


def _barcode_box(width: int, height: int) -> tuple[int, int, int, int]:
    """Recompute the barcode exclusion box exactly as the module does."""
    spine_center_x = width // 2
    spine_left_x = spine_center_x - int(round((SPINE_WIDTH_IN * DPI) / 2))
    bx1 = spine_left_x - 600 - 150
    by1 = height - 360 - 150
    return bx1, by1, bx1 + 600, by1 + 360


def make_cover(
    tmp_path: Path,
    *,
    width_px: int = WIDTH_PX,
    height_px: int = HEIGHT_PX,
    dpi: tuple[int, int] = (DPI, DPI),
    fill: int = 255,
    name: str = "cover.png",
) -> Path:
    """Write a synthetic single-channel cover image."""
    path = tmp_path / name
    Image.new("L", (width_px, height_px), fill).save(path, dpi=dpi)
    return path


def validate(cover_path: Path, tmp_path: Path, **kwargs) -> CoverValidationResult:
    """Call the validator with an isolated report path unless overridden."""
    kwargs.setdefault("report_output_path", tmp_path / "report.json")
    return validate_kdp_cover(cover_path, **kwargs)


# ----------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------


def test_valid_cover_passes(tmp_path: Path):
    cover = make_cover(tmp_path)
    result = validate(cover, tmp_path)

    assert result.passed is True
    assert result.kdp_compliant is True
    assert result.violations == []
    assert result.width_px == WIDTH_PX
    assert result.height_px == HEIGHT_PX
    assert result.dpi == (DPI, DPI)
    assert result.barcode_box_clear is True
    assert result.width_in == round(WIDTH_PX / DPI, 3)
    assert result.height_in == round(HEIGHT_PX / DPI, 3)
    assert (tmp_path / "report.json").exists()


def test_report_json_round_trips(tmp_path: Path):
    cover = make_cover(tmp_path)
    report = tmp_path / "custom_report.json"
    result = validate_kdp_cover(cover, report_output_path=report)

    assert report.exists()
    data = json.loads(report.read_text(encoding="utf-8"))
    # JSON has no tuple type, so the ``dpi`` pair serialises as a list.
    assert data["dpi"] == list(result.dpi)
    assert {k: v for k, v in data.items() if k != "dpi"} == {
        k: v for k, v in result.model_dump().items() if k != "dpi"
    }
    assert data["passed"] is True


def test_report_output_path_none_writes_nothing(tmp_path: Path):
    cover = make_cover(tmp_path)
    result = validate_kdp_cover(cover, report_output_path=None)

    assert result.passed is True
    assert list(tmp_path.glob("*.json")) == []


# ----------------------------------------------------------------------
# 1. Dimension tolerance (fails when off by more than 3 px)
# ----------------------------------------------------------------------


def test_width_mismatch_flags_violation(tmp_path: Path):
    cover = make_cover(tmp_path, width_px=WIDTH_PX - 9)
    result = validate(cover, tmp_path)

    assert result.passed is False
    assert result.kdp_compliant is False
    assert any("Cover Width Mismatch" in v for v in result.violations)
    assert not any("Cover Height Mismatch" in v for v in result.violations)


def test_height_mismatch_flags_violation(tmp_path: Path):
    cover = make_cover(tmp_path, height_px=HEIGHT_PX - 15)
    result = validate(cover, tmp_path)

    assert result.passed is False
    assert any("Cover Height Mismatch" in v for v in result.violations)
    assert not any("Cover Width Mismatch" in v for v in result.violations)


@pytest.mark.parametrize("offset", [0, 1, 2, 3])
def test_dimension_within_three_px_tolerance_passes(tmp_path: Path, offset: int):
    """The documented tolerance is ±3 px; the boundary itself must still pass."""
    cover = make_cover(tmp_path, width_px=WIDTH_PX + offset, height_px=HEIGHT_PX - offset)
    result = validate(cover, tmp_path)

    assert result.passed is True, result.violations


def test_dimension_just_outside_tolerance_fails(tmp_path: Path):
    cover = make_cover(tmp_path, width_px=WIDTH_PX + 4)
    result = validate(cover, tmp_path)

    assert result.passed is False
    assert any("Cover Width Mismatch" in v for v in result.violations)


# ----------------------------------------------------------------------
# 2. DPI verification
# ----------------------------------------------------------------------


def test_dpi_mismatch_flags_violation(tmp_path: Path):
    cover = make_cover(tmp_path, dpi=(72, 72))
    result = validate(cover, tmp_path)

    assert result.passed is False
    assert result.dpi == (72, 72)
    assert any("Cover DPI Mismatch" in v for v in result.violations)


# ----------------------------------------------------------------------
# 3. Barcode exclusion box
# ----------------------------------------------------------------------


def test_barcode_box_dark_pixels_fail(tmp_path: Path):
    cover = make_cover(tmp_path)
    bx1, by1, bx2, by2 = _barcode_box(WIDTH_PX, HEIGHT_PX)
    with Image.open(cover) as img:
        # The check thresholds the *mean* brightness of the whole 600x360 box
        # at >200, so the ink must cover a large share of it: a 500x300 patch
        # drops the mean to roughly 78, well under the threshold.
        ImageDraw.Draw(img).rectangle([bx1 + 50, by1 + 30, bx1 + 550, by1 + 330], fill=0)
        img.save(cover)

    result = validate(cover, tmp_path)

    assert result.passed is False
    assert result.barcode_box_clear is False
    assert any("Barcode Zone Obstructed" in v for v in result.violations)


def test_dark_pixels_outside_barcode_box_are_ignored(tmp_path: Path):
    """Ink elsewhere on the cover must not trip the barcode check."""
    cover = make_cover(tmp_path)
    bx1, by1, bx2, by2 = _barcode_box(WIDTH_PX, HEIGHT_PX)
    with Image.open(cover) as img:
        # Top-left corner, far from both the barcode box and the margins check
        ImageDraw.Draw(img).rectangle([0, 0, 400, 400], fill=0)
        img.save(cover)

    result = validate(cover, tmp_path)

    assert result.barcode_box_clear is True
    # this validator does not inspect margins, so the cover still passes
    assert result.passed is True


def test_spine_center_reported(tmp_path: Path):
    cover = make_cover(tmp_path)
    result = validate(cover, tmp_path)

    assert result.spine_center_x_px == WIDTH_PX // 2


# ----------------------------------------------------------------------
# Early return: missing file
# ----------------------------------------------------------------------


def test_missing_file_early_return(tmp_path: Path):
    missing = tmp_path / "does_not_exist.png"
    report = tmp_path / "report.json"
    result = validate_kdp_cover(missing, report_output_path=report)

    assert result.passed is False
    assert result.kdp_compliant is False
    assert result.violations == [f"Cover file not found: {missing}"]
    assert result.cover_image_path == str(missing)
    assert (result.width_px, result.height_px) == (0, 0)
    assert result.dpi == (0, 0)
    assert result.barcode_box_clear is False
    # an unusable input must not produce a report
    assert not report.exists()


def test_missing_file_with_default_report_path_writes_nothing(tmp_path: Path):
    """Even the default report path must not be honoured on the early return."""
    missing = tmp_path / "nope.png"
    result = validate_kdp_cover(missing, report_output_path=tmp_path / "report.json")

    assert result.passed is False
    assert not (tmp_path / "report.json").exists()


# ----------------------------------------------------------------------
# Defensive branch: a non-tuple DPI tag
# ----------------------------------------------------------------------


def test_non_tuple_dpi_tag_falls_back_to_default(tmp_path: Path, monkeypatch):
    """A malformed ``dpi`` tag must not crash the validator.

    PIL normally hands back a ``(x, y)`` tuple, but the module guards against
    anything else (a scalar, a 1-tuple) and falls back to the 300 DPI default.
    """
    cover = make_cover(tmp_path)  # real file so ``path.exists()`` passes
    real = Image.open(cover)
    real.info["dpi"] = 300.0  # scalar rather than a tuple

    class _FakeHandle:
        def __enter__(self):
            return real

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(
        "curiokraft_book.validators.cover_validator.Image.open", lambda _p: _FakeHandle()
    )

    result = validate(cover, tmp_path)

    assert result.dpi == (300, 300)
    assert result.passed is True