"""Unit tests for programmatic typography, brand, cover, and PDF compositors."""

import pytest
from pathlib import Path
from PIL import Image, ImageDraw

from curiokraft_book.compositor.typography import composite_typography
from curiokraft_book.compositor.brand import get_brand_logo, get_brand_emblem
from curiokraft_book.compositor.cover import composite_kdp_cover
from curiokraft_book.compositor.interior_pdf import compile_interior_pdf
from curiokraft_book.validators.pdf import validate_interior_pdf


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def sample_raw_page(temp_dir: Path) -> Path:
    """Create a 2550x3300 px 300 DPI test page with an apple drawing."""
    img_path = temp_dir / "sample_raw.png"
    img = Image.new("L", (2550, 3300), 255)
    draw = ImageDraw.Draw(img)
    draw.ellipse([800, 1000, 1750, 2400], outline=0, width=25)
    img.save(img_path, dpi=(300, 300))
    return img_path


def test_composite_typography(sample_raw_page: Path, temp_dir: Path):
    out_path = temp_dir / "page_005_titled.png"
    result = composite_typography(
        image_input=sample_raw_page,
        display_label="BANANA",
        output_path=out_path
    )
    assert result.success is True
    assert result.display_label == "BANANA"
    assert out_path.exists()

    with Image.open(out_path) as res_img:
        assert res_img.size == (2550, 3300)
        dpi = res_img.info.get("dpi", (300, 300))
        assert int(round(dpi[0])) == 300
        assert int(round(dpi[1])) == 300


def test_brand_logo_and_emblem():
    logo = get_brand_logo(target_width_px=500)
    assert logo is not None
    assert logo.width == 500

    emblem = get_brand_emblem(target_size_px=180)
    assert emblem is not None
    assert emblem.size == (180, 180)


def test_composite_kdp_cover(temp_dir: Path):
    cover_png = temp_dir / "test_cover.png"
    cover_pdf = temp_dir / "test_cover.pdf"

    result = composite_kdp_cover(
        output_png_path=cover_png,
        output_pdf_path=cover_pdf,
        title="TINY HANDS COLOR & LEARN",
        subtitle="FUN & EASY FIRST WORDS",
        brand_name="CURIOKRAFT-KIDS"
    )

    assert result.success is True
    assert cover_png.exists()
    assert cover_pdf.exists()
    assert result.canvas_dimensions_px == (5249, 3375)
    assert result.spine_width_px == 74


def test_compile_interior_pdf(temp_dir: Path, sample_raw_page: Path):
    # Test compilation with a mini batch of 3 pages (expected_page_count=3 for test)
    page_paths = [sample_raw_page, sample_raw_page, sample_raw_page]
    pdf_path = temp_dir / "test_mini_interior.pdf"

    result = compile_interior_pdf(
        image_paths=page_paths,
        output_pdf_path=pdf_path,
        expected_page_count=3
    )

    assert result.success is True
    assert pdf_path.exists()
    assert result.total_pages_compiled == 3
    assert result.validation.passed is True
