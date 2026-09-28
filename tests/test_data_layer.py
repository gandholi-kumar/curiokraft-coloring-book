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


def test_media_asset_registration_and_cas_deduplication(
    tmp_path: Path, test_hybrid_store: HybridDataStore
):
    """Verify SHA-256 computation and asset deduplication."""
    img_path = tmp_path / "page_001.png"
    # Create simple 100x100 grayscale image
    img = Image.new("L", (100, 100), 255)
    img.save(img_path)

    # 1. Register asset
    asset1 = test_hybrid_store.register_media_asset(
        img_path, asset_type="composite_master", page_id="P001"
    )
    assert asset1.id is not None
    assert len(asset1.sha256_hash) == 64

    # 2. Re-registering identical asset returns existing record without duplication
    asset2 = test_hybrid_store.register_media_asset(
        img_path, asset_type="composite_master", page_id="P001"
    )
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
    assert np.array_equal(original_arr, decompressed_arr), (
        "Compression was not mathematically lossless!"
    )


def test_cross_book_asset_reuse_and_scoping(tmp_path: Path):
    """Test cross-book asset discovery by canonical object and book slug scoping."""
    db_file = tmp_path / "cross_book_test.db"
    db_url = f"sqlite:///{db_file}"

    # Book A: Ocean Expeditions
    storage_a = LocalFileStorageBackend(base_dir=tmp_path / "storage_a")
    store_a = HybridDataStore(
        db_url=db_url,
        state_file=tmp_path / "state_a.json",
        book_slug="ocean-vol1",
        storage_backend=storage_a,
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
    storage_b = LocalFileStorageBackend(base_dir=tmp_path / "storage_b")
    store_b = HybridDataStore(
        db_url=db_url,
        state_file=tmp_path / "state_b.json",
        book_slug="safari-vol1",
        storage_backend=storage_b,
    )
    assert store_b.active_book.slug == "safari-vol1"
    assert store_b.active_book.id != store_a.active_book.id

    # Book B queries for "clownfish" (case-insensitive)
    found_asset = store_b.find_raw_asset_by_canonical("ClownFish")
    assert found_asset is not None
    assert Path(found_asset) == raw_img

    # Book B queries for an object that has not been drawn yet
    assert store_b.find_raw_asset_by_canonical("lion") is None


def test_local_storage_backend_methods(tmp_path: Path):
    """Test LocalFileStorageBackend operations and SHA256 helper."""
    from curiokraft_book.data.object_storage import compute_sha256, get_storage_backend

    storage = LocalFileStorageBackend(base_dir=tmp_path / "storage_test")
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Hello CurioKraft Storage!", encoding="utf-8")

    # Hash verification
    sha_str = compute_sha256(test_file)
    assert len(sha_str) == 64
    assert compute_sha256(b"Hello CurioKraft Storage!") == sha_str
    assert compute_sha256(tmp_path / "does_not_exist.txt") == ""

    # Upload
    stored_path = storage.upload_file(str(test_file), "docs/sample.txt")
    assert Path(stored_path).exists()
    assert storage.exists("docs/sample.txt")
    assert not storage.exists("docs/missing.txt")

    # Get bytes
    data_bytes = storage.get_bytes("docs/sample.txt")
    assert data_bytes == b"Hello CurioKraft Storage!"
    assert storage.get_bytes("docs/missing.txt") is None

    # Download
    dl_target = tmp_path / "downloaded_sample.txt"
    success = storage.download_file("docs/sample.txt", str(dl_target))
    assert success is True
    assert dl_target.read_text(encoding="utf-8") == "Hello CurioKraft Storage!"
    assert storage.download_file("docs/missing.txt", str(tmp_path / "none.txt")) is False

    # Missing source file upload raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        storage.upload_file(str(tmp_path / "absent.txt"), "dest.txt")

    # Factory instantiation
    local_backend = get_storage_backend("local", local_dir=str(tmp_path / "local_factory"))
    assert isinstance(local_backend, LocalFileStorageBackend)


def test_s3_storage_backend_mocked(tmp_path: Path, monkeypatch):
    """Test S3StorageBackend methods using a mocked boto3 S3 client."""
    from unittest.mock import MagicMock

    import boto3

    from curiokraft_book.data.object_storage import S3StorageBackend, get_storage_backend

    mock_client = MagicMock()
    mock_body = MagicMock()
    mock_body.iter_chunks.return_value = [b"chunk1", b"chunk2"]
    mock_body.read.return_value = b"chunk1chunk2"
    mock_client.get_object.return_value = {"Body": mock_body}

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: mock_client)

    s3 = S3StorageBackend(
        bucket_name="test-bucket",
        endpoint_url="http://mocked.s3",
        access_key_id="test-key",
        secret_access_key="test-secret",  # noqa: S106
    )

    # Upload
    sample_file = tmp_path / "s3_sample.png"
    sample_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    uri = s3.upload_file(str(sample_file), "pages/p001.png")
    assert uri == "s3://test-bucket/pages/p001.png"
    mock_client.put_object.assert_called_once()

    # Exists
    mock_client.head_object.return_value = {}
    assert s3.exists("pages/p001.png") is True

    # Exists failure
    mock_client.head_object.side_effect = Exception("Not found")
    assert s3.exists("pages/missing.png") is False

    # Download
    dl_path = tmp_path / "s3_downloaded.png"
    mock_client.head_object.side_effect = None
    assert s3.download_file("pages/p001.png", str(dl_path)) is True
    assert dl_path.read_bytes() == b"chunk1chunk2"

    # Download failure
    mock_client.get_object.side_effect = Exception("S3 error")
    assert s3.download_file("pages/bad.png", str(tmp_path / "fail.png")) is False

    # Get bytes
    mock_client.get_object.side_effect = None
    assert s3.get_bytes("pages/p001.png") == b"chunk1chunk2"
    mock_client.get_object.side_effect = Exception("Get bytes error")
    assert s3.get_bytes("pages/p001.png") is None

    # Factory with s3 mode
    s3_backend = get_storage_backend("s3", bucket_name="test-bucket")
    assert isinstance(s3_backend, S3StorageBackend)


