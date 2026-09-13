"""Unit tests for ``validators/kdp_preflight.py`` — the 18-point KDP preflight.

**What this module actually does.** Despite the "diagnostic suite" name and the
six path arguments, only check #1 is computed, and only from the manifest's page
count. Checks #2-#18 are hard-coded literals with ``passed=True`` and static
detail strings; the six path arguments (interior/cover PDFs, PNG, objects
registry, masters dir) are accepted and then never read. Likewise ``book_title``
and ``publisher`` come from module constants, not the manifest.

These tests pin that behaviour deliberately: if someone later wires up real
checks, the assertions below are what should change.
"""

from __future__ import annotations

import json
from pathlib import Path

from curiokraft_book.constants import (
    DEFAULT_BOOK_TITLE,
    DEFAULT_IMPRINT,
    DEFAULT_PAGE_COUNT,
)
from curiokraft_book.validators.kdp_preflight import (
    MasterPreflightReport,
    run_full_preflight,
)


def _manifest(tmp_path: Path, page_count: int, name: str = "pages.json") -> Path:
    """Write a manifest with ``page_count`` pages."""
    path = tmp_path / name
    path.write_text(
        json.dumps(
            {
                "pages": [
                    {"page_id": f"P{i:03d}", "page_number": i} for i in range(1, page_count + 1)
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def _run(tmp_path: Path, manifest: Path | None = None) -> MasterPreflightReport:
    return run_full_preflight(
        manifest_pages_path=manifest if manifest is not None else tmp_path / "absent.json"
    )


def _check(report: MasterPreflightReport, number: int):
    return next(item for item in report.items if item.check_number == number)


# ----------------------------------------------------------------------
# Structure
# ----------------------------------------------------------------------


def test_always_reports_eighteen_checks(tmp_path: Path):
    report = _run(tmp_path, _manifest(tmp_path, DEFAULT_PAGE_COUNT))

    assert report.total_checks_run == 18
    assert len(report.items) == 18
    assert [item.check_number for item in report.items] == list(range(1, 19))


def test_checks_two_through_eighteen_are_unconditional(tmp_path: Path):
    """Checks #2-#18 are literals: they pass regardless of check #1's verdict.

    This is the honest characterisation of the module, not a bug to fix here.
    """
    report = _run(tmp_path, _manifest(tmp_path, page_count=1))

    assert _check(report, 1).passed is False
    for number in range(2, 19):
        assert _check(report, number).passed is True, f"check #{number} was expected to be static"


def test_title_and_publisher_come_from_constants_not_manifest(tmp_path: Path):
    manifest = tmp_path / "pages.json"
    manifest.write_text(
        json.dumps(
            {
                "book_title": "A DIFFERENT TITLE",
                "publisher": "SOMEONE ELSE",
                "pages": [{"page_id": "P001"}],
            }
        ),
        encoding="utf-8",
    )
    report = run_full_preflight(manifest_pages_path=manifest)

    assert report.book_title == DEFAULT_BOOK_TITLE
    assert report.publisher == DEFAULT_IMPRINT


# ----------------------------------------------------------------------
# Check #1 — the only computed check
# ----------------------------------------------------------------------


def test_matching_page_count_certifies(tmp_path: Path):
    report = _run(tmp_path, _manifest(tmp_path, DEFAULT_PAGE_COUNT))

    assert _check(report, 1).passed is True
    assert report.certified is True
    assert report.checks_passed == 18
    assert report.checks_failed == 0
    assert "CERTIFIED FOR AMAZON KDP PRINTING" in report.certificate_text


def test_mismatched_page_count_fails_check_one_only(tmp_path: Path):
    report = _run(tmp_path, _manifest(tmp_path, DEFAULT_PAGE_COUNT - 1))

    first = _check(report, 1)
    assert first.passed is False
    assert first.actual_value == f"{DEFAULT_PAGE_COUNT - 1} Pages"
    assert "Mismatch" in first.details
    assert report.certified is False
    assert report.checks_passed == 17
    assert report.checks_failed == 1
    assert "FAILED" in report.certificate_text


def test_manifest_total_pages_field_used_when_pages_list_absent(tmp_path: Path):
    """Falls back to the ``total_pages`` scalar when ``pages`` is missing/empty."""
    path = tmp_path / "scalar.json"
    path.write_text(json.dumps({"total_pages": 7}), encoding="utf-8")
    report = run_full_preflight(manifest_pages_path=path)

    assert _check(report, 1).actual_value == "7 Pages"
    assert report.certified is False


def test_manifest_total_pages_field_used_when_pages_list_empty(tmp_path: Path):
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"pages": [], "total_pages": 3}), encoding="utf-8")
    report = run_full_preflight(manifest_pages_path=path)

    assert _check(report, 1).actual_value == "3 Pages"


def test_pages_list_takes_precedence_over_total_pages_scalar(tmp_path: Path):
    path = tmp_path / "both.json"
    path.write_text(
        json.dumps({"pages": [{"page_id": "P001"}, {"page_id": "P002"}], "total_pages": 99}),
        encoding="utf-8",
    )
    report = run_full_preflight(manifest_pages_path=path)

    assert _check(report, 1).actual_value == "2 Pages"


def test_empty_pages_list_without_total_pages_falls_back_to_default(tmp_path: Path):
    """A present-but-empty ``pages`` list is falsy, so the default survives.

    Worth pinning: an empty manifest is silently treated as a complete
    110-page book and certifies, rather than failing check #1.
    """
    path = tmp_path / "empty_no_scalar.json"
    path.write_text(json.dumps({"pages": []}), encoding="utf-8")
    report = run_full_preflight(manifest_pages_path=path)

    assert _check(report, 1).passed is True
    assert _check(report, 1).actual_value == f"{DEFAULT_PAGE_COUNT} Pages"
    assert report.certified is True


# ----------------------------------------------------------------------
# Fallbacks
# ----------------------------------------------------------------------


def test_missing_manifest_falls_back_to_default_page_count(tmp_path: Path):
    """The ``m_path.exists()`` False branch keeps the default page count."""
    report = run_full_preflight(manifest_pages_path=tmp_path / "does_not_exist.json")

    assert _check(report, 1).passed is True
    assert _check(report, 1).actual_value == f"{DEFAULT_PAGE_COUNT} Pages"
    assert report.certified is True


def test_corrupt_manifest_json_is_swallowed(tmp_path: Path):
    """A malformed manifest is swallowed by a bare ``except`` and defaulted."""
    path = tmp_path / "corrupt.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    report = run_full_preflight(manifest_pages_path=path)

    assert _check(report, 1).passed is True
    assert _check(report, 1).actual_value == f"{DEFAULT_PAGE_COUNT} Pages"


def test_non_numeric_total_pages_is_swallowed(tmp_path: Path):
    """An unparseable ``total_pages`` raises inside the try and is swallowed."""
    path = tmp_path / "bad_scalar.json"
    path.write_text(json.dumps({"total_pages": "many"}), encoding="utf-8")
    report = run_full_preflight(manifest_pages_path=path)

    assert _check(report, 1).actual_value == f"{DEFAULT_PAGE_COUNT} Pages"


# ----------------------------------------------------------------------
# Certificate text
# ----------------------------------------------------------------------


def test_certificate_contains_computed_cover_dimensions(tmp_path: Path):
    report = _run(tmp_path, _manifest(tmp_path, DEFAULT_PAGE_COUNT))

    text = report.certificate_text
    assert "CURIOKRAFT PUBLICATIONS" in text
    assert DEFAULT_BOOK_TITLE in text
    assert DEFAULT_IMPRINT in text
    # cover dims are formatted from calculate_kdp_cover_dimensions(total_pages)
    assert "17.498 x 11.250 in" in text
    assert "Spine: 0.248 in" in text
    assert f"Pages:     {DEFAULT_PAGE_COUNT} Pages" in text
    assert "Checks:    18/18 Passed" in text


def test_certificate_reports_failure_count_when_uncertified(tmp_path: Path):
    report = _run(tmp_path, _manifest(tmp_path, page_count=5))

    assert "Result:    FAILED" in report.certificate_text
