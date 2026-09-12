"""PDF geometry, page count, and print-standard validator using PyMuPDF."""

from pathlib import Path

import pymupdf as fitz
from pydantic import BaseModel, Field

from curiokraft_book.constants import (
    DEFAULT_PAGE_COUNT,
    DEFAULT_TRIM_HEIGHT_IN,
    DEFAULT_TRIM_WIDTH_IN,
)


class PageDimensionInfo(BaseModel):
    """Geometry metrics for an individual PDF page."""

    page_number: int
    width_pt: float
    height_pt: float
    width_in: float
    height_in: float
    is_standard_letter: bool


class PDFValidationResult(BaseModel):
    """Result of comprehensive PDF preflight analysis."""

    passed: bool
    pdf_path: str
    total_pages: int
    expected_pages: int
    is_page_count_correct: bool
    all_pages_correct_size: bool
    has_blank_pages: bool
    blank_page_numbers: list[int] = Field(default_factory=list)
    pages_geometry: list[PageDimensionInfo] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)


def validate_interior_pdf(
    pdf_path: str | Path,
    expected_page_count: int = DEFAULT_PAGE_COUNT,
    expected_width_in: float = DEFAULT_TRIM_WIDTH_IN,
    expected_height_in: float = DEFAULT_TRIM_HEIGHT_IN,
    pt_tolerance: float = 2.0,
) -> PDFValidationResult:
    """Validate that an assembled interior PDF complies with KDP 8.5x11 110-page requirements.

    Args:
        pdf_path: Path to the assembled interior PDF file.
        expected_page_count: Expected exact page count (default: 110).
        expected_width_in: Expected page width in inches (default: 8.5 in = 612 pt).
        expected_height_in: Expected page height in inches (default: 11.0 in = 792 pt).
        pt_tolerance: Permitted size variance in PostScript points (default: 2.0 pt).

    Returns:
        PDFValidationResult with full page-by-page geometry analysis.
    """
    path = Path(pdf_path)
    if not path.exists():
        return PDFValidationResult(
            passed=False,
            pdf_path=str(path),
            total_pages=0,
            expected_pages=expected_page_count,
            is_page_count_correct=False,
            all_pages_correct_size=False,
            has_blank_pages=False,
            violations=[f"PDF file does not exist: {path}"],
        )

    expected_width_pt = expected_width_in * 72.0
    expected_height_pt = expected_height_in * 72.0

    violations = []
    pages_geometry = []
    blank_pages = []

    try:
        doc = fitz.open(str(path))
    except Exception as e:
        return PDFValidationResult(
            passed=False,
            pdf_path=str(path),
            total_pages=0,
            expected_pages=expected_page_count,
            is_page_count_correct=False,
            all_pages_correct_size=False,
            has_blank_pages=False,
            violations=[f"Failed to open PDF document: {e}"],
        )

    total_pages = len(doc)
    is_page_count_correct = total_pages == expected_page_count
    if not is_page_count_correct:
        violations.append(
            f"Page Count Mismatch: Expected exactly {expected_page_count} pages, found {total_pages} pages."
        )

    all_pages_correct_size = True

    for i in range(len(doc)):
        page = doc[i]
        page_num = i + 1
        rect = page.rect
        w_pt, h_pt = rect.width, rect.height
        w_in = round(w_pt / 72.0, 3)
        h_in = round(h_pt / 72.0, 3)

        width_ok = abs(w_pt - expected_width_pt) <= pt_tolerance
        height_ok = abs(h_pt - expected_height_pt) <= pt_tolerance
        is_letter = width_ok and height_ok

        if not is_letter:
            all_pages_correct_size = False
            violations.append(
                f"Page {page_num} Geometry Error: Expected {expected_width_in}x{expected_height_in}in ({expected_width_pt}x{expected_height_pt}pt), "
                f"got {w_in}x{h_in}in ({w_pt}x{h_pt}pt)."
            )

        # Check if page has zero drawings, text, and images (blank page)
        image_list = page.get_images()
        drawings = page.get_drawings()
        text = page.get_text().strip()

        if len(image_list) == 0 and len(drawings) == 0 and len(text) == 0:
            blank_pages.append(page_num)

        pages_geometry.append(
            PageDimensionInfo(
                page_number=page_num,
                width_pt=round(w_pt, 2),
                height_pt=round(h_pt, 2),
                width_in=w_in,
                height_in=h_in,
                is_standard_letter=is_letter,
            )
        )

    doc.close()

    has_blank_pages = len(blank_pages) > 0
    if has_blank_pages:
        violations.append(
            f"Blank Pages Detected: Found empty pages at positions {blank_pages}. All 110 pages must contain content."
        )

    passed = is_page_count_correct and all_pages_correct_size and not has_blank_pages

    return PDFValidationResult(
        passed=passed,
        pdf_path=str(path),
        total_pages=total_pages,
        expected_pages=expected_page_count,
        is_page_count_correct=is_page_count_correct,
        all_pages_correct_size=all_pages_correct_size,
        has_blank_pages=has_blank_pages,
        blank_page_numbers=blank_pages,
        pages_geometry=pages_geometry,
        violations=violations,
    )
