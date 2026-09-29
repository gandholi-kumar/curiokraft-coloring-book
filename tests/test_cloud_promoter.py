"""Comprehensive unit tests for CloudPromoter (offline-to-cloud promotion engine)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from curiokraft_book.data.base import (
    BookRecord,
    MediaAssetRecord,
    PageRecord,
    PromptRecord,
    SyncStatus,
)
from curiokraft_book.data.cloud_promoter import CloudPromoter
from curiokraft_book.data.hybrid_store import HybridDataStore
from curiokraft_book.data.models import (
    BookModel,
    MediaAssetModel,
    OutboxEventModel,
    PageModel,
    PromptModel,
)
from curiokraft_book.data.object_storage import LocalFileStorageBackend, S3StorageBackend
from curiokraft_book.data.postgres_store import SQLDatabaseManager


@pytest.fixture(autouse=True)
def isolate_promoter_env(monkeypatch):
    """Ensure environment is isolated from ambient credentials or database URLs."""
    monkeypatch.delenv("CLOUD_DATABASE_URL", raising=False)
    monkeypatch.delenv("REMOTE_DATABASE_URL", raising=False)
    monkeypatch.delenv("CLOUD_S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("CLOUD_S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("CLOUD_S3_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("CLOUD_S3_BUCKET_NAME", raising=False)
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("S3_SECRET_ACCESS_KEY", raising=False)


@pytest.fixture
def local_hybrid_store(tmp_path: Path) -> HybridDataStore:
    """Fixture providing isolated local HybridDataStore with SQLite backend."""
    storage_dir = tmp_path / "local_storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage = LocalFileStorageBackend(base_dir=storage_dir)

    db_path = tmp_path / "local.db"
    store = HybridDataStore(
        db_url=f"sqlite:///{db_path}",
        state_file=tmp_path / "local_state.json",
        book_slug="ocean-vol1",
        storage_backend=storage,
    )
    return store


@pytest.fixture
def cloud_db_mgr(tmp_path: Path) -> SQLDatabaseManager:
    """Fixture providing isolated cloud SQLDatabaseManager with SQLite backend."""
    db_path = tmp_path / "cloud.db"
    mgr = SQLDatabaseManager(f"sqlite:///{db_path}")
    mgr.init_db()
    return mgr


@pytest.fixture
def mock_cloud_storage() -> MagicMock:
    """Fixture providing mock Backblaze B2 S3 storage backend."""
    storage = MagicMock(spec=S3StorageBackend)
    storage.bucket_name = "curiokraft-test-bucket"
    storage.s3_client = MagicMock()
    storage.upload_file = MagicMock()
    return storage


# ==============================================================================
# 1. Configuration & Initial State Tests
# ==============================================================================


def test_promoter_unconfigured(local_hybrid_store: HybridDataStore):
    """Verify promoter handles unconfigured cloud targets gracefully."""
    promoter = CloudPromoter(local_store=local_hybrid_store, cloud_db_url=None, cloud_storage=None)
    assert promoter.is_cloud_configured() is False

    with pytest.raises(RuntimeError, match="Cloud database connection is not configured"):
        promoter.get_catalog_diff()

    report = promoter.promote_book("any-slug")
    assert report.success is False
    assert any("Cloud database (Neon) not configured" in err for err in report.errors)


def test_promoter_missing_cloud_storage(
    local_hybrid_store: HybridDataStore, cloud_db_mgr: SQLDatabaseManager
):
    """Verify promoter handles configured DB but missing storage gracefully."""
    promoter = CloudPromoter(
        local_store=local_hybrid_store,
        cloud_db_url=cloud_db_mgr.db_url,
        cloud_storage=None,
    )
    assert promoter.is_cloud_configured() is False

    report = promoter.promote_book("ocean-vol1")
    assert report.success is False
    assert any("Cloud object storage (Backblaze B2) not configured" in err for err in report.errors)


def test_promoter_book_not_found(
    local_hybrid_store: HybridDataStore,
    cloud_db_mgr: SQLDatabaseManager,
    mock_cloud_storage: MagicMock,
):
    """Verify error report when requested book slug does not exist locally."""
    promoter = CloudPromoter(
        local_store=local_hybrid_store,
        cloud_db_url=cloud_db_mgr.db_url,
        cloud_storage=mock_cloud_storage,
    )
    assert promoter.is_cloud_configured() is True

    report = promoter.promote_book("non-existent-book")
    assert report.success is False
    assert "Book with slug 'non-existent-book' not found" in report.errors[0]


# ==============================================================================
# 2. Catalog Diff Tests
# ==============================================================================


def test_promoter_get_catalog_diff(
    local_hybrid_store: HybridDataStore,
    cloud_db_mgr: SQLDatabaseManager,
    mock_cloud_storage: MagicMock,
):
    """Verify O(1) catalog diff calculation between local and cloud databases."""
    # 1. Setup local store: Active book has 2 pages
    p1 = PageRecord(
        book_id=local_hybrid_store.active_book.id,
        page_id="P001",
        page_number=1,
        canonical_object="starfish",
        display_label="STARFISH",
    )
    p2 = PageRecord(
        book_id=local_hybrid_store.active_book.id,
        page_id="P002",
        page_number=2,
        canonical_object="dolphin",
        display_label="DOLPHIN",
    )
    local_hybrid_store.pages.save_page(p1)
    local_hybrid_store.pages.save_page(p2)

    # Add a second unpromoted book locally
    book2 = BookRecord(
        title="Dinosaur Expeditions",
        slug="dino-vol1",
        volume="vol1",
        theme="dinosaur",
    )
    local_hybrid_store.books.save(book2)

    promoter = CloudPromoter(
        local_store=local_hybrid_store,
        cloud_db_url=cloud_db_mgr.db_url,
        cloud_storage=mock_cloud_storage,
    )

    # Initial diff: both books are unpromoted in cloud
    diff1 = promoter.get_catalog_diff()
    assert diff1["local_total"] == 2
    assert diff1["cloud_total"] == 0
    assert len(diff1["unpromoted"]) == 2
    assert len(diff1["partial"]) == 0
    assert len(diff1["in_sync"]) == 0

    # Simulate ocean-vol1 partially exists in cloud (only 1 page)
    with cloud_db_mgr.session() as s:
        cloud_b1 = BookModel(
            id=local_hybrid_store.active_book.id,
            slug="ocean-vol1",
            title="Ocean Expeditions",
            volume="vol1",
        )
        s.add(cloud_b1)
        s.flush()
        cloud_p1 = PageModel(
            id=str(uuid4()),
            book_id=cloud_b1.id,
            page_id="P001",
            page_number=1,
            canonical_object="starfish",
            display_label="STARFISH",
        )
        s.add(cloud_p1)

    diff2 = promoter.get_catalog_diff()
    assert diff2["local_total"] == 2
    assert diff2["cloud_total"] == 1
    assert len(diff2["unpromoted"]) == 1
    assert diff2["unpromoted"][0].slug == "dino-vol1"
    assert len(diff2["partial"]) == 1
    assert diff2["partial"][0][0].slug == "ocean-vol1"
    assert diff2["partial"][0][1] == 2  # local_count
    assert diff2["partial"][0][2] == 1  # cloud_count
    assert len(diff2["in_sync"]) == 0

    # Add missing second page to cloud so ocean-vol1 is in sync
    with cloud_db_mgr.session() as s:
        cloud_p2 = PageModel(
            id=str(uuid4()),
            book_id=local_hybrid_store.active_book.id,
            page_id="P002",
            page_number=2,
            canonical_object="dolphin",
            display_label="DOLPHIN",
        )
        s.add(cloud_p2)

    diff3 = promoter.get_catalog_diff()
    assert len(diff3["in_sync"]) == 1
    assert diff3["in_sync"][0].slug == "ocean-vol1"
    assert len(diff3["partial"]) == 0


# ==============================================================================
# 3. Dry-Run Promotion Tests
# ==============================================================================


def test_promoter_dry_run(
    local_hybrid_store: HybridDataStore,
    cloud_db_mgr: SQLDatabaseManager,
    mock_cloud_storage: MagicMock,
):
    """Verify dry_run previews promotion without modifying cloud DB or S3."""
    p1 = PageRecord(
        book_id=local_hybrid_store.active_book.id,
        page_id="P001",
        page_number=1,
        canonical_object="starfish",
        display_label="STARFISH",
    )
    local_hybrid_store.pages.save_page(p1)

    promoter = CloudPromoter(
        local_store=local_hybrid_store,
        cloud_db_url=cloud_db_mgr.db_url,
        cloud_storage=mock_cloud_storage,
    )

    report = promoter.promote_book(slug="ocean-vol1", dry_run=True)
    assert report.success is True
    assert report.dry_run is True
    assert report.pushed_pages == 1
    assert report.pushed_books == 0

    # Confirm cloud DB remains completely empty
    with cloud_db_mgr.session() as s:
        cloud_books = s.scalars(select(BookModel)).all()
        assert len(cloud_books) == 0


# ==============================================================================
# 4. Full Real Promotion & CAS Deduplication Tests
# ==============================================================================


def test_promoter_full_real_execution(
    local_hybrid_store: HybridDataStore,
    cloud_db_mgr: SQLDatabaseManager,
    mock_cloud_storage: MagicMock,
    tmp_path: Path,
):
    """Verify real promotion copies books, pages, prompts, and media assets to cloud."""
    book = local_hybrid_store.active_book

    # 1. Add page
    page = PageRecord(
        book_id=book.id,
        page_id="P001",
        page_number=1,
        canonical_object="starfish",
        display_label="STARFISH",
    )
    local_hybrid_store.pages.save_page(page)

    # 2. Add prompt
    prompt = PromptRecord(
        book_id=book.id,
        page_id="P001",
        prompt_type="positive_generation",
        positive_prompt="A cute starfish",
    )
    local_hybrid_store.prompts.save_prompt(prompt)

    # 3. Add asset with bytes in storage backend
    img_bytes = b"fake_png_image_bytes_for_testing"
    storage_key = "assets/ocean-vol1/interior/P001.png"
    target_storage_file = local_hybrid_store.storage.base_dir / storage_key
    target_storage_file.parent.mkdir(parents=True, exist_ok=True)
    target_storage_file.write_bytes(img_bytes)
    sha256 = hashlib.sha256(img_bytes).hexdigest()

    asset1 = MediaAssetRecord(
        book_id=book.id,
        page_id="P001",
        asset_type="composite_master",
        storage_key=storage_key,
        file_size_bytes=len(img_bytes),
        sha256_hash=sha256,
    )
    local_hybrid_store.assets.save_asset(asset1)

    # 4. Add asset via fallback disk path
    disk_file = Path("test_temp_fallback_cover.png")
    disk_bytes = b"disk_fallback_bytes"
    disk_file.write_bytes(disk_bytes)
    disk_sha256 = hashlib.sha256(disk_bytes).hexdigest()

    try:
        asset2 = MediaAssetRecord(
            book_id=book.id,
            page_id="COVER_FRONT",
            asset_type="cover_front",
            storage_key=str(disk_file),
            file_size_bytes=len(disk_bytes),
            sha256_hash=disk_sha256,
        )
        local_hybrid_store.assets.save_asset(asset2)

        # 5. Add pending outbox events in local and cloud DB
        with local_hybrid_store.db_mgr.session() as s:
            outbox_local = OutboxEventModel(
                id=f"outbox_{uuid4().hex}",
                entity_type="book",
                entity_id=book.id,
                operation="INSERT",
                payload={"slug": book.slug},
                status="PENDING",
            )
            s.add(outbox_local)

        with cloud_db_mgr.session() as s:
            outbox_cloud = OutboxEventModel(
                id=f"outbox_cloud_{uuid4().hex}",
                entity_type="book",
                entity_id=book.id,
                operation="INSERT",
                payload={"slug": book.slug},
                status="PENDING",
            )
            s.add(outbox_cloud)

        promoter = CloudPromoter(
            local_store=local_hybrid_store,
            cloud_db_url=cloud_db_mgr.db_url,
            cloud_storage=mock_cloud_storage,
        )

        # First promotion run
        report1 = promoter.promote_book(slug="ocean-vol1", dry_run=False)
        assert report1.success is True
        assert report1.pushed_books == 1
        assert report1.pushed_pages == 1
        assert report1.pushed_prompts == 1
        assert report1.pushed_assets == 2
        assert report1.bytes_uploaded > 0
        assert report1.skipped_assets_reused == 0

        # Verify cloud database state
        with cloud_db_mgr.session() as s:
            cloud_book = s.scalars(select(BookModel).where(BookModel.slug == "ocean-vol1")).first()
            assert cloud_book is not None
            assert cloud_book.sync_status == SyncStatus.SYNCED.value

            cloud_pages = s.scalars(
                select(PageModel).where(PageModel.book_id == cloud_book.id)
            ).all()
            assert len(cloud_pages) == 1
            assert cloud_pages[0].display_label == "STARFISH"

            cloud_prompts = s.scalars(
                select(PromptModel).where(PromptModel.book_id == cloud_book.id)
            ).all()
            assert len(cloud_prompts) == 1
            assert cloud_prompts[0].positive_prompt == "A cute starfish"

            cloud_assets = s.scalars(
                select(MediaAssetModel).where(MediaAssetModel.book_id == cloud_book.id)
            ).all()
            assert len(cloud_assets) == 2

            # Check outbox status updated to PROCESSED
            cloud_outbox = s.scalars(
                select(OutboxEventModel).where(OutboxEventModel.entity_id == book.id)
            ).first()
            assert cloud_outbox.status == "PROCESSED"

        # Verify local outbox status updated to PROCESSED
        with local_hybrid_store.db_mgr.session() as s:
            loc_outbox = s.scalars(
                select(OutboxEventModel).where(OutboxEventModel.entity_id == book.id)
            ).first()
            assert loc_outbox.status == "PROCESSED"

        # Verify S3 upload was called for the first asset
        mock_cloud_storage.s3_client.put_object.assert_called()
        mock_cloud_storage.upload_file.assert_called_with(str(disk_file), str(disk_file))

        # --------------------------------------------------------------------------
        # Second promotion run: CAS Deduplication fast-path
        # --------------------------------------------------------------------------
        mock_cloud_storage.s3_client.put_object.reset_mock()
        mock_cloud_storage.upload_file.reset_mock()

        report2 = promoter.promote_book(slug="ocean-vol1", dry_run=False, force_upload=False)
        assert report2.success is True
        assert report2.skipped_assets_reused == 2
        assert report2.bytes_uploaded == 0
        mock_cloud_storage.s3_client.put_object.assert_not_called()
        mock_cloud_storage.upload_file.assert_not_called()

        # --------------------------------------------------------------------------
        # Third promotion run: Force upload bypasses CAS deduplication
        # --------------------------------------------------------------------------
        mock_cloud_storage.s3_client.put_object.reset_mock()
        mock_cloud_storage.upload_file.reset_mock()

        report3 = promoter.promote_book(slug="ocean-vol1", dry_run=False, force_upload=True)
        assert report3.success is True
        assert report3.skipped_assets_reused == 0
        mock_cloud_storage.s3_client.put_object.assert_called()
    finally:
        disk_file.unlink(missing_ok=True)


# ==============================================================================
# 5. Error Scenarios & Locked Prompt Tests
# ==============================================================================


def test_promoter_locked_prompt_protection(
    local_hybrid_store: HybridDataStore,
    cloud_db_mgr: SQLDatabaseManager,
    mock_cloud_storage: MagicMock,
):
    """Verify that prompts locked in cloud DB are not overwritten by promoter."""
    book = local_hybrid_store.active_book

    # 1. Setup prompt in local store
    prompt = PromptRecord(
        book_id=book.id,
        page_id="P001",
        prompt_type="positive_generation",
        positive_prompt="Local prompt text",
    )
    local_hybrid_store.prompts.save_prompt(prompt)

    # 2. Setup existing prompt in cloud DB that is marked is_locked=True
    with cloud_db_mgr.session() as s:
        b = BookModel(id=book.id, slug=book.slug, title=book.title, volume=book.volume)
        s.add(b)
        s.flush()
        cloud_prompt = PromptModel(
            id=str(uuid4()),
            book_id=b.id,
            page_id="P001",
            prompt_type="positive_generation",
            positive_prompt="LOCKED CLOUD PROMPT",
            is_locked=True,
        )
        s.add(cloud_prompt)

    promoter = CloudPromoter(
        local_store=local_hybrid_store,
        cloud_db_url=cloud_db_mgr.db_url,
        cloud_storage=mock_cloud_storage,
    )

    report = promoter.promote_book(slug=book.slug, dry_run=False)
    assert report.success is True

    # Cloud prompt should still have locked prompt text
    with cloud_db_mgr.session() as s:
        cp = s.scalars(
            select(PromptModel).where(PromptModel.book_id == book.id, PromptModel.page_id == "P001")
        ).first()
        assert cp.positive_prompt == "LOCKED CLOUD PROMPT"


def test_promoter_hash_mismatch_and_missing_binary(
    local_hybrid_store: HybridDataStore,
    cloud_db_mgr: SQLDatabaseManager,
    mock_cloud_storage: MagicMock,
):
    """Verify promoter handles hash mismatches and missing source files cleanly."""
    book = local_hybrid_store.active_book

    # Asset 1: Bytes in storage with mismatched expected hash
    real_bytes = b"actual_content_bytes"
    storage_key1 = "assets/mismatch.png"
    target_file = local_hybrid_store.storage.base_dir / storage_key1
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_bytes(real_bytes)

    asset1 = MediaAssetRecord(
        book_id=book.id,
        page_id="P001",
        asset_type="composite_master",
        storage_key=storage_key1,
        file_size_bytes=len(real_bytes),
        sha256_hash="0000000000000000000000000000000000000000000000000000000000000000",
    )
    local_hybrid_store.assets.save_asset(asset1)

    # Asset 2: Non-existent storage key and non-existent file on disk
    asset2 = MediaAssetRecord(
        book_id=book.id,
        page_id="P002",
        asset_type="composite_master",
        storage_key="non_existent_dir/ghost_image.png",
        file_size_bytes=100,
        sha256_hash="1111111111111111111111111111111111111111111111111111111111111111",
    )
    local_hybrid_store.assets.save_asset(asset2)

    promoter = CloudPromoter(
        local_store=local_hybrid_store,
        cloud_db_url=cloud_db_mgr.db_url,
        cloud_storage=mock_cloud_storage,
    )

    report = promoter.promote_book(slug=book.slug, dry_run=False)
    assert len(report.errors) == 2
    assert any("Hash mismatch on" in err for err in report.errors)
    assert any("Cannot locate source binary for" in err for err in report.errors)


# ==============================================================================
# 6. Promote All Pending Tests
# ==============================================================================


def test_promoter_promote_all_pending(
    local_hybrid_store: HybridDataStore,
    cloud_db_mgr: SQLDatabaseManager,
    mock_cloud_storage: MagicMock,
):
    """Verify promote_all_pending discovers and promotes all pending books."""
    assert local_hybrid_store.active_book is not None
    b2 = BookRecord(
        title="Dinosaur World",
        slug="dino-vol1",
        volume="vol1",
        theme="dinosaur",
    )
    local_hybrid_store.books.save(b2)

    promoter = CloudPromoter(
        local_store=local_hybrid_store,
        cloud_db_url=cloud_db_mgr.db_url,
        cloud_storage=mock_cloud_storage,
    )

    reports = promoter.promote_all_pending(dry_run=False)
    assert len(reports) == 2
    assert all(r.success for r in reports)

    diff = promoter.get_catalog_diff()
    assert len(diff["unpromoted"]) == 0
    assert len(diff["in_sync"]) == 2


# ==============================================================================
# 7. Environment Variable Initialization Tests
# ==============================================================================


def test_promoter_env_initialization(monkeypatch, tmp_path: Path):
    """Verify promoter initializes from environment variables."""
    cloud_db = tmp_path / "env_cloud.db"
    monkeypatch.setenv("CLOUD_DATABASE_URL", f"sqlite:///{cloud_db}")
    monkeypatch.setenv("CLOUD_S3_ENDPOINT_URL", "https://s3.us-east-005.backblazeb2.com")
    monkeypatch.setenv("CLOUD_S3_ACCESS_KEY_ID", "mock_key_id")
    monkeypatch.setenv("CLOUD_S3_SECRET_ACCESS_KEY", "mock_secret")
    monkeypatch.setenv("CLOUD_S3_BUCKET_NAME", "mock-b2-bucket")

    promoter = CloudPromoter()
    assert promoter.cloud_db_mgr is not None
    assert promoter.cloud_storage is not None
    assert promoter.is_cloud_configured() is True
