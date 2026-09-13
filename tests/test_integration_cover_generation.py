"""Integration test: cover discovery, cover debate prompts, and KDP cover compositing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from curiokraft_book.compositor.cover import composite_kdp_cover
from curiokraft_book.constants import DEFAULT_PAGE_COUNT
from curiokraft_book.orchestrator.debate_engine import (
    extract_front_cover_ensemble,
    generate_back_cover_prompt,
    generate_front_cover_prompt,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BOOK_CONFIG = _REPO_ROOT / "config" / "book_config.yaml"
_CURRICULUM_CONFIG = _REPO_ROOT / "config" / "curriculum.yaml"


def _manifest(tmp_path: Path, pages: list[tuple[str, int, str, str, str]]) -> Path:
    p = tmp_path / "cover_manifest.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "book_title": "COVER MINI",
                "total_pages": len(pages),
                "pages": [
                    {
                        "page_id": pid,
                        "page_number": num,
                        "section": section,
                        "canonical_object": canonical,
                        "display_label": label,
                        "type": "coloring_page",
                    }
                    for pid, num, section, canonical, label in pages
                ],
            }
        ),
        encoding="utf-8",
    )
    return p


_THEMED_PAGES = [
    ("P001", 1, "Welcome", "panda", "PANDA"),
    ("P005", 5, "Animals", "elephant", "ELEPHANT"),
    ("P006", 6, "Fruits", "apple", "APPLE"),
    ("P007", 7, "Vehicles", "truck", "TRUCK"),
]


def test_extract_front_cover_ensemble_discovers_hero_and_companions(tmp_path: Path):
    manifest = _manifest(tmp_path, _THEMED_PAGES)

    hero, companions, page_count = extract_front_cover_ensemble(str(manifest))

    # The mascot priority list picks the elephant over the welcome-page panda
    assert "elephant" in hero
    assert "crayon" in hero
    assert page_count == 4
    # One fruit companion, one vehicle companion, plus the fixed rainbow
    assert len(companions) == 3
    assert any("apple" in c for c in companions)
    assert any("truck" in c for c in companions)
    assert any("rainbow" in c for c in companions)


def test_extract_front_cover_ensemble_falls_back_for_a_non_living_manifest(tmp_path: Path):
    manifest = _manifest(
        tmp_path,
        [("P005", 5, "Objects", "chair", "CHAIR"), ("P006", 6, "Objects", "table", "TABLE")],
    )

    hero, companions, page_count = extract_front_cover_ensemble(str(manifest))

    assert "chair" not in hero and "table" not in hero
    assert "mascot" in hero
    assert page_count == 2
    assert companions == [
        "a vibrant multi-colored arching rainbow emerging from two fluffy white cumulus clouds"
    ]


def test_extract_front_cover_ensemble_ignores_a_corrupt_manifest(tmp_path: Path):
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{ not json at all", encoding="utf-8")

    hero, companions, page_count = extract_front_cover_ensemble(str(corrupt))

    assert "mascot" in hero
    assert page_count == DEFAULT_PAGE_COUNT
    assert len(companions) == 1


def test_cover_prompts_are_synthesized_offline(tmp_path: Path):
    """Front/back cover debate runs without any LLM call and yields distinct prompts."""
    manifest = _manifest(tmp_path, _THEMED_PAGES)

    front_pos, front_neg = generate_front_cover_prompt(
        book_config_path=str(_BOOK_CONFIG), manifest_path=str(manifest)
    )
    back_pos, back_neg = generate_back_cover_prompt(
        book_config_path=str(_BOOK_CONFIG), manifest_path=str(manifest)
    )

    assert front_pos.strip() and front_neg.strip()
    assert back_pos.strip() and back_neg.strip()
    assert front_pos != back_pos
    # Negative prompts are comma-separated forbidden-token lists
    assert "," in front_neg
    assert "" not in [t.strip() for t in front_neg.split(",")]


def test_cover_prompt_rejects_a_missing_book_config(tmp_path: Path):
    """The debate engine refuses to invent a book identity — config is mandatory."""
    manifest = _manifest(tmp_path, _THEMED_PAGES)

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        generate_front_cover_prompt(
            book_config_path=str(tmp_path / "absent.yaml"), manifest_path=str(manifest)
        )


def test_composite_kdp_cover_produces_a_print_ready_wrap(tmp_path: Path):
    """With no artwork in the inbox the compositor draws its procedural placeholder."""
    manifest = _manifest(tmp_path, _THEMED_PAGES)
    cover_png = tmp_path / "cover" / "cover_300DPI.png"

    result = composite_kdp_cover(
        output_png_path=cover_png,
        output_pdf_path=None,
        manifest_path=manifest,
        book_config_path=_BOOK_CONFIG,
        curriculum_config_path=_CURRICULUM_CONFIG,
        page_count=DEFAULT_PAGE_COUNT,
    )

    assert result.success is True
    assert result.violations == []
    assert result.canvas_dimensions_px == (5249, 3375)  # 17.498 x 11.250 in @ 300 DPI
    assert result.spine_width_px == 74
    assert result.overall_width_in == pytest.approx(17.498, abs=0.01)
    assert result.overall_height_in == pytest.approx(11.250, abs=0.01)
    # Spine sits dead centre of the wrap
    assert result.spine_center_x_px == 5249 // 2

    assert cover_png.exists()
    with Image.open(cover_png) as img:
        assert img.size == result.canvas_dimensions_px
        assert img.mode == "RGB"
