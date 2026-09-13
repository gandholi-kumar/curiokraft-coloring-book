"""Integration test: full batch pipeline plus whole-book QA audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from curiokraft_book.agents.book_qa import run_book_qa_audit
from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner

pytestmark = pytest.mark.integration


_PAGES = [
    ("P001", 1, "Fruits", "apple", "APPLE"),
    ("P002", 2, "Fruits", "banana", "BANANA"),
    ("P003", 3, "Nature", "flower", "FLOWER"),
]


def _manifest(tmp_path: Path, pages: list[tuple[str, int, str, str, str]]) -> Path:
    p = tmp_path / "batch_manifest.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "book_title": "INTEGRATION BATCH",
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


def test_batch_pipeline_and_qa_audit(sandbox_cwd: Path):
    """A 3-page batch runs to completion and the whole-book audit passes."""
    tmp_path = sandbox_cwd
    manifest = _manifest(tmp_path, _PAGES)

    runner = InteriorBatchRunner(
        manifest_path=manifest,
        output_masters_dir=tmp_path / "masters",
        raw_generated_dir=tmp_path / "raw",
    )

    seen: list[tuple[int, int, str]] = []
    report = runner.run_full_book_batch(
        progress_callback=lambda cur, total, label: seen.append((cur, total, label)),
        source_mode="mock",
    )

    assert report.total_pages == 3
    assert report.successful_pages == 3
    assert report.failed_pages == 0
    assert [r["status"] for r in report.page_records] == ["APPROVED"] * 3
    # Progress callback fired once per page, ending on the final page
    assert len(seen) == 3
    assert seen[-1][0] == seen[-1][1] == 3

    for page_num in (1, 2, 3):
        master = tmp_path / "masters" / f"page_{page_num:03d}.png"
        assert master.exists()
        with Image.open(master) as img:
            assert img.size == (2550, 3300)
            assert img.mode == "L"
        # Temp rescue artifact is cleaned up after compositing
        assert not (tmp_path / "masters" / f"temp_rescued_{page_num:03d}.png").exists()

    qa = run_book_qa_audit(
        masters_dir=tmp_path / "masters",
        manifest_path=manifest,
        objects_registry_path=tmp_path / "objects.json",
        report_output_path=tmp_path / "reports" / "book_qa.json",
    )

    assert qa.audit_verdict == "PASSED"
    assert qa.ready_for_press is True
    assert qa.total_pages_audited == 3
    assert qa.passed_pages_count == 3
    assert qa.failed_pages_count == 0
    assert qa.duplicate_objects_found == 0
    assert qa.kdp_compliance_score == 100.0
    assert (tmp_path / "reports" / "book_qa.json").exists()


def test_batch_qa_audit_flags_missing_master(sandbox_cwd: Path):
    """An incomplete masters directory is reported as FAILED, not an exception."""
    tmp_path = sandbox_cwd
    manifest = _manifest(tmp_path, _PAGES)
    (tmp_path / "masters").mkdir()

    qa = run_book_qa_audit(
        masters_dir=tmp_path / "masters",
        manifest_path=manifest,
        objects_registry_path=tmp_path / "objects.json",
        report_output_path=tmp_path / "reports" / "book_qa.json",
    )

    assert qa.audit_verdict == "FAILED"
    assert qa.ready_for_press is False
    assert qa.failed_pages_count == 3
    assert qa.passed_pages_count == 0
    assert all("Missing master file" in v for audit in qa.pages_audit for v in audit.violations)


def test_batch_qa_audit_counts_duplicate_objects(sandbox_cwd: Path):
    """A repeated canonical object is detected as a duplicate collision."""
    tmp_path = sandbox_cwd
    dupes = [
        ("P001", 1, "Fruits", "apple", "APPLE"),
        ("P002", 2, "Fruits", "apple", "APPLE"),
    ]
    manifest = _manifest(tmp_path, dupes)

    runner = InteriorBatchRunner(
        manifest_path=manifest,
        output_masters_dir=tmp_path / "masters",
        raw_generated_dir=tmp_path / "raw",
    )
    runner.run_full_book_batch(source_mode="mock")

    qa = run_book_qa_audit(
        masters_dir=tmp_path / "masters",
        manifest_path=manifest,
        objects_registry_path=tmp_path / "objects.json",
        report_output_path=tmp_path / "reports" / "book_qa.json",
    )

    assert qa.duplicate_objects_found == 1
    assert qa.audit_verdict == "FAILED"
    # 100% page compliance, docked only by the duplicate penalty
    assert qa.kdp_compliance_score == 100.0
    assert qa.overall_readiness_score == 90.0
