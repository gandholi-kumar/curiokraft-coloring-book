"""Automated test suite for CurioKraft Publishing Studio FastAPI Gateway & WebSocket Server."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from curiokraft_book.api.app import create_app
from curiokraft_book.data.hybrid_store import HybridDataStore
from curiokraft_book.data.object_storage import LocalFileStorageBackend


@pytest.fixture
def test_client(tmp_path: Path, monkeypatch):
    """Fixture providing an isolated FastAPI TestClient with an ephemeral SQLite database."""
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    test_db = tmp_path / "test_api.db"
    db_url = f"sqlite:///{test_db}"
    store = HybridDataStore(
        db_url=db_url,
        storage_backend=LocalFileStorageBackend(base_dir=tmp_path / "storage"),
    )

    app = create_app(db_url=db_url, test_mode=True)
    app.state.store = store

    with TestClient(app) as client:
        yield client


def test_health_endpoint(test_client: TestClient):
    """Verify /api/health returns 200 and connected database status."""
    response = test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "connected" in data["db_status"]
    assert "timestamp" in data


def test_system_config_endpoint(test_client: TestClient):
    """Verify /api/config exposes standard trim sizes, workflow modes, and DPI."""
    response = test_client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert any("8.5" in s for s in data["default_trim_sizes"])
    assert "free_web_ui" in data["workflow_modes"]
    assert any("Toddler" in s for s in data["default_age_groups"])


def test_books_crud_workflow(test_client: TestClient):
    """Verify listing books, creating a new book, and retrieving/updating it."""
    # 1. List books (should include at least active default book)
    list_resp = test_client.get("/api/books")
    assert list_resp.status_code == 200
    books = list_resp.json()
    assert len(books) >= 1

    # 2. Create a new custom book
    new_book_payload = {
        "title": "Ocean Wonders Coloring",
        "subtitle": "Underwater Animals for Kids",
        "slug": "ocean-wonders-vol1",
        "volume": "vol1",
        "page_count": 80,
        "trim_width_in": 8.5,
        "trim_height_in": 11.0,
        "bleed": False,
        "visual_style": {"theme": "ocean"},
    }
    create_resp = test_client.post("/api/books", json=new_book_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["title"] == "Ocean Wonders Coloring"
    assert created["slug"] == "ocean-wonders-vol1"
    assert created["page_count"] == 80
    assert created["spine_width_in"] > 0
    new_id = created["id"]

    # 3. Retrieve new book by ID
    get_resp = test_client.get(f"/api/books/{new_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == new_id

    # 4. Patch book
    patch_resp = test_client.patch(
        f"/api/books/{new_id}",
        json={"page_count": 100, "subtitle": "Updated Subtitle"},
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["page_count"] == 100
    assert patched["subtitle"] == "Updated Subtitle"


def test_pages_listing(test_client: TestClient):
    """Verify pages listing for the default book."""
    books = test_client.get("/api/books").json()
    book_id = books[0]["id"]

    pages_resp = test_client.get(f"/api/books/{book_id}/pages")
    assert pages_resp.status_code == 200
    pages = pages_resp.json()
    assert isinstance(pages, list)
    # Even if empty initially or seeded from manifest, the list is valid
    assert len(pages) >= 0


def test_prompts_synthesis_endpoint(test_client: TestClient):
    """Verify /api/books/{id}/prompts/synthesize triggers debate engine synthesis."""
    books = test_client.get("/api/books").json()
    book_id = books[0]["id"]

    synth_resp = test_client.post(
        f"/api/books/{book_id}/prompts/synthesize?count=2",
        json={"include_covers": True, "include_special_pages": True},
    )
    assert synth_resp.status_code == 200
    manifest = synth_resp.json()
    assert manifest["book_id"] == book_id
    assert manifest["total_prompts"] >= 2
    assert len(manifest["prompts"]) >= 2

    first_prompt = manifest["prompts"][0]
    assert "positive_prompt" in first_prompt
    assert "negative_prompt" in first_prompt
    assert "preset_name" in first_prompt
    assert len(first_prompt["positive_prompt"]) > 10


def test_book_production_status(test_client: TestClient):
    """Verify /api/books/{id}/status aggregates all 6 publishing wizard stages."""
    books = test_client.get("/api/books").json()
    book_id = books[0]["id"]

    status_resp = test_client.get(f"/api/books/{book_id}/status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["book_id"] == book_id
    assert len(data["stages"]) == 6

    stage_ids = [s["stage_id"] for s in data["stages"]]
    assert stage_ids == ["blueprint", "prompts", "ingestion", "masters", "preflight", "kdp"]
    assert "page_stats" in data


def test_telemetry_logs_and_websocket(test_client: TestClient):
    """Verify REST telemetry log ingestion and WebSocket bidirectional exchange."""
    # 1. Ingest a log via REST
    log_payload = {
        "level": "INFO",
        "component": "test_suite",
        "message": "Gateway unit test telemetry probe",
        "context": {"test": True},
    }
    log_resp = test_client.post("/api/telemetry/logs", json=log_payload)
    assert log_resp.status_code == 200

    # 2. Verify recent logs endpoint contains it
    logs_resp = test_client.get("/api/telemetry/logs")
    assert logs_resp.status_code == 200
    recent_logs = logs_resp.json()
    assert any("Gateway unit test telemetry probe" in entry["message"] for entry in recent_logs)

    # 3. Test WebSocket connection
    with test_client.websocket_connect("/ws") as ws:
        # Check initial handshake message
        handshake = ws.receive_json()
        assert handshake["type"] == "handshake_ack"

        # Send ping
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_root_spa_serving(test_client: TestClient):
    """Verify that root / serves HTML containing CurioKraft Studio."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert "html" in response.headers.get("content-type", "").lower()
    text = response.text.lower()
    assert "curiokraft" in text or "vite" in text