def test_sql_repositories_extended_methods(test_hybrid_store: HybridDataStore):
    """Test extended query methods for Books, Pages, Prompts, Logs, and Assets."""
    from curiokraft_book.data.base import LogRecord, PromptRecord

    book_id = test_hybrid_store.active_book.id

    # 1. Book repository listing and search
    all_books = test_hybrid_store.books.list_books()
    assert len(all_books) >= 1
    assert test_hybrid_store.books.get_by_slug("non-existent-book-slug") is None

    # 2. Page repository listing
    test_hybrid_store.update_page("P001", status="PLANNED")
    all_pages = test_hybrid_store.pages.get_pages_for_book(book_id)
    assert any(p.page_id == "P001" for p in all_pages)
    found = test_hybrid_store.pages.find_by_canonical(all_pages[0].canonical_object)
    assert len(found) >= 1

    # 3. Prompt repository listing
    prompt = PromptRecord(
        book_id=book_id,
        page_id="P001",
        prompt_type="cover_page",
        positive_prompt="Lively marine cover",
    )
    test_hybrid_store.prompts.save_prompt(prompt)
    prompts = test_hybrid_store.prompts.list_prompts_for_book(book_id)
    assert len(prompts) >= 1
    assert test_hybrid_store.prompts.get_prompt(book_id, "P999", "interior_page") is None

    # 4. Log repository
    log_rec = LogRecord(
        book_id=book_id,
        page_id="P001",
        level="INFO",
        source="unit_test",
        message="Test log entry",
    )
    test_hybrid_store.logs.log(log_rec)

    # 5. Asset repository listing and lookup by hash
    assets = test_hybrid_store.assets.list_assets_for_book(book_id)
    assert isinstance(assets, list)
    assert test_hybrid_store.assets.find_by_hash("0" * 64) is None
    assert test_hybrid_store.assets.get_asset("phantom_asset_id") is None


def test_hybrid_store_corrupted_legacy_state_file(tmp_path: Path, test_db: SQLDatabaseManager):
    """Test that corrupted legacy state file is logged gracefully during dual write."""
    from curiokraft_book.data.base import PageRecord

    state_file = tmp_path / "corrupted_state.json"
    state_file.write_text("NOT_VALID_JSON{", encoding="utf-8")

    manifest = tmp_path / "pages.json"
    manifest.write_text('{"manifest_version": "1.0", "pages": []}', encoding="utf-8")

    store = HybridDataStore(
        db_url=test_db.db_url,
        state_file=state_file,
        manifest_path=manifest,
        storage_backend=LocalFileStorageBackend(base_dir=tmp_path / "storage"),
    )

    page = PageRecord(
        book_id=store.active_book.id,
        page_id="P001",
        page_number=1,
        canonical_object="starfish",
        display_label="STARFISH",
    )
    store.pages.save_page(page)

    # Update page should not crash; it logs warning and writes fresh data
    updated = store.update_page("P001", status="approved")
    assert updated.status == "approved"
    assert state_file.exists()
