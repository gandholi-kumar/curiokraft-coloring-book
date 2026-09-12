"""Programmatic 110-page interior PDF compiler for Amazon KDP printing."""

from pathlib import Path

import pymupdf as fitz
from pydantic import BaseModel

from curiokraft_book.constants import (
    DEFAULT_INTERIOR_PDF,
    DEFAULT_PAGE_COUNT,
    DEFAULT_PAGE_HEIGHT_PT,
    DEFAULT_PAGE_WIDTH_PT,
)
from curiokraft_book.validators.pdf import PDFValidationResult, validate_interior_pdf


class InteriorPDFResult(BaseModel):
    """Result of compiling the 110-page interior PDF."""

    success: bool
    output_pdf_path: str
    total_pages_compiled: int
    validation: PDFValidationResult
    error_message: str | None = None


def compile_interior_pdf(
    image_paths: list[str | Path],
    output_pdf_path: str | Path = DEFAULT_INTERIOR_PDF,
    expected_page_count: int = DEFAULT_PAGE_COUNT,
    page_width_pt: float = DEFAULT_PAGE_WIDTH_PT,  # 8.5 in * 72 pt/in
    page_height_pt: float = DEFAULT_PAGE_HEIGHT_PT,  # 11.0 in * 72 pt/in
) -> InteriorPDFResult:
    """Compile a list of 110 page images into a single lossless 8.5x11 inch print PDF.

    Args:
        image_paths: Ordered list of 110 image file paths.
        output_pdf_path: Destination path for the compiled PDF.
        expected_page_count: Required page count (default: 110).
        page_width_pt: Page width in points (default: 612 pt = 8.5 in).
        page_height_pt: Page height in points (default: 792 pt = 11.0 in).

    Returns:
        InteriorPDFResult with compilation and validation report.
    """
    out_p = Path(output_pdf_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    if len(image_paths) != expected_page_count:
        dummy_val = PDFValidationResult(
            passed=False,
            pdf_path=str(out_p),
            total_pages=len(image_paths),
            expected_pages=expected_page_count,
            is_page_count_correct=False,
            all_pages_correct_size=False,
            has_blank_pages=False,
            violations=[
                f"Input image count mismatch: Expected {expected_page_count} images, received {len(image_paths)}."
            ],
        )
        return InteriorPDFResult(
            success=False,
            output_pdf_path=str(out_p),
            total_pages_compiled=len(image_paths),
            validation=dummy_val,
            error_message=f"Received {len(image_paths)} images instead of {expected_page_count}.",
        )

    # Use PyMuPDF for lossless fast PDF assembly
    doc = fitz.open()

    for idx, img_path in enumerate(image_paths):
        p = Path(img_path)
        if not p.exists():
            doc.close()
            raise FileNotFoundError(f"Missing page image at index {idx + 1}: {p}")

        # Create new blank 8.5x11 page (612x792 pt)
        page = doc.new_page(width=page_width_pt, height=page_height_pt)

        # Insert image fitting the entire rect without margin distortion (margins are inside the 2550x3300 px raster)
        rect = fitz.Rect(0, 0, page_width_pt, page_height_pt)
        page.insert_image(rect, filename=str(p))

    # Set clean publishing metadata
    doc.set_metadata(
        {
            "title": "Tiny Hands Color & Learn",
            "author": "CurioKraft Publications",
            "subject": "Amazon KDP Preschool Activity Coloring Book",
            "creator": "CurioKraft Publishing Engine v1.0",
            "producer": "CurioKraft Automated Preflight Suite",
        }
    )

    # Save PDF with lossless compression
    doc.save(str(out_p), garbage=4, deflate=True)
    doc.close()

    # Run immediate preflight validation on the newly compiled PDF
    val_report = validate_interior_pdf(out_p, expected_page_count=expected_page_count)

    return InteriorPDFResult(
        success=val_report.passed,
        output_pdf_path=str(out_p),
        total_pages_compiled=len(image_paths),
        validation=val_report,
        error_message=None if val_report.passed else "; ".join(val_report.violations),
    )