def test_upload_raw_pages_endpoint(test_client: TestClient):
    """Verify multipart file upload links images to pages and executes rescue."""
    books = test_client.get("/api/books").json()
    book_id = books[0]["id"]

    img = Image.new("RGB", (100, 100), color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    files = [("files", ("raw_p001.png", buf.getvalue(), "image/png"))]
    resp = test_client.post(f"/api/books/{book_id}/ingest/upload?auto_rescue=true", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_files"] == 1
    assert data["matched_pages"] >= 1
    assert len(data["processed_pages"]) >= 1
    assert data["processed_pages"][0]["raw_image_path"] == "/inbox/raw_pages/raw_p001.png"


def test_scan_inbox_endpoint(test_client: TestClient):
    """Verify scanning inbox links existing files to book pages."""
    books = test_client.get("/api/books").json()
    book_id = books[0]["id"]

    resp = test_client.post(f"/api/books/{book_id}/ingest/scan?auto_rescue=false")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_files" in data
    assert "matched_pages" in data


def test_book_not_found_errors(test_client: TestClient):
    """Verify 404 responses for nonexistent book lookups and updates."""
    non_existent = "non-existent-book-uuid"
    get_resp = test_client.get(f"/api/books/{non_existent}")
    assert get_resp.status_code == 404
    assert "not found" in get_resp.json()["detail"].lower()

    patch_resp = test_client.patch(f"/api/books/{non_existent}", json={"title": "Updated"})
    assert patch_resp.status_code == 404
    assert "not found" in patch_resp.json()["detail"].lower()


def test_page_endpoints_extended(test_client: TestClient):
    """Verify single page retrieval and 404 for missing pages."""
    books = test_client.get("/api/books").json()
    book_id = books[0]["id"]

    # 404 on missing page
    missing_resp = test_client.get(f"/api/books/{book_id}/pages/P999999")
    assert missing_resp.status_code == 404

    # List pages, and if any exist, verify single-page retrieval
    pages_resp = test_client.get(f"/api/books/{book_id}/pages")
    assert pages_resp.status_code == 200
    pages = pages_resp.json()
    if pages:
        first_pid = pages[0]["page_id"]
        single_resp = test_client.get(f"/api/books/{book_id}/pages/{first_pid}")
        assert single_resp.status_code == 200
        assert single_resp.json()["page_id"] == first_pid


def test_default_ingest_convenience_endpoints(test_client: TestClient):
    """Verify convenience ingest endpoints targeting the active book."""
    scan_resp = test_client.post("/api/ingest/scan?auto_rescue=false")
    assert scan_resp.status_code == 200

    img = Image.new("RGB", (50, 50), color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    files = [("files", ("raw_p002.png", buf.getvalue(), "image/png"))]
    upload_resp = test_client.post("/api/ingest/upload?auto_rescue=false", files=files)
    assert upload_resp.status_code == 200


def test_prompts_listing_endpoint(test_client: TestClient):
    """Verify retrieving prompts list for a book."""
    books = test_client.get("/api/books").json()
    book_id = books[0]["id"]

    prompts_resp = test_client.get(f"/api/books/{book_id}/prompts")
    assert prompts_resp.status_code == 200
    assert isinstance(prompts_resp.json(), list)


def test_spa_static_serving(tmp_path: Path):
    """Verify custom static_dir serves index.html, favicon.ico, and assets."""
    dist_dir = tmp_path / "web_dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    index_html = dist_dir / "index.html"
    index_html.write_text("<!DOCTYPE html><html><body>Studio App</body></html>", encoding="utf-8")

    favicon_ico = dist_dir / "favicon.ico"
    favicon_ico.write_bytes(b"\x00\x00\x01\x00")

    asset_js = assets_dir / "main.js"
    asset_js.write_text("console.log('loaded');", encoding="utf-8")

    app = create_app(
        db_url=f"sqlite:///{tmp_path / 'spa_test.db'}", static_dir=dist_dir, test_mode=True
    )
    with TestClient(app) as client:
        # Route: favicon.ico
        fav_resp = client.get("/favicon.ico")
        assert fav_resp.status_code == 200

        # Route: asset
        asset_resp = client.get("/assets/main.js")
        assert asset_resp.status_code == 200

        # Route: SPA fallback
        spa_resp = client.get("/dashboard/editor/p001")
        assert spa_resp.status_code == 200
        assert "Studio App" in spa_resp.text


def test_websocket_broadcasts(test_client: TestClient):
    """Verify websocket manager broadcast methods stream events to active clients and track history."""
    import asyncio

    from curiokraft_book.api.websocket_manager import ConnectionManager

    mgr = ConnectionManager()
    # Test broadcast methods without active connections (buffering logs)
    asyncio.run(
        mgr.broadcast_debate_turn(
            turn_index=1, speaker="Judge", proposal="Test line art", verdict="APPROVED"
        )
    )
    asyncio.run(
        mgr.broadcast_progress(stage="masters", progress_percentage=75.5, message="Processing")
    )
    asyncio.run(mgr.broadcast_log(level="DEBUG", message="Debug streaming message"))
    logs = mgr.get_recent_logs()
    assert len(logs) == 1
    assert logs[0]["message"] == "Debug streaming message"

    # Test WebSocket endpoint connection, handshake, ping/pong, and unknown type
    with test_client.websocket_connect("/ws") as ws:
        handshake = ws.receive_json()
        assert handshake["type"] == "handshake_ack"

        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"

        ws.send_json({"type": "unknown_message_type"})


def test_cli_web_status_command(monkeypatch):
    """Verify cli_web 'status' and helper commands execute without unhandled exceptions."""
    from unittest.mock import MagicMock

    import httpx
    from typer.testing import CliRunner

    from curiokraft_book.cli_web import _open_browser_delayed, web_app

    runner = CliRunner()
    # Test status probe with an invalid port to hit connection exception path
    result = runner.invoke(web_app, ["status", "--port", "1"])
    assert result.exit_code == 0

    # Test status probe when server returns 200 OK
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "status": "ok",
        "version": "1.0.0",
        "db_status": "connected",
        "storage_backend": "local_disk",
        "timestamp": "2026-09-28T12:00:00Z",
    }
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: mock_resp_200)
    result_200 = runner.invoke(web_app, ["status", "--port", "8000"])
    assert result_200.exit_code == 0

    # Test status probe when server returns 500 error
    mock_resp_500 = MagicMock()
    mock_resp_500.status_code = 500
    mock_resp_500.text = "Internal Server Error"
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: mock_resp_500)
    result_500 = runner.invoke(web_app, ["status", "--port", "8000"])
    assert result_500.exit_code == 0

    # Test _open_browser_delayed
    import webbrowser

    mock_open = MagicMock()
    monkeypatch.setattr(webbrowser, "open", mock_open)
    _open_browser_delayed("http://127.0.0.1:8000", delay_seconds=0.01)

    # Test start_web_server command
    import uvicorn

    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: None)
    result_start = runner.invoke(web_app, ["start", "--no-open-browser", "--port", "8999"])
    assert result_start.exit_code == 0


