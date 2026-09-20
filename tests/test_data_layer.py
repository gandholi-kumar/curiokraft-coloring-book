"""Tests for centralized database, hybrid persistence, sync engine, and lossless compression."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from curiokraft_book.data.base import (
    BookRecord,
    PageRecord,
    PromptRecord,
)
from curiokraft_book.data.hybrid_store import HybridDataStore
from curiokraft_book.data.object_storage import LocalFileStorageBackend
from curiokraft_book.data.postgres_store import SQLDatabaseManager


@pytest.fixture
def test_db(tmp_path: Path):
    """Fixture providing isolated SQLite database."""
    db_file = tmp_path / "test_curiokraft.db"
    db_mgr = SQLDatabaseManager(f"sqlite:///{db_file}")
    return db_mgr


@pytest.fixture
def test_hybrid_store(tmp_path: Path, test_db: SQLDatabaseManager):
    """Fixture providing isolated HybridDataStore."""
    state_file = tmp_path / "test_pipeline_state.json"
    manifest_file = tmp_path / "test_pages.json"
    config_file = tmp_path / "test_book_config.yaml"

    manifest_file.write_text(
        '{"manifest_version": "1.0", "pages": [{"page_id": "P001", "page_number": 1, "canonical_object": "apple", "display_label": "APPLE"}]}',
        encoding="utf-8",
    )
    config_file.write_text(
        'book:\n  title: "Test Book"\n  volume: "vol1"',
        encoding="utf-8",
    )

    storage = LocalFileStorageBackend(base_dir=tmp_path / "storage")

    store = HybridDataStore(
        db_url=test_db.db_url,
        state_file=state_file,
        manifest_path=manifest_file,
        book_config_path=config_file,
        storage_backend=storage,
    )
    return store


# ==============================================================================
# 1. Database Model and Repository Tests
# ==============================================================================


def test_book_repository_crud(test_hybrid_store: HybridDataStore):
    """Verify Book CRUD operations in database."""
    book = BookRecord(
        slug="test-vol1",
        title="Test Coloring Book",
        volume="vol1",
        page_count=55,
    )
    saved = test_hybrid_store.books.save(book)
    assert saved.id is not None

    fetched = test_hybrid_store.books.get_by_slug("test-vol1")
    assert fetched is not None
    assert fetched.title == "Test Coloring Book"
    assert fetched.page_count == 55


def test_page_repository_dual_write(test_hybrid_store: HybridDataStore):
    """Verify dual-write: writes to SQL and updates pipeline_state.json simultaneously."""
    # 1. Update page in hybrid store
    updated = test_hybrid_store.update_page(
        "P001",
        status="generating",
        positive_prompt="Crisp line art of apple",
        qa_score=98.5,
    )
    assert updated.status == "generating"
    assert updated.positive_prompt == "Crisp line art of apple"

    # 2. Check SQL database has the update
    page_in_db = test_hybrid_store.pages.get_page(test_hybrid_store.active_book.id, "P001")
    assert page_in_db is not None
    assert page_in_db.status == "generating"
    assert page_in_db.qa_score == 98.5

    # 3. Check legacy pipeline_state.json has the update
    assert test_hybrid_store.state_file.exists()
    import json
    with open(test_hybrid_store.state_file, encoding="utf-8") as f:
        data = json.load(f)
    assert "P001" in data["pages"]
    assert data["pages"]["P001"]["status"] == "generating"
    assert data["pages"]["P001"]["positive_prompt"] == "Crisp line art of apple"


def test_prompt_repository_locking(test_hybrid_store: HybridDataStore):
    """Verify locked prompts cannot be overwritten."""
    prompt = PromptRecord(
        book_id=test_hybrid_store.active_book.id,
        page_id="P001",
        positive_prompt="Initial prompt",
        is_locked=True,
    )
    test_hybrid_store.prompts.save_prompt(prompt)

    # Attempt to overwrite locked prompt
    attempted_overwrite = PromptRecord(
        id=prompt.id,
        book_id=test_hybrid_store.active_book.id,
        page_id="P001",
        positive_prompt="Overwritten prompt",
        is_locked=False,
    )
    test_hybrid_store.prompts.save_prompt(attempted_overwrite)

    # Must preserve original prompt
    current = test_hybrid_store.prompts.get_prompt(
        test_hybrid_store.active_book.id, "P001", "interior_page"
    )
    assert current is not None
    assert current.positive_prompt == "Initial prompt"


# ==============================================================================
# 2. Content-Addressable Storage & Deduplication Tests
# ==============================================================================


def test_media_asset_registration_and_cas_deduplication(tmp_path: Path, test_hybrid_store: HybridDataStore):
    """Verify SHA-256 computation and asset deduplication."""
    img_path = tmp_path / "page_001.png"
    # Create simple 100x100 grayscale image
    img = Image.new("L", (100, 100), 255)
    img.save(img_path)

    # 1. Register asset
    asset1 = test_hybrid_store.register_media_asset(img_path, asset_type="composite_master", page_id="P001")
    assert asset1.id is not None
    assert len(asset1.sha256_hash) == 64

    # 2. Re-registering identical asset returns existing record without duplication
    asset2 = test_hybrid_store.register_media_asset(img_path, asset_type="composite_master", page_id="P001")
    assert asset1.id == asset2.id
    assert asset1.sha256_hash == asset2.sha256_hash


# ==============================================================================
# 3. Mathematical Bit-for-Bit Zero-Loss Verification
# ==============================================================================


def test_mathematical_bit_for_bit_lossless_compression(tmp_path: Path):
    """Assert 100% mathematical bit-for-bit equality between raw image and decompressed stream."""
    import pymupdf as fitz

    # 1. Create a synthetic 300 DPI coloring book raster with anti-aliased edge transitions
    width, height = 300, 400
    original_arr = np.full((height, width), 255, dtype=np.uint8)
    # Draw sharp black line
    original_arr[150:160, 50:250] = 0
    # Draw 1-2px smooth anti-aliased transition edge
    original_arr[148:150, 50:250] = 120
    original_arr[160:162, 50:250] = 120

    img_path = tmp_path / "test_lossless_master.png"
    pil_img = Image.fromarray(original_arr, mode="L")
    pil_img.save(img_path, dpi=(300, 300), optimize=True)

    # 2. Compile into PDF using exact PyMuPDF Flate compression
    pdf_path = tmp_path / "test_lossless.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_image(fitz.Rect(0, 0, 612, 792), filename=str(img_path))
    doc.save(str(pdf_path), garbage=4, deflate=True)
    doc.close()

    # 3. Extract decompressed pixel stream from PDF
    read_doc = fitz.open(pdf_path)
    extracted_img_meta = read_doc[0].get_images()[0]
    extracted_dict = read_doc.extract_image(extracted_img_meta[0])
    read_doc.close()

    from io import BytesIO
    decompressed_pil = Image.open(BytesIO(extracted_dict["image"])).convert("L")
    decompressed_arr = np.array(decompressed_pil)

    # 4. Strict assertion: Every single pixel in the entire matrix must be IDENTICAL
    assert np.array_equal(original_arr, decompressed_arr), "Compression was not mathematically lossless!"


def test_cross_book_asset_reuse_and_scoping(tmp_path: Path):
    """Test cross-book asset discovery by canonical object and book slug scoping."""
    db_file = tmp_path / "cross_book_test.db"
    db_url = f"sqlite:///{db_file}"

    # Book A: Ocean Expeditions
    store_a = HybridDataStore(
        db_url=db_url,
        state_file=tmp_path / "state_a.json",
        book_slug="ocean-vol1",
    )
    # Register an image for clownfish in Book A
    raw_img = tmp_path / "raw_clownfish.png"
    Image.new("L", (100, 100), 128).save(raw_img)

    page_a = PageRecord(
        book_id=store_a.active_book.id,
        page_id="P001",
        page_number=1,
        canonical_object="clownfish",
        display_label="CLOWNFISH",
        raw_image_path=str(raw_img),
        status="approved",
    )
    store_a.pages.save_page(page_a)

    # Book B: Safari Adventures
    store_b = HybridDataStore(
        db_url=db_url,
        state_file=tmp_path / "state_b.json",
        book_slug="safari-vol1",
    )
    assert store_b.active_book.slug == "safari-vol1"
    assert store_b.active_book.id != store_a.active_book.id

    # Book B queries for "clownfish" (case-insensitive)
    found_asset = store_b.find_raw_asset_by_canonical("ClownFish")
    assert found_asset is not None
    assert Path(found_asset) == raw_img

    # Book B queries for an object that has not been drawn yet
    assert store_b.find_raw_asset_by_canonical("lion") is None
