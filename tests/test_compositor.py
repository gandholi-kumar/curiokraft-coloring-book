"""Unit tests for programmatic typography, brand, cover, and PDF compositors."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from curiokraft_book.compositor.brand import (
    create_publisher_badge,
    get_brand_emblem,
    get_brand_logo,
)
from curiokraft_book.compositor.cover import composite_kdp_cover
from curiokraft_book.compositor.interior_pdf import compile_interior_pdf
from curiokraft_book.compositor.typography import composite_typography


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
        image_input=sample_raw_page, display_label="BANANA", output_path=out_path
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


def test_create_publisher_badge():
    badge_patch, pad_px = create_publisher_badge(
        card_w=640,
        card_h=420,
        radius=28,
        offset_x=16,
        offset_y=20,
        blur_radius=20,
        shadow_alpha=95,
    )
    assert badge_patch is not None
    assert pad_px > 0
    assert badge_patch.width == 640 + pad_px * 2
    assert badge_patch.height == 420 + pad_px * 2


def test_composite_kdp_cover(temp_dir: Path):
    cover_png = temp_dir / "test_cover.png"
    cover_pdf = temp_dir / "test_cover.pdf"

    result = composite_kdp_cover(
        output_png_path=cover_png,
        output_pdf_path=cover_pdf,
        title="TINY HANDS COLOR & LEARN",
        subtitle="FUN & EASY FIRST WORDS",
        brand_name="CURIOKRAFT-KIDS",
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
        image_paths=page_paths, output_pdf_path=pdf_path, expected_page_count=3
    )

    assert result.success is True
    assert pdf_path.exists()
    assert result.total_pages_compiled == 3
    assert result.validation.passed is True


def test_render_special_pages(temp_dir: Path):
    from curiokraft_book.compositor.special_pages import (
        render_certificate_page,
        render_welcome_page,
    )

    p001_out = temp_dir / "page_001.png"
    res1 = render_welcome_page(output_path=str(p001_out))
    assert res1.exists()
    with Image.open(res1) as img1:
        assert img1.size == (2550, 3300)
        assert img1.mode == "L"
        dpi = img1.info.get("dpi", (300, 300))
        assert int(round(dpi[0])) >= 300

    p110_out = temp_dir / "page_110.png"
    res110 = render_certificate_page(output_path=str(p110_out))
    assert res110.exists()
    with Image.open(res110) as img110:
        assert img110.size == (2550, 3300)
        assert img110.mode == "L"
        dpi = img110.info.get("dpi", (300, 300))
        assert int(round(dpi[0])) >= 300


def test_archive_processed_special_assets(temp_dir: Path):
    from curiokraft_book.compositor.special_pages import archive_processed_special_assets

    inbox_dir = temp_dir / "inbox_special"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    dest_dir = temp_dir / "assets_special" / "vol_test"

    # Create dummy special assets in inbox
    sample_mascot = inbox_dir / "test_mascot.png"
    img = Image.new("RGBA", (400, 400), (255, 255, 255, 255))
    img.save(sample_mascot)
    assert sample_mascot.exists()

    moved = archive_processed_special_assets(
        volume="vol_test",
        dest_dir=dest_dir,
        inbox_dir=inbox_dir,
    )

    assert len(moved) == 1
    assert not sample_mascot.exists()
    assert (dest_dir / "test_mascot.png").exists()


def test_kdp_form_privacy_protection():
    """Verify that KDP HTML forms are protected by .gitignore and never tracked by Git."""
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists(), ".gitignore file must exist"
    gi_text = gitignore_path.read_text(encoding="utf-8")

    assert "inbox/kdp_forms/*.html" in gi_text, "inbox/kdp_forms/*.html must be ignored"
    assert "inbox/kdp_forms/*.htm" in gi_text, "inbox/kdp_forms/*.htm must be ignored"
    assert "!inbox/kdp_forms/README.md" in gi_text, "README.md must be kept tracked"


def test_special_pages_borders_and_helpers(tmp_path: Path):
    from curiokraft_book.compositor.special_pages import (
        BOOK_THEME,
        _draw_border_certificate,
        _draw_border_welcome,
        _draw_star,
        _load_contoured_mascot,
    )

    canvas = Image.new("L", (2550, 3300), 255)
    draw = ImageDraw.Draw(canvas)

    _draw_star(draw, 200, 200, 30, fill=0)
    _draw_border_welcome(draw, {**BOOK_THEME, "canvas_w": 2550, "canvas_h": 3300}, is_aquatic=False)
    _draw_border_certificate(draw, {**BOOK_THEME, "canvas_w": 2550, "canvas_h": 3300})

    # Test mascot contouring
    mascot_img = tmp_path / "mascot.png"
    m_canvas = Image.new("RGB", (300, 300), (255, 255, 255))
    m_draw = ImageDraw.Draw(m_canvas)
    m_draw.ellipse([50, 50, 250, 250], fill=(50, 50, 50))
    m_canvas.save(mascot_img)

    contoured = _load_contoured_mascot(mascot_img)
    assert contoured is not None
    m_gray, m_mask = contoured
    assert m_gray.mode == "L"
    assert m_mask.mode == "L"


def test_special_pages_render_programmatic(sandbox_cwd, tmp_path: Path):
    from curiokraft_book.compositor.special_pages import (
        render_certificate_page,
        render_welcome_page,
    )

    p1 = tmp_path / "page_001.png"
    p109 = tmp_path / "page_109.png"

    res1 = render_welcome_page(output_path=p1)
    assert res1.exists()

    res2 = render_certificate_page(output_path=p109)
    assert res2.exists()


def test_special_pages_render_toddler(sandbox_cwd, tmp_path: Path, monkeypatch):
    from curiokraft_book.compositor.special_pages import (
        render_certificate_page,
        render_welcome_page,
    )

    monkeypatch.setattr("curiokraft_book.compositor.special_pages.DEFAULT_BOOK_VOLUME", "vol_1")
    p1 = tmp_path / "page_001_toddler.png"
    p109 = tmp_path / "page_109_toddler.png"

    res1 = render_welcome_page(output_path=p1, title="Toddler First Animals")
    assert res1.exists()

    res2 = render_certificate_page(output_path=p109, title="Toddler First Animals")
    assert res2.exists()


def test_special_pages_ingest_raw_full_page(tmp_path: Path):
    from curiokraft_book.compositor.special_pages import _ingest_raw_full_page

    raw = tmp_path / "raw_artwork.png"
    img = Image.new("RGBA", (1000, 1200), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 900, 1100], outline=0, width=10)
    img.save(raw)

    result = _ingest_raw_full_page(raw, canvas_w=1275, canvas_h=1650, dpi=150)
    assert result.size == (1275, 1650)
    assert result.mode == "L"