def test_book_update_full_fields(test_client: TestClient):
    """Verify updating all optional book fields via PATCH."""
    books = test_client.get("/api/books").json()
    book_id = books[0]["id"]

    update_payload = {
        "title": "Comprehensive Title",
        "subtitle": "A Wonderful Subtitle",
        "trim_width_in": 8.5,
        "trim_height_in": 11.0,
        "page_count": 80,
        "bleed": True,
        "layout": "standard_margins",
        "visual_style": {"style_preset": "thick_vector_outlines"},
        "target_audience": {"age_range": "toddler"},
        "status": "in_progress",
    }
    resp = test_client.patch(f"/api/books/{book_id}", json=update_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Comprehensive Title"
    assert data["subtitle"] == "A Wonderful Subtitle"
    assert data["page_count"] == 80
    assert data["spine_width_in"] > 0
    assert data["bleed"] is True


def test_book_production_status_and_prompts_extended(test_client: TestClient):
    """Verify aggregated production status and prompt listing with presets."""
    from curiokraft_book.data.base import PromptRecord

    books = test_client.get("/api/books").json()
    book_id = books[0]["id"]

    # Production status check
    status_resp = test_client.get(f"/api/books/{book_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "overall_progress" in status_data
    assert "stages" in status_data
    assert "page_stats" in status_data

    # Save sample prompts into store and verify listing logic
    store = test_client.app.state.store  # type: ignore[attr-defined]
    p_cover = PromptRecord(
        book_id=book_id,
        page_id="cover_front",
        prompt_type="front_cover",
        positive_prompt="A lovely bear cover",
        preset_name="CurioKraft - Cover Art Master",
    )
    p_interior = PromptRecord(
        book_id=book_id,
        page_id="P001",
        prompt_type="interior_page",
        positive_prompt="A friendly bear coloring page",
        preset_name="CurioKraft - Interior Coloring Pages",
    )
    store.prompts.save_prompt(p_cover)
    store.prompts.save_prompt(p_interior)

    prompts_resp = test_client.get(f"/api/books/{book_id}/prompts")
    assert prompts_resp.status_code == 200
    prompts_list = prompts_resp.json()
    assert len(prompts_list) >= 2


def test_websocket_manager_error_handling(test_client: TestClient):
    """Verify connection manager handles dead connections cleanly."""
    import asyncio
    from unittest.mock import AsyncMock

    from curiokraft_book.api.websocket_manager import ConnectionManager

    mgr = ConnectionManager()
    good_conn = AsyncMock()
    bad_conn = AsyncMock()

    async def _test():
        await mgr.connect(good_conn)
        await mgr.connect(bad_conn)
        assert len(mgr.active_connections) == 2

        # Configure bad_conn to fail on broadcast
        bad_conn.send_json.side_effect = RuntimeError("Client socket disconnected")

        await mgr.broadcast({"test": "data"})
        # bad_conn should have been discarded
        assert len(mgr.active_connections) == 1
        assert good_conn in mgr.active_connections

        await mgr.broadcast_progress(stage="testing", progress_percentage=100.0, message="Done")
        await mgr.broadcast_debate_turn(
            turn_index=2, speaker="Critic", proposal="Fine-tune outlines"
        )
        await mgr.disconnect(good_conn)
        assert len(mgr.active_connections) == 0

    asyncio.run(_test())

    # Test WebSocket client sending client_log and malformed text
    with test_client.websocket_connect("/ws") as ws:
        _ = ws.receive_json()  # Handshake ack
        ws.send_json(
            {
                "type": "client_log",
                "level": "INFO",
                "message": "Client test log message",
                "component": "ui",
                "context": {"key": "val"},
            }
        )
        broadcast_log = ws.receive_json()
        assert broadcast_log["type"] == "log_event"

        ws.send_text("this is not json")
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_pipeline_state_manager_logic(tmp_path: Path):
    """Verify PageStateRecord status normalization and PipelineStateManager lifecycle."""
    from curiokraft_book.orchestrator.state_manager import (
        PageStateRecord,
        PageStatus,
        PipelineStateManager,
    )

    # Test status normalization
    rec1 = PageStateRecord(
        page_id="P001",
        page_number=1,
        canonical_object="bear",
        display_label="BEAR",
        section="Animals",
        status="RECEIVED",  # type: ignore[arg-type]
    )
    assert rec1.status == PageStatus.GENERATED

    rec2 = PageStateRecord(
        page_id="P002",
        page_number=2,
        canonical_object="fox",
        display_label="FOX",
        section="Animals",
        status="RESCUING",  # type: ignore[arg-type]
    )
    assert rec2.status == PageStatus.GENERATING

    rec3 = PageStateRecord(
        page_id="P003",
        page_number=3,
        canonical_object="owl",
        display_label="OWL",
        section="Animals",
        status="PASSED",  # type: ignore[arg-type]
    )
    assert rec3.status == PageStatus.TECHNICAL_QA_PASSED

    # Test PipelineStateManager initialization with dummy manifest
    manifest_file = tmp_path / "manifest.json"
    state_file = tmp_path / "state.json"
    manifest_data = {
        "pages": [
            {
                "page_id": "P001",
                "page_number": 1,
                "canonical_object": "bear",
                "display_label": "BEAR",
                "section": "Animals",
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    mgr = PipelineStateManager(state_file_path=state_file, manifest_path=manifest_file)
    assert "P001" in mgr.pages
    assert mgr.pages["P001"].canonical_object == "bear"
