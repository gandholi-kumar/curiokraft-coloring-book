"""Tests for the offline-to-cloud SyncEngine."""

from pathlib import Path

from PIL import Image

from curiokraft_book.data.base import PageRecord, PromptRecord
from curiokraft_book.data.hybrid_store import HybridDataStore
from curiokraft_book.data.object_storage import LocalFileStorageBackend
from curiokraft_book.data.sync_engine import SyncEngine


def test_sync_engine_without_remote_url(tmp_path: Path):
    """SyncEngine reports error gracefully when remote DB URL is missing."""
    storage = LocalFileStorageBackend(base_dir=tmp_path / "storage")
    store = HybridDataStore(
        db_url=f"sqlite:///{tmp_path / 'local.db'}",
        state_file=tmp_path / "state.json",
        storage_backend=storage,
    )

    engine = SyncEngine(local_store=store, remote_db_url=None, remote_storage=storage)
    report = engine.sync()

    assert report.success is False
    assert len(report.errors) > 0
    assert "Remote database URL not configured" in report.errors[0]


def test_sync_engine_push_and_pull(tmp_path: Path):
    """SyncEngine pushes local outbox events to remote and pulls remote updates."""
    local_storage = LocalFileStorageBackend(base_dir=tmp_path / "local_storage")
    remote_storage = LocalFileStorageBackend(base_dir=tmp_path / "remote_storage")

    local_db_url = f"sqlite:///{tmp_path / 'local.db'}"
    remote_db_url = f"sqlite:///{tmp_path / 'remote.db'}"

    # 1. Setup local and remote hybrid stores
    local_store = HybridDataStore(
        db_url=local_db_url,
        state_file=tmp_path / "local_state.json",
        book_slug="sync-test-vol1",
        storage_backend=local_storage,
    )

    # 2. Add local changes that generate outbox events
    img_path = tmp_path / "sync_image.png"
    Image.new("L", (50, 50), 200).save(img_path)
    local_store.register_media_asset(img_path, asset_type="composite_master", page_id="P001")

    prompt = PromptRecord(
        book_id=local_store.active_book.id,
        page_id="P001",
        positive_prompt="Synchronized prompt",
    )
    local_store.prompts.save_prompt(prompt)

    page = PageRecord(
        book_id=local_store.active_book.id,
        page_id="P001",
        page_number=1,
        canonical_object="dolphin",
        display_label="DOLPHIN",
        status="approved",
    )
    local_store.pages.save_page(page)

    # 3. Setup remote store with a different page to verify pull
    remote_store = HybridDataStore(
        db_url=remote_db_url,
        state_file=tmp_path / "remote_state.json",
        book_slug="sync-test-vol1",
        storage_backend=remote_storage,
    )
    remote_page = PageRecord(
        book_id=remote_store.active_book.id,
        page_id="P002",
        page_number=2,
        canonical_object="whale",
        display_label="WHALE",
        status="generated",
    )
    remote_store.pages.save_page(remote_page)

    # 4. Execute sync
    engine = SyncEngine(
        local_store=local_store,
        remote_db_url=remote_db_url,
        remote_storage=remote_storage,
    )
    report = engine.sync()

    assert report.success is True
    assert report.pushed_books >= 1
    assert report.pushed_pages >= 1
    assert report.pushed_prompts >= 1
    assert report.pushed_assets >= 1
    assert report.pulled_pages >= 1

    # 5. Verify local store now has the pulled remote page
    pulled = local_store.pages.get_page(local_store.active_book.id, "P002")
    assert pulled is not None
    assert pulled.canonical_object == "whale"

    # 6. Verify remote store has the pushed local page
    pushed = remote_store.pages.get_page(remote_store.active_book.id, "P001")
    assert pushed is not None
    assert pushed.canonical_object == "dolphin"
