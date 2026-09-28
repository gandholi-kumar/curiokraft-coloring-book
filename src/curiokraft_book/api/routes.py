"""REST API routes and WebSocket endpoint for CurioKraft Publishing Studio."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import text

from curiokraft_book import __version__
from curiokraft_book.api.schemas import (
    BookCreateRequest,
    BookProductionStatusResponse,
    BookResponse,
    BookUpdateRequest,
    HealthResponse,
    IngestUploadResponse,
    PageResponse,
    PipelineStageStatus,
    PromptManifestResponse,
    PromptSynthesizeRequest,
    SystemConfigResponse,
    TelemetryLogEvent,
)
from curiokraft_book.api.websocket_manager import ws_manager
from curiokraft_book.constants import (
    CANVAS_DPI,
    DEFAULT_AGE_GROUPS,
    DEFAULT_TRIM_SIZES,
    DEFAULT_WORKFLOW_MODES,
    calculate_spine_width,
)
from curiokraft_book.data.base import (
    BookRecord,
    PageRecord,
)
from curiokraft_book.data.base import (
    PromptRecord as StoragePromptRecord,
)
from curiokraft_book.data.hybrid_store import HybridDataStore
from curiokraft_book.orchestrator.debate_engine import synthesize_prompts
from curiokraft_book.rescue.binarizer import rescue_binarize
from curiokraft_book.schemas.prompt_manifest import PromptItem

logger = logging.getLogger("curiokraft.api")

api_router = APIRouter(prefix="/api", tags=["CurioKraft Publishing Studio"])


def get_store(request: Request) -> HybridDataStore:
    """Dependency: retrieve HybridDataStore from application state."""
    if not hasattr(request.app.state, "store") or request.app.state.store is None:
        # Fallback lazily to a default instance if not pre-initialized
        request.app.state.store = HybridDataStore()
    return request.app.state.store


# ------------------------------------------------------------------------------
# System & Health Endpoints
# ------------------------------------------------------------------------------


@api_router.get("/health", response_model=HealthResponse)
async def get_health(store: HybridDataStore = Depends(get_store)) -> HealthResponse:
    """Check service health and database connectivity."""
    db_status = "connected"
    try:
        with store.db_mgr.session_factory() as session:
            session.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning(f"Database health check degraded: {e}")
        db_status = f"degraded: {e}"

    storage_backend_name = getattr(store.storage, "backend_type", "local_disk")

    return HealthResponse(
        status="ok" if "connected" in db_status else "degraded",
        version=__version__,
        db_status=db_status,
        storage_backend=storage_backend_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@api_router.get("/config", response_model=SystemConfigResponse)
async def get_system_config() -> SystemConfigResponse:
    """Retrieve production system defaults, trim sizes, and workflow modes."""
    return SystemConfigResponse(
        version=__version__,
        dpi=CANVAS_DPI,
        default_trim_sizes=DEFAULT_TRIM_SIZES,
        default_age_groups=DEFAULT_AGE_GROUPS,
        workflow_modes=DEFAULT_WORKFLOW_MODES,
    )


# ------------------------------------------------------------------------------
# Book Management Endpoints
# ------------------------------------------------------------------------------


@api_router.get("/books", response_model=list[BookResponse])
async def list_books(store: HybridDataStore = Depends(get_store)) -> list[BookResponse]:
    """List all registered coloring book projects."""
    books = store.books.list_books()
    if not books:
        # Ensure default active book exists and return it
        active = store.active_book
        return [
            BookResponse(
                id=active.id,
                tenant_id=active.tenant_id,
                slug=active.slug,
                title=active.title,
                subtitle=active.subtitle,
                volume=active.volume,
                imprint=active.imprint,
                target_audience=active.target_audience,
                layout=active.layout,
                bleed=active.bleed,
                trim_width_in=active.trim_width_in,
                trim_height_in=active.trim_height_in,
                spine_width_in=active.spine_width_in,
                page_count=active.page_count,
                visual_style=active.visual_style,
                status=active.status,
                sync_status=active.sync_status.value
                if hasattr(active.sync_status, "value")
                else str(active.sync_status),
                version=active.version,
                created_at=active.created_at,
                updated_at=active.updated_at,
            )
        ]

    return [
        BookResponse(
            id=b.id,
            tenant_id=b.tenant_id,
            slug=b.slug,
            title=b.title,
            subtitle=b.subtitle,
            volume=b.volume,
            imprint=b.imprint,
            target_audience=b.target_audience,
            layout=b.layout,
            bleed=b.bleed,
            trim_width_in=b.trim_width_in,
            trim_height_in=b.trim_height_in,
            spine_width_in=b.spine_width_in,
            page_count=b.page_count,
            visual_style=b.visual_style,
            status=b.status,
            sync_status=b.sync_status.value
            if hasattr(b.sync_status, "value")
            else str(b.sync_status),
            version=b.version,
            created_at=b.created_at,
            updated_at=b.updated_at,
        )
        for b in books
    ]


@api_router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    payload: BookCreateRequest, store: HybridDataStore = Depends(get_store)
) -> BookResponse:
    """Create and initialize a new coloring book project."""
    slug = payload.slug or payload.title.lower().replace(" ", "-").replace("&", "and")
    # Sanitize slug
    slug = "".join(c for c in slug if c.isalnum() or c in "-_")

    existing = store.books.get_by_slug(slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Book with slug '{slug}' already exists (ID: {existing.id})",
        )

    spine_width = payload.spine_width_in or calculate_spine_width(payload.page_count)

    record = BookRecord(
        id=str(uuid4()),
        slug=slug,
        title=payload.title,
        subtitle=payload.subtitle,
        volume=payload.volume,
        imprint=payload.imprint,
        target_audience=payload.target_audience,
        layout=payload.layout,
        bleed=payload.bleed,
        trim_width_in=payload.trim_width_in,
        trim_height_in=payload.trim_height_in,
        spine_width_in=spine_width,
        page_count=payload.page_count,
        visual_style=payload.visual_style,
        status="DRAFT",
    )

    saved = store.books.save(record)

    await ws_manager.broadcast_log(
        level="INFO",
        message=f"Initialized new book '{saved.title}' ({saved.slug})",
        component="api",
        context={"book_id": saved.id, "slug": saved.slug},
    )

    return BookResponse(
        id=saved.id,
        tenant_id=saved.tenant_id,
        slug=saved.slug,
        title=saved.title,
        subtitle=saved.subtitle,
        volume=saved.volume,
        imprint=saved.imprint,
        target_audience=saved.target_audience,
        layout=saved.layout,
        bleed=saved.bleed,
        trim_width_in=saved.trim_width_in,
        trim_height_in=saved.trim_height_in,
        spine_width_in=saved.spine_width_in,
        page_count=saved.page_count,
        visual_style=saved.visual_style,
        status=saved.status,
        sync_status=saved.sync_status.value
        if hasattr(saved.sync_status, "value")
        else str(saved.sync_status),
        version=saved.version,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
    )


@api_router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: str, store: HybridDataStore = Depends(get_store)) -> BookResponse:
    """Retrieve book metadata by ID."""
    book = store.books.get_by_id(book_id)
    if not book:
        # Fallback to active book if matching
        if store.active_book and store.active_book.id == book_id:
            book = store.active_book
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Book not found: {book_id}"
            )

    return BookResponse(
        id=book.id,
        tenant_id=book.tenant_id,
        slug=book.slug,
        title=book.title,
        subtitle=book.subtitle,
        volume=book.volume,
        imprint=book.imprint,
        target_audience=book.target_audience,
        layout=book.layout,
        bleed=book.bleed,
        trim_width_in=book.trim_width_in,
        trim_height_in=book.trim_height_in,
        spine_width_in=book.spine_width_in,
        page_count=book.page_count,
        visual_style=book.visual_style,
        status=book.status,
        sync_status=book.sync_status.value
        if hasattr(book.sync_status, "value")
        else str(book.sync_status),
        version=book.version,
        created_at=book.created_at,
        updated_at=book.updated_at,
    )


@api_router.patch("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: str, payload: BookUpdateRequest, store: HybridDataStore = Depends(get_store)
) -> BookResponse:
    """Update book settings and recompute spine if needed."""
    book = store.books.get_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Book not found: {book_id}"
        )

    if payload.title is not None:
        book.title = payload.title
    if payload.subtitle is not None:
        book.subtitle = payload.subtitle
    if payload.trim_width_in is not None:
        book.trim_width_in = payload.trim_width_in
    if payload.trim_height_in is not None:
        book.trim_height_in = payload.trim_height_in
    if payload.page_count is not None:
        book.page_count = payload.page_count
        book.spine_width_in = calculate_spine_width(payload.page_count)
    if payload.bleed is not None:
        book.bleed = payload.bleed
    if payload.layout is not None:
        book.layout = payload.layout
    if payload.visual_style is not None:
        book.visual_style = payload.visual_style
    if payload.target_audience is not None:
        book.target_audience = payload.target_audience
    if payload.status is not None:
        book.status = payload.status

    book.updated_at = datetime.now(timezone.utc).isoformat()
    saved = store.books.save(book)
    return BookResponse(
        id=saved.id,
        tenant_id=saved.tenant_id,
        slug=saved.slug,
        title=saved.title,
        subtitle=saved.subtitle,
        volume=saved.volume,
        imprint=saved.imprint,
        target_audience=saved.target_audience,
        layout=saved.layout,
        bleed=saved.bleed,
        trim_width_in=saved.trim_width_in,
        trim_height_in=saved.trim_height_in,
        spine_width_in=saved.spine_width_in,
        page_count=saved.page_count,
        visual_style=saved.visual_style,
        status=saved.status,
        sync_status=saved.sync_status.value
        if hasattr(saved.sync_status, "value")
        else str(saved.sync_status),
        version=saved.version,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
    )


# ------------------------------------------------------------------------------
# Page Management Endpoints
# ------------------------------------------------------------------------------


@api_router.get("/books/{book_id}/pages", response_model=list[PageResponse])
async def list_book_pages(
    book_id: str, store: HybridDataStore = Depends(get_store)
) -> list[PageResponse]:
    """Retrieve all pages for a given book, syncing from manifest if empty."""
    pages = store.pages.get_pages_for_book(book_id)
    if not pages:
        # Check if manifest exists to seed initial pages
        manifest_path = store.manifest_path
        if manifest_path.exists():
            try:
                import json

                with open(manifest_path, encoding="utf-8") as f:
                    data = json.load(f)
                raw_pages = data.get("pages", [])
                page_records: list[PageRecord] = []
                for p in raw_pages:
                    pid = p.get("page_id") or f"P{p.get('page_number', 0):03d}"
                    rec = PageRecord(
                        book_id=book_id,
                        page_id=pid,
                        page_number=p.get("page_number", 0),
                        section=p.get("section", "General"),
                        canonical_object=p.get("canonical_object", p.get("display_label", "")),
                        display_label=p.get("display_label", ""),
                        page_type=p.get("page_type", "coloring_page"),
                        cards=p.get("cards", []),
                        status="planned",
                    )
                    page_records.append(rec)
                if page_records:
                    store.pages.bulk_save_pages(page_records)
                    pages = page_records
            except Exception as e:
                logger.warning(f"Could not auto-seed pages from manifest: {e}")

    return [
        PageResponse(
            id=p.id,
            book_id=p.book_id,
            page_id=p.page_id,
            page_number=p.page_number,
            section=p.section,
            canonical_object=p.canonical_object,
            display_label=p.display_label,
            page_type=p.page_type,
            cards=p.cards,
            status=p.status,
            attempts=p.attempts,
            max_attempts=p.max_attempts,
            qa_score=p.qa_score,
            qa_passed=p.qa_passed,
            violations=p.violations,
            positive_prompt=p.positive_prompt,
            negative_prompt=p.negative_prompt,
            raw_image_path=p.raw_image_path,
            rescued_image_path=p.rescued_image_path,
            composite_image_path=p.composite_image_path,
            sync_status=p.sync_status.value
            if hasattr(p.sync_status, "value")
            else str(p.sync_status),
            version=p.version,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in pages
    ]


@api_router.get("/books/{book_id}/pages/{page_id}", response_model=PageResponse)
async def get_book_page(
    book_id: str, page_id: str, store: HybridDataStore = Depends(get_store)
) -> PageResponse:
    """Retrieve detailed state for a single book page."""
    page = store.pages.get_page(book_id, page_id)
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_id} not found for book {book_id}",
        )
    return PageResponse(
        id=page.id,
        book_id=page.book_id,
        page_id=page.page_id,
        page_number=page.page_number,
        section=page.section,
        canonical_object=page.canonical_object,
        display_label=page.display_label,
        page_type=page.page_type,
        cards=page.cards,
        status=page.status,
        attempts=page.attempts,
        max_attempts=page.max_attempts,
        qa_score=page.qa_score,
        qa_passed=page.qa_passed,
        violations=page.violations,
        positive_prompt=page.positive_prompt,
        negative_prompt=page.negative_prompt,
        raw_image_path=page.raw_image_path,
        rescued_image_path=page.rescued_image_path,
        composite_image_path=page.composite_image_path,
        sync_status=page.sync_status.value
        if hasattr(page.sync_status, "value")
        else str(page.sync_status),
        version=page.version,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )


def _format_page_response(page: PageRecord) -> PageResponse:
    """Format PageRecord to PageResponse."""
    return PageResponse(
        id=page.id,
        book_id=page.book_id,
        page_id=page.page_id,
        page_number=page.page_number,
        section=page.section,
        canonical_object=page.canonical_object,
        display_label=page.display_label,
        page_type=page.page_type,
        cards=page.cards,
        status=page.status,
        attempts=page.attempts,
        max_attempts=page.max_attempts,
        qa_score=page.qa_score,
        qa_passed=page.qa_passed,
        violations=page.violations,
        positive_prompt=page.positive_prompt,
        negative_prompt=page.negative_prompt,
        raw_image_path=page.raw_image_path,
        rescued_image_path=page.rescued_image_path,
        composite_image_path=page.composite_image_path,
        sync_status=page.sync_status.value
        if hasattr(page.sync_status, "value")
        else str(page.sync_status),
        version=page.version,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )


def _match_file_to_page(file_stem: str, pages: list[PageRecord]) -> PageRecord | None:
    """Match a filename or stem against candidate book pages using page number, id, or canonical object."""
    import re

    clean = file_stem.lower().strip().replace(" ", "_")

    # 1. Try matching explicit page number: e.g. raw_p001, p001, raw_p1, p1, raw_p003_clownfish
    p_num_match = re.match(r"^(?:raw_)?p(\d+)(?:[_-].*)?$", clean)
    if p_num_match:
        target_num = int(p_num_match.group(1))
        for p in pages:
            if p.page_number == target_num:
                return p

    # 2. Try matching page_id: e.g. P001, p001
    for p in pages:
        pid = p.page_id.lower().strip()
        if clean == pid or clean == f"raw_{pid}":
            return p

    # 3. Try matching canonical_object: e.g. clownfish, blue_tang
    for p in pages:
        if p.canonical_object:
            canon = p.canonical_object.lower().strip().replace(" ", "_")
            if canon and (canon in clean or clean in canon):
                return p

    return None


# ------------------------------------------------------------------------------
# Asset Ingestion & Drop Target Upload Endpoints
# ------------------------------------------------------------------------------


@api_router.post("/books/{book_id}/ingest/upload", response_model=IngestUploadResponse)
async def upload_book_raw_pages(
    book_id: str,
    files: list[UploadFile] = File(...),
    auto_rescue: bool = Query(True, description="Automatically run pre-QA binarization rescue"),
    store: HybridDataStore = Depends(get_store),
) -> IngestUploadResponse:
    """Accept drag-and-drop raw illustrations, persist to inbox/raw_pages, and bind to book pages."""
    pages = store.pages.get_pages_for_book(book_id) or store.get_all_pages()
    inbox_dir = Path("inbox/raw_pages")
    inbox_dir.mkdir(parents=True, exist_ok=True)
    generated_dir = Path("generated/raw_pages")
    generated_dir.mkdir(parents=True, exist_ok=True)

    total_files = len(files)
    matched_pages: list[PageResponse] = []
    unmatched_files: list[str] = []
    rescued_count = 0

    for upload_file in files:
        raw_name = upload_file.filename or f"raw_{uuid4().hex[:8]}.png"
        safe_name = raw_name.replace(" ", "_")
        dest_path = inbox_dir / safe_name

        try:
            content = await upload_file.read()
            with open(dest_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to write uploaded file {safe_name}: {e}")
            unmatched_files.append(safe_name)
            continue

        matched_page = _match_file_to_page(dest_path.stem, pages)
        if matched_page:
            raw_rel_path = f"/inbox/raw_pages/{safe_name}"
            rescued_rel_path = matched_page.rescued_image_path
            new_status = "GENERATED"

            if auto_rescue:
                canon_str = matched_page.canonical_object or dest_path.stem
                rescued_name = f"raw_p{matched_page.page_number:03d}_{canon_str}_rescued.png"
                rescued_dest = generated_dir / rescued_name
                try:
                    res = rescue_binarize(input_path=dest_path, output_path=rescued_dest)
                    if res.success and rescued_dest.exists() and rescued_dest.stat().st_size > 0:
                        rescued_rel_path = f"/generated/raw_pages/{rescued_name}"
                        new_status = "RESCUED"
                        rescued_count += 1
                except Exception as e:
                    logger.warning(f"Auto-rescue binarization failed for {dest_path.name}: {e}")

            updated_page = store.update_page(
                matched_page.page_id,
                raw_image_path=raw_rel_path,
                rescued_image_path=rescued_rel_path,
                status=new_status,
            )
            matched_pages.append(_format_page_response(updated_page))
        else:
            unmatched_files.append(safe_name)

    await ws_manager.broadcast_log(
        level="INFO",
        message=f"Uploaded {total_files} illustrations: {len(matched_pages)} matched to pages, {rescued_count} rescued",
        component="ingestion",
        context={
            "book_id": book_id,
            "matched": len(matched_pages),
            "unmatched": len(unmatched_files),
        },
    )
    await ws_manager.broadcast_progress(
        stage="ingestion",
        progress_percentage=min(100.0, (len(matched_pages) / max(1, len(pages))) * 100.0),
        message=f"Ingested {len(matched_pages)} raw illustrations into book pages",
    )

    return IngestUploadResponse(
        total_files=total_files,
        matched_pages=len(matched_pages),
        rescued_count=rescued_count,
        unmatched_files=unmatched_files,
        processed_pages=matched_pages,
        message=f"Successfully ingested {len(matched_pages)} illustrations",
    )


@api_router.post("/books/{book_id}/ingest/scan", response_model=IngestUploadResponse)
async def scan_book_inbox_pages(
    book_id: str,
    auto_rescue: bool = Query(True, description="Automatically run pre-QA binarization rescue"),
    store: HybridDataStore = Depends(get_store),
) -> IngestUploadResponse:
    """Scan existing illustrations in inbox/raw_pages/ and link them to book pages."""
    pages = store.pages.get_pages_for_book(book_id) or store.get_all_pages()
    inbox_dir = Path("inbox/raw_pages")
    generated_dir = Path("generated/raw_pages")
    generated_dir.mkdir(parents=True, exist_ok=True)

    if not inbox_dir.exists():
        return IngestUploadResponse(
            total_files=0,
            matched_pages=0,
            rescued_count=0,
            message="inbox/raw_pages directory does not exist",
        )

    valid_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    candidate_files = [
        f
        for f in inbox_dir.iterdir()
        if f.is_file() and f.suffix.lower() in valid_extensions and f.stat().st_size > 500
    ]

    matched_pages: list[PageResponse] = []
    unmatched_files: list[str] = []
    rescued_count = 0

    for file_path in candidate_files:
        matched_page = _match_file_to_page(file_path.stem, pages)
        if matched_page:
            raw_rel_path = f"/inbox/raw_pages/{file_path.name}"
            rescued_rel_path = matched_page.rescued_image_path
            new_status = "received"

            if auto_rescue:
                canon_str = matched_page.canonical_object or file_path.stem
                rescued_name = f"raw_p{matched_page.page_number:03d}_{canon_str}_rescued.png"
                rescued_dest = generated_dir / rescued_name
                if not rescued_dest.exists() or rescued_dest.stat().st_size == 0:
                    try:
                        res = rescue_binarize(input_path=file_path, output_path=rescued_dest)
                        if res.success and rescued_dest.exists():
                            rescued_rel_path = f"/generated/raw_pages/{rescued_name}"
                            new_status = "RESCUED"
                            rescued_count += 1
                    except Exception as e:
                        logger.warning(f"Rescue failed during scan for {file_path.name}: {e}")
                else:
                    rescued_rel_path = f"/generated/raw_pages/{rescued_name}"
                    new_status = "RESCUED"
                    rescued_count += 1

            updated_page = store.update_page(
                matched_page.page_id,
                raw_image_path=raw_rel_path,
                rescued_image_path=rescued_rel_path,
                status=new_status,
            )
            matched_pages.append(_format_page_response(updated_page))
        else:
            unmatched_files.append(file_path.name)

    await ws_manager.broadcast_log(
        level="INFO",
        message=f"Scanned inbox: {len(candidate_files)} files found, {len(matched_pages)} matched to pages, {rescued_count} rescued",
        component="ingestion",
    )
    return IngestUploadResponse(
        total_files=len(candidate_files),
        matched_pages=len(matched_pages),
        rescued_count=rescued_count,
        unmatched_files=unmatched_files,
        processed_pages=matched_pages,
        message=f"Successfully scanned inbox: {len(matched_pages)} pages linked",
    )


@api_router.post("/ingest/upload", response_model=IngestUploadResponse)
async def upload_raw_pages_default(
    files: list[UploadFile] = File(...),
    auto_rescue: bool = Query(True),
    store: HybridDataStore = Depends(get_store),
) -> IngestUploadResponse:
    """Convenience endpoint uploading directly to active book."""
    return await upload_book_raw_pages(
        book_id=store.active_book.id, files=files, auto_rescue=auto_rescue, store=store
    )


@api_router.post("/ingest/scan", response_model=IngestUploadResponse)
async def scan_inbox_pages_default(
    auto_rescue: bool = Query(True),
    store: HybridDataStore = Depends(get_store),
) -> IngestUploadResponse:
    """Convenience endpoint scanning directly into active book."""
    return await scan_book_inbox_pages(
        book_id=store.active_book.id, auto_rescue=auto_rescue, store=store
    )


# ------------------------------------------------------------------------------
# Prompt Synthesis & Arsenal Endpoints
# ------------------------------------------------------------------------------


@api_router.get("/books/{book_id}/prompts", response_model=list[PromptItem])
async def list_book_prompts(
    book_id: str, store: HybridDataStore = Depends(get_store)
) -> list[PromptItem]:
    """Retrieve prompts stored for a book."""
    db_prompts = store.prompts.list_prompts_for_book(book_id)
    items: list[PromptItem] = []
    for p in db_prompts:
        preset: Literal["CurioKraft - Interior Coloring Pages", "CurioKraft - Cover Art Master"] = (
            "CurioKraft - Cover Art Master"
            if p.preset_name == "CurioKraft - Cover Art Master"
            or "cover" in (p.prompt_type or "").lower()
            else "CurioKraft - Interior Coloring Pages"
        )
        items.append(
            PromptItem(
                id=p.page_id or p.id,
                page_number=None,
                label=p.prompt_type.replace("_", " ").title(),
                type="interior_page" if p.prompt_type == "interior_page" else "front_cover",
                section="General",
                drop_target=f"inbox/raw_pages/raw_{p.page_id}.png"
                if p.page_id
                else "inbox/cover/cover.png",
                preset_name=preset,
                aspect_ratio=p.aspect_ratio,
                temperature=p.temperature,
                top_p=p.top_p,
                positive_prompt=p.positive_prompt,
                negative_prompt=p.negative_prompt,
                chat_id=p.chat_id,
            )
        )
    return items


@api_router.post("/books/{book_id}/prompts/synthesize", response_model=PromptManifestResponse)
async def trigger_prompt_synthesis(
    book_id: str,
    payload: PromptSynthesizeRequest = PromptSynthesizeRequest(),
    count: int | None = Query(None, description="Optional count limit (e.g. 5 for testing)"),
    store: HybridDataStore = Depends(get_store),
) -> PromptManifestResponse:
    """Execute pure multi-agent prompt synthesis and cache results in SQL repository."""
    book = store.books.get_by_id(book_id)
    book_title = book.title if book else "CurioKraft Coloring Book"
    volume = book.volume if book else "vol1"

    await ws_manager.broadcast_log(
        level="INFO",
        message=f"Starting multi-agent prompt synthesis for book '{book_title}' (limit: {count or 'all'})",
        component="debate_engine",
        context={"book_id": book_id, "limit": count},
    )

    try:
        prompt_items = synthesize_prompts(
            manifest_path=payload.pages_csv_path,
            count=count,
        )

        # Cache prompts into SQL PromptRepository
        for item in prompt_items:
            p_rec = StoragePromptRecord(
                book_id=book_id,
                page_id=item.id,
                prompt_type=item.type,
                positive_prompt=item.positive_prompt,
                negative_prompt=item.negative_prompt,
                temperature=item.temperature,
                top_p=item.top_p,
                aspect_ratio=item.aspect_ratio,
                preset_name=item.preset_name,
                chat_id=item.chat_id,
            )
            store.prompts.save_prompt(p_rec)

        await ws_manager.broadcast_progress(
            stage="prompts",
            progress_percentage=100.0,
            message=f"Successfully synthesized {len(prompt_items)} prompts",
            details={"total_prompts": len(prompt_items)},
        )

        return PromptManifestResponse(
            book_title=book_title,
            book_id=book_id,
            volume=volume,
            total_prompts=len(prompt_items),
            prompts=prompt_items,
        )
    except Exception as e:
        logger.exception("Error during prompt synthesis")
        await ws_manager.broadcast_log(
            level="ERROR",
            message=f"Prompt synthesis failed: {e}",
            component="debate_engine",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prompt synthesis failed: {e}",
        ) from e


# ------------------------------------------------------------------------------
# Production Status & 6-Stage Wizard Endpoints
# ------------------------------------------------------------------------------


@api_router.get("/books/{book_id}/status", response_model=BookProductionStatusResponse)
async def get_book_production_status(
    book_id: str, store: HybridDataStore = Depends(get_store)
) -> BookProductionStatusResponse:
    """Retrieve the real-time aggregated completion status across all 6 publishing stages."""
    book = store.books.get_by_id(book_id)
    if not book and store.active_book and store.active_book.id == book_id:
        book = store.active_book

    title = book.title if book else "Unknown Book"
    target_pages = book.page_count if book else 110

    pages = store.pages.get_pages_for_book(book_id)
    total_pages = len(pages) or target_pages
    planned = sum(1 for p in pages if (p.status or "").upper() == "PLANNED")
    inbox_received = sum(
        1
        for p in pages
        if p.raw_image_path is not None
        or (p.status or "").upper()
        in ("RECEIVED", "GENERATED", "RESCUING", "RESCUED", "PASSED", "APPROVED", "COMPOSITED")
    )
    rescued = sum(
        1
        for p in pages
        if p.rescued_image_path is not None
        or (p.status or "").upper()
        in ("RESCUED", "PASSED", "APPROVED", "COMPOSITED", "TECHNICAL_QA_PASSED")
    )
    qa_passed = sum(
        1
        for p in pages
        if p.qa_passed
        or (p.status or "").upper()
        in ("PASSED", "TECHNICAL_QA_PASSED", "VISION_QA_PASSED", "APPROVED", "COMPOSITED")
    )
    composited = sum(
        1
        for p in pages
        if p.composite_image_path is not None
        or (p.status or "").upper() in ("COMPOSITED", "APPROVED")
    )

    prompts = store.prompts.list_prompts_for_book(book_id)
    prompts_count = len(prompts)

    # Calculate 6 stages
    stage_1_blueprint = PipelineStageStatus(
        stage_id="blueprint",
        title="1. Blueprint & Manifest",
        status="completed" if total_pages >= target_pages else "in_progress",
        progress_percentage=min(100.0, (total_pages / max(1, target_pages)) * 100.0),
        completed_items=total_pages,
        total_items=target_pages,
    )

    stage_2_prompts = PipelineStageStatus(
        stage_id="prompts",
        title="2. Prompt Arsenal Synthesis",
        status="completed"
        if prompts_count >= target_pages
        else ("in_progress" if prompts_count > 0 else "pending"),
        progress_percentage=min(100.0, (prompts_count / max(1, target_pages)) * 100.0),
        completed_items=prompts_count,
        total_items=target_pages,
    )

    stage_3_ingestion = PipelineStageStatus(
        stage_id="ingestion",
        title="3. Ingestion & Pre-QA Rescue",
        status="completed"
        if rescued >= target_pages
        else ("in_progress" if inbox_received > 0 else "pending"),
        progress_percentage=min(100.0, (rescued / max(1, target_pages)) * 100.0),
        completed_items=rescued,
        total_items=target_pages,
    )

    stage_4_masters = PipelineStageStatus(
        stage_id="masters",
        title="4. Composite Masters (600 DPI)",
        status="completed"
        if composited >= target_pages
        else ("in_progress" if composited > 0 else "pending"),
        progress_percentage=min(100.0, (composited / max(1, target_pages)) * 100.0),
        completed_items=composited,
        total_items=target_pages,
    )

    stage_5_preflight = PipelineStageStatus(
        stage_id="preflight",
        title="5. KDP Preflight Diagnostic",
        status="completed"
        if qa_passed >= target_pages
        else ("in_progress" if qa_passed > 0 else "pending"),
        progress_percentage=min(100.0, (qa_passed / max(1, target_pages)) * 100.0),
        completed_items=qa_passed,
        total_items=target_pages,
    )

    stage_6_kdp = PipelineStageStatus(
        stage_id="kdp",
        title="6. KDP Submission Bundle",
        status="pending",
        progress_percentage=0.0,
        completed_items=0,
        total_items=1,
    )

    stages = [
        stage_1_blueprint,
        stage_2_prompts,
        stage_3_ingestion,
        stage_4_masters,
        stage_5_preflight,
        stage_6_kdp,
    ]

    overall_progress = sum(s.progress_percentage for s in stages) / len(stages)

    # Determine active stage
    active_stage = "blueprint"
    for s in stages:
        if s.status != "completed":
            active_stage = s.stage_id
            break

    return BookProductionStatusResponse(
        book_id=book_id,
        book_title=title,
        overall_progress=round(overall_progress, 1),
        active_stage=active_stage,
        stages=stages,
        page_stats={
            "total_pages": total_pages,
            "planned": planned,
            "inbox_received": inbox_received,
            "rescued": rescued,
            "qa_passed": qa_passed,
            "composited": composited,
        },
    )


# ------------------------------------------------------------------------------
# Telemetry & Logging Endpoints
# ------------------------------------------------------------------------------


@api_router.get("/telemetry/logs", response_model=list[dict[str, Any]])
async def get_recent_telemetry_logs() -> list[dict[str, Any]]:
    """Retrieve buffered telemetry logs for the frontend console log drawer."""
    return ws_manager.get_recent_logs()


@api_router.post("/telemetry/logs")
async def ingest_client_log(event: TelemetryLogEvent) -> dict[str, str]:
    """Receive client-side log from the React app and broadcast to connected debuggers."""
    await ws_manager.broadcast_log(
        level=event.level,
        message=event.message,
        component=event.component,
        context=event.context,
    )
    return {"status": "broadcasted"}


# ------------------------------------------------------------------------------
# WebSocket Real-Time Channel
# ------------------------------------------------------------------------------


@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Full-duplex real-time channel for logs, progress, and multi-agent events."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                import json

                msg = json.loads(data)
                msg_type = msg.get("type", "ping")
                if msg_type == "ping":
                    await websocket.send_json(
                        {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}
                    )
                elif msg_type == "client_log":
                    await ws_manager.broadcast_log(
                        level=msg.get("level", "INFO"),
                        message=msg.get("message", ""),
                        component=msg.get("component", "client"),
                        context=msg.get("context", {}),
                    )
            except Exception as e:
                logger.debug(f"Non-JSON or malformed message on websocket: {e}")
                await websocket.send_json({"type": "pong", "echo": data})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        await ws_manager.disconnect(websocket)
