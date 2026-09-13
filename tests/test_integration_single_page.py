"""Integration test: full single-page pipeline (debate -> generate -> composite)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner

pytestmark = pytest.mark.integration


def _manifest(tmp_path: Path) -> Path:
    p = tmp_path / "mini_manifest.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "book_title": "INTEGRATION MINI",
                "total_pages": 1,
                "pages": [
                    {
                        "page_id": "P005",
                        "page_number": 5,
                        "section": "Fruits",
                        "canonical_object": "banana",
                        "display_label": "BANANA",
                        "type": "coloring_page",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return p


def test_single_page_end_to_end(sandbox_cwd: Path):
    """One page goes debate -> prompt lock -> mock raster -> master PNG."""
    tmp_path = sandbox_cwd
    manifest = _manifest(tmp_path)
    runner = InteriorBatchRunner(
        manifest_path=manifest,
        output_masters_dir=tmp_path / "masters",
        raw_generated_dir=tmp_path / "raw",
    )

    page = json.loads(manifest.read_text(encoding="utf-8"))["pages"][0]
    master = runner.generate_single_page(page, source_mode="mock")

    assert master.exists()
    assert master.name == "page_005.png"
    with Image.open(master) as img:
        assert img.size == (2550, 3300)
        assert img.mode == "L"

    # Raw artifact is preserved alongside the composite master
    raw = tmp_path / "raw" / "raw_p005_banana.png"
    assert raw.exists()
    assert raw.stat().st_size > 500

    # State manager recorded the page as approved
    record = runner.state_mgr.get_page("P005")
    assert record is not None
    assert record.composite_image_path == str(master)
