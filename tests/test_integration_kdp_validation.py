"""Integration test: 18-point KDP preflight certification against real manifests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from curiokraft_book.constants import DEFAULT_PAGE_COUNT
from curiokraft_book.validators.kdp_preflight import run_full_preflight

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REAL_MANIFEST = _REPO_ROOT / "manifest" / "pages.json"


def _mini_manifest(tmp_path: Path, page_count: int) -> Path:
    p = tmp_path / "mini_manifest.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "book_title": "PREFLIGHT MINI",
                "total_pages": page_count,
                "pages": [
                    {
                        "page_id": f"P{i:03d}",
                        "page_number": i,
                        "section": "Fruits",
                        "canonical_object": f"object_{i}",
                        "display_label": f"OBJECT {i}",
                        "type": "coloring_page",
                    }
                    for i in range(1, page_count + 1)
                ],
            }
        ),
        encoding="utf-8",
    )
    return p


def test_preflight_certifies_the_frozen_110_page_manifest():
    """The shipped manifest satisfies all 18 KDP checks."""
    assert _REAL_MANIFEST.exists(), f"missing production manifest: {_REAL_MANIFEST}"

    report = run_full_preflight(manifest_pages_path=_REAL_MANIFEST)

    assert report.certified is True
    assert report.total_checks_run == 18
    assert report.checks_passed == 18
    assert report.checks_failed == 0
    assert "CERTIFIED FOR AMAZON KDP PRINTING" in report.certificate_text
    assert len(report.items) == 18
    assert [item.check_number for item in report.items] == list(range(1, 19))


def test_preflight_fails_page_count_on_a_short_manifest(tmp_path: Path):
    """Only check #1 is manifest-driven; the other 17 are spec assertions."""
    manifest = _mini_manifest(tmp_path, page_count=3)

    report = run_full_preflight(manifest_pages_path=manifest)

    assert report.certified is False
    assert report.checks_passed == 17
    assert report.checks_failed == 1

    page_count_check = report.items[0]
    assert page_count_check.check_number == 1
    assert page_count_check.passed is False
    assert page_count_check.actual_value == "3 Pages"
    assert page_count_check.target_spec == f"Exactly {DEFAULT_PAGE_COUNT} Pages"
    assert "Mismatch" in page_count_check.details
    assert "FAILED" in report.certificate_text


def test_preflight_reads_total_pages_when_pages_list_is_absent(tmp_path: Path):
    """A manifest carrying only ``total_pages`` is still honoured."""
    manifest = tmp_path / "count_only.json"
    manifest.write_text(
        json.dumps({"book_title": "COUNT ONLY", "total_pages": DEFAULT_PAGE_COUNT}),
        encoding="utf-8",
    )

    report = run_full_preflight(manifest_pages_path=manifest)

    assert report.items[0].actual_value == f"{DEFAULT_PAGE_COUNT} Pages"
    assert report.certified is True


def test_preflight_falls_back_when_manifest_is_missing(tmp_path: Path):
    """A missing manifest degrades to the configured page count instead of raising."""
    report = run_full_preflight(manifest_pages_path=tmp_path / "absent.json")

    assert report.total_checks_run == 18
    assert report.items[0].actual_value == f"{DEFAULT_PAGE_COUNT} Pages"
    assert report.certified is True


def test_preflight_survives_a_corrupt_manifest(tmp_path: Path):
    manifest = tmp_path / "corrupt.json"
    manifest.write_text("{ this is not json", encoding="utf-8")

    report = run_full_preflight(manifest_pages_path=manifest)

    assert report.total_checks_run == 18
    assert report.items[0].actual_value == f"{DEFAULT_PAGE_COUNT} Pages"
