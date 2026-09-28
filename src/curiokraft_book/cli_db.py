"""Database CLI management commands for CurioKraft.

Commands:
- init: Initialize database schema (PostgreSQL or local SQLite).
- status: Check database health, connection, and entity record counts.
- sync: Execute bi-directional sync between local offline store and Cloudflare R2 / Neon.
- migrate-from-fs: Ingest filesystem manifests, book configs, and pipeline state into database.
- sync-assets: Index on-disk images, compute SHA-256 hashes, and populate media_assets.
- export-to-fs: Export database state back to pipeline_state.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import re
from uuid import uuid4

from curiokraft_book.constants import (
    DEFAULT_BOOK_CONFIG,
    DEFAULT_PAGES_MANIFEST,
    DEFAULT_PIPELINE_STATE_FILE,
)
from curiokraft_book.data.base import (
    BookRecord,
    MediaAssetRecord,
    PageRecord,
    PromptRecord,
)
from curiokraft_book.data.hybrid_store import HybridDataStore, get_data_store
from curiokraft_book.data.sync_engine import SyncEngine

load_dotenv()

db_app = typer.Typer(help="[Data & Cloud] Centralized database and S3/R2 storage operations")
console = Console(force_terminal=True, legacy_windows=False)


@db_app.command("init")
def db_init():
    """Initialize relational database schema and create required tables."""
    store = get_data_store()
    store.db_mgr.init_db()
    console.print(
        Panel.fit(
            f"[bold green]Database schema initialized successfully![/bold green]\n"
            f"[dim]Engine URL: {store.db_mgr.db_url}[/dim]",
            title="[bold green]CurioKraft DB Init[/bold green]",
            border_style="green",
        )
    )


def _scan_and_index_all_assets(store: HybridDataStore) -> int:
    """Scan all standard asset directories, register in DB, and upload to MinIO/S3."""
    indexed = 0

    # 1. Composite Masters (output/interior_masters/)
    masters_dir = Path("output/interior_masters")
    if masters_dir.exists():
        for f in sorted(masters_dir.glob("page_*.png")):
            m = re.search(r"(\d+)", f.stem)
            page_id = f"P{int(m.group(1)):03d}" if m else None
            try:
                store.register_media_asset(f, asset_type="composite_master", page_id=page_id)
                indexed += 1
            except Exception as e:
                console.print(f"[red]Failed indexing master {f.name}:[/] {e}")

    # 2. Raw Pages (inbox/raw_pages/ or generated/raw_pages/)
    raw_dirs = [Path("inbox/raw_pages"), Path("generated/raw_pages")]
    seen_raw_pages: set[str] = set()
    for r_dir in raw_dirs:
        if not r_dir.exists():
            continue
        for f in sorted(r_dir.glob("raw_p*.png")):
            m = re.search(r"p(\d+)", f.stem.lower())
            if m:
                page_id = f"P{int(m.group(1)):03d}"
                if page_id in seen_raw_pages:
                    continue
                seen_raw_pages.add(page_id)
                try:
                    store.register_media_asset(f, asset_type="raw_image", page_id=page_id)
                    indexed += 1
                except Exception as e:
                    console.print(f"[red]Failed indexing raw page {f.name}:[/] {e}")

    # 3. Cover Assets (output/cover/ and inbox covers)
    cover_dir = Path("output/cover")
    if cover_dir.exists():
        for f in sorted(cover_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in [".png", ".pdf"]:
                p_id = "COVER_CMYK_PDF" if f.suffix.lower() == ".pdf" else "COVER_300DPI_PNG"
                try:
                    store.register_media_asset(f, asset_type="cover_asset", page_id=p_id)
                    indexed += 1
                except Exception as e:
                    console.print(f"[red]Failed indexing cover {f.name}:[/] {e}")

    for cov_cand, p_id in [
        (Path("inbox/front_cover.png"), "COVER_FRONT"),
        (Path("inbox/back_cover.png"), "COVER_BACK"),
    ]:
        if cov_cand.exists():
            try:
                store.register_media_asset(cov_cand, asset_type="cover_asset", page_id=p_id)
                indexed += 1
            except Exception as e:
                console.print(f"[red]Failed indexing inbox cover {cov_cand.name}:[/] {e}")

    # 4. Interior PDF (output/interior/)
    interior_dir = Path("output/interior")
    if interior_dir.exists():
        for f in sorted(interior_dir.glob("*.pdf")):
            try:
                store.register_media_asset(f, asset_type="interior_pdf", page_id=None)
                indexed += 1
            except Exception as e:
                console.print(f"[red]Failed indexing interior PDF {f.name}:[/] {e}")

    return indexed


@db_app.command("status")
def db_status(
    slug: str | None = typer.Option(None, "--slug", help="Target book slug in database"),
):
    """Display database connection status and entity counts."""
    store = get_data_store(book_slug=slug)
    try:
        books = store.books.list_books()
        pages = store.get_all_pages()
        active_b = store.active_book

        prompts = store.prompts.list_prompts_for_book(active_b.id)
        assets = store.assets.list_assets_for_book(active_b.id)

        summary = {}
        for p in pages:
            summary[p.status] = summary.get(p.status, 0) + 1

        table = Table(title="CurioKraft Centralized Database Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Database Engine", store.db_mgr.db_url)
        table.add_row("Storage Backend", store.storage.__class__.__name__)
        table.add_row("Active Book", f"{active_b.title} ({active_b.slug})")
        table.add_row("Total Books", str(len(books)))
        table.add_row("Total Pages in Active Book", str(len(pages)))

        for st, count in sorted(summary.items()):
            table.add_row(f"  Pages [{st}]", str(count))

        table.add_row("Total Prompts Stored", str(len(prompts)))
        table.add_row("Total Media Assets Stored", str(len(assets)))

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Failed connecting to database:[/] {e}")


@db_app.command("migrate-from-fs")
def db_migrate_from_fs(
    manifest_path: Path = typer.Option(DEFAULT_PAGES_MANIFEST, "--manifest", "-m"),
    config_path: Path = typer.Option(DEFAULT_BOOK_CONFIG, "--config", "-c"),
    state_path: Path = typer.Option(DEFAULT_PIPELINE_STATE_FILE, "--state", "-s"),
    include_images: bool = typer.Option(
        True,
        "--images/--no-images",
        help="Scan and migrate on-disk images to database and object storage",
    ),
    include_prompts: bool = typer.Option(
        True,
        "--prompts/--no-prompts",
        help="Migrate generation prompts from pipeline state into database",
    ),
    slug: str | None = typer.Option(None, "--slug", help="Target book slug in database"),
):
    """Ingest existing filesystem manifests, book configs, prompts, and images into database."""
    store = get_data_store(book_slug=slug)
    console.print(f"[cyan]Migrating book configuration from {config_path}...[/cyan]")

    book_title = "Tiny Hands Color & Learn"
    subtitle = ""
    volume = "vol1"
    imprint = "CurioKraft Publications"
    target_audience = {}
    layout = "single_sided"
    bleed = False
    trim_width_in = 8.5
    trim_height_in = 11.0
    spine_width_in = 0.248
    page_count = 110
    visual_style = {}

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        b_cfg = cfg.get("book", {})
        book_title = b_cfg.get("title", book_title)
        subtitle = b_cfg.get("subtitle", "")
        volume = str(b_cfg.get("volume", volume)).lower()
        imprint = b_cfg.get("brand", imprint)
        target_audience = b_cfg.get("target_audience", {})

        i_cfg = b_cfg.get("interior", {})
        page_count = int(i_cfg.get("page_count", page_count))
        layout = i_cfg.get("layout", layout)
        bleed = bool(i_cfg.get("bleed", bleed))
        trim_cfg = i_cfg.get("trim_size", {})
        trim_width_in = float(trim_cfg.get("width_in", trim_width_in))
        trim_height_in = float(trim_cfg.get("height_in", trim_height_in))

        c_cfg = b_cfg.get("cover", {})
        spine_width_in = float(c_cfg.get("spine_width_in", spine_width_in))

        visual_style = b_cfg.get("visual_style", {})

    target_slug = slug or f"curiokraft-{volume}"
    book = store.books.get_by_slug(target_slug)
    if book:
        book.title = book_title
        book.subtitle = subtitle
        book.volume = volume
        book.imprint = imprint
        book.target_audience = target_audience
        book.layout = layout
        book.bleed = bleed
        book.trim_width_in = trim_width_in
        book.trim_height_in = trim_height_in
        book.spine_width_in = spine_width_in
        book.page_count = page_count
        book.visual_style = visual_style
        book.status = "IN_PRODUCTION"
        book = store.books.save(book)
    else:
        book = store.books.save(
            BookRecord(
                slug=target_slug,
                title=book_title,
                subtitle=subtitle,
                volume=volume,
                imprint=imprint,
                target_audience=target_audience,
                layout=layout,
                bleed=bleed,
                trim_width_in=trim_width_in,
                trim_height_in=trim_height_in,
                spine_width_in=spine_width_in,
                page_count=page_count,
                visual_style=visual_style,
                status="IN_PRODUCTION",
            )
        )

    store.active_book = book

    migrated_pages = 0
    # Ingest manifest definitions
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            m_data = json.load(f)
        for item in m_data.get("pages", []):
            p = PageRecord(
                book_id=book.id,
                page_id=item["page_id"],
                page_number=item["page_number"],
                canonical_object=item["canonical_object"],
                display_label=item.get("display_label", item["canonical_object"].upper()),
                section=item.get("section", "General"),
                cards=item.get("cards", []),
                page_type=item.get("type", "coloring_page"),
            )
            store.pages.save_page(p)
            migrated_pages += 1

    migrated_prompts = 0
    # Ingest pipeline_state.json if present
    if state_path.exists():
        with open(state_path, encoding="utf-8") as f:
            s_data = json.load(f)
        for p_id, rec in s_data.get("pages", {}).items():
            clean_kwargs = {k: v for k, v in rec.items() if k != "page_id"}
            store.update_page(p_id, **clean_kwargs)

            # Ingest prompt if enabled and prompt is present
            if include_prompts and rec.get("positive_prompt"):
                prompt_type = (
                    "welcome_page"
                    if p_id == "P001"
                    else (
                        "certificate_page" if p_id in ["P109", "P110"] else "interior_page"
                    )
                )
                existing_pr = store.prompts.get_prompt(book.id, p_id, prompt_type)
                pr_id = existing_pr.id if existing_pr else str(uuid4())
                pr = PromptRecord(
                    id=pr_id,
                    book_id=book.id,
                    page_id=p_id,
                    prompt_type=prompt_type,
                    positive_prompt=rec["positive_prompt"],
                    negative_prompt=rec.get("negative_prompt", "") or "",
                    is_locked=True,
                )
                store.prompts.save_prompt(pr)
                migrated_prompts += 1

    # Ingest standalone prompt exports if present (e.g. cover & special assets)
    prompts_export_file = Path("generated/prompts_export.json")
    if include_prompts and prompts_export_file.exists():
        try:
            with open(prompts_export_file, encoding="utf-8") as f:
                pe_data = json.load(f)
            for item in pe_data.get("prompts", []):
                p_id = item.get("id")
                p_type = item.get("type", "interior_page")
                if p_type in ["front_cover", "back_cover", "special_asset"]:
                    existing_pr = store.prompts.get_prompt(book.id, p_id, p_type)
                    pr_id = existing_pr.id if existing_pr else str(uuid4())
                    pr = PromptRecord(
                        id=pr_id,
                        book_id=book.id,
                        page_id=p_id,
                        prompt_type=p_type,
                        positive_prompt=item.get("positive_prompt", ""),
                        negative_prompt=item.get("negative_prompt", "") or "",
                        temperature=item.get("temperature", 0.9),
                        top_p=item.get("top_p", 0.95),
                        aspect_ratio=item.get("aspect_ratio", "3:4"),
                        preset_name=item.get("preset_name", "CurioKraft - Cover Art Master"),
                        is_locked=True,
                    )
                    store.prompts.save_prompt(pr)
                    migrated_prompts += 1
        except Exception as e:
            logger.debug(f"Notice reading prompts export file: {e}")

    # Ingest images and media assets into DB and S3/MinIO
    migrated_assets = 0
    if include_images:
        console.print("[cyan]Scanning on-disk images and indexing into database & storage...[/cyan]")
        migrated_assets = _scan_and_index_all_assets(store)

    table = Table(title=f"Migration Complete: {book.title} ({book.slug})")
    table.add_column("Entity", style="cyan")
    table.add_column("Migrated Count", style="green")
    table.add_row("Pages", str(migrated_pages))
    table.add_row("Prompts", str(migrated_prompts))
    table.add_row("Media Assets (CAS Indexed)", str(migrated_assets))
    table.add_row("Storage Backend", store.storage.__class__.__name__)
    console.print(table)


@db_app.command("sync-assets")
def db_sync_assets(
    directory: Path | None = typer.Option(
        None, "--dir", "-d", help="Directory to scan (default: output/interior_masters)"
    ),
    asset_type: str = typer.Option("composite_master", "--type", "-t"),
    all_assets: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Scan and sync all standard directories (masters, raw, covers, pdfs)",
    ),
    slug: str | None = typer.Option(None, "--slug", help="Target book slug in database"),
):
    """Scan directory of images, compute SHA-256 hashes, and index into media_assets."""
    store = get_data_store(book_slug=slug)
    if all_assets:
        console.print(
            f"[cyan]Scanning and indexing ALL asset categories for '{store.active_book.slug}'...[/cyan]"
        )
        indexed = _scan_and_index_all_assets(store)
        console.print(
            f"[bold green]Indexed {indexed} media assets with SHA-256 content hashes.[/bold green]"
        )
        return

    target_dir = directory or Path("output/interior_masters")
    if not target_dir.exists():
        console.print(f"[yellow]Directory {target_dir} does not exist.[/yellow]")
        return

    valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
    files = [f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]

    console.print(f"[cyan]Indexing {len(files)} files from {target_dir}...[/cyan]")
    indexed = 0
    for f in files:
        # Determine page_id from name if possible (e.g. page_001.png -> P001)
        m = re.search(r"(\d+)", f.stem)
        page_id = f"P{int(m.group(1)):03d}" if m else None

        try:
            store.register_media_asset(f, asset_type=asset_type, page_id=page_id)
            indexed += 1
        except Exception as e:
            console.print(f"[red]Failed indexing {f.name}:[/] {e}")

    console.print(
        f"[bold green]Indexed {indexed} media assets with SHA-256 content hashes.[/bold green]"
    )


@db_app.command("pull-assets")
def db_pull_assets(
    directory: Path | None = typer.Option(
        None,
        "--dir",
        "-d",
        help="Destination folder (default: standard output folders e.g. output/interior_masters/)",
    ),
    asset_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by type (composite_master, interior_pdf, cover_asset, raw_image)",
    ),
    slug: str | None = typer.Option(None, "--slug", help="Target book slug in database"),
    verify_hash: bool = typer.Option(
        True,
        "--verify-hash/--no-verify-hash",
        help="Verify SHA-256 integrity against database records",
    ),
):
    """Pull assets from database & MinIO down to local machine and verify file integrity."""
    from curiokraft_book.data.object_storage import compute_sha256

    store = get_data_store(book_slug=slug)
    book = store.active_book
    console.print(
        Panel.fit(
            f"[bold cyan]Pulling Assets for '{book.title}' ({book.slug}) from MinIO/DB[/bold cyan]"
        )
    )

    all_assets = store.assets.list_assets_for_book(book.id)
    if asset_type:
        all_assets = [a for a in all_assets if a.asset_type.lower() == asset_type.lower()]

    if not all_assets:
        console.print(
            f"[yellow]No assets found in database for book '{book.slug}' (filter: {asset_type or 'all'}).[/yellow]"
        )
        return

    console.print(
        f"[cyan]Found {len(all_assets)} asset records in database. Downloading & verifying...[/cyan]\n"
    )

    standard_dirs = {
        "composite_master": Path("output/interior_masters"),
        "interior_pdf": Path("output/interior"),
        "cover_asset": Path("output/cover"),
        "raw_image": Path("generated/raw_pages"),
    }

    pulled = 0
    verified = 0
    failed = 0

    for asset in all_assets:
        filename = Path(asset.storage_key).name
        if directory:
            dest_file = directory / filename
        else:
            folder = standard_dirs.get(asset.asset_type, Path("output/downloaded"))
            dest_file = folder / filename

        dest_file.parent.mkdir(parents=True, exist_ok=True)
        ok = store.storage.download_file(asset.storage_key, str(dest_file))
        if not ok:
            console.print(
                f"  [red][FAIL][/red] Failed to download {filename} from {asset.storage_key}"
            )
            failed += 1
            continue

        pulled += 1
        if verify_hash:
            local_hash = compute_sha256(dest_file)
            if local_hash == asset.sha256_hash:
                verified += 1
                console.print(
                    f"  [green][VERIFIED][/green] {filename} [dim]({dest_file.stat().st_size:,} bytes | SHA-256 match)[/dim]"
                )
            else:
                console.print(
                    f"  [yellow][MISMATCH][/yellow] {filename} hash does not match DB record!"
                )
        else:
            console.print(f"  [green][OK][/green] Downloaded {filename} -> {dest_file}")

    console.print(
        Panel.fit(
            f"[bold green]Asset Pull & Verification Complete![/bold green]\n\n"
            f"- Downloaded: [bold cyan]{pulled}/{len(all_assets)}[/bold cyan]\n"
            f"- Integrity Verified: [bold green]{verified}[/bold green]\n"
            f"- Failures: [bold red]{failed}[/bold red]",
            title="[bold green]MinIO/DB Pull Summary[/bold green]",
            border_style="green",
        )
    )


@db_app.command("sync")
def db_sync():
    """Execute bi-directional synchronization between local store and cloud (Neon + Cloudflare R2)."""
    store = get_data_store()
    sync_engine = SyncEngine(local_store=store)

    console.print("[cyan]Running bi-directional sync with cloud...[/cyan]")
    report = sync_engine.sync()

    if report.success:
        console.print(
            Panel.fit(
                f"[bold green]Sync Completed Successfully![/bold green]\n\n"
                f"- Pushed Books: [bold yellow]{report.pushed_books}[/bold yellow]\n"
                f"- Pushed Pages: [bold yellow]{report.pushed_pages}[/bold yellow]\n"
                f"- Pushed Prompts: [bold yellow]{report.pushed_prompts}[/bold yellow]\n"
                f"- Pushed Media Assets: [bold yellow]{report.pushed_assets}[/bold yellow]\n"
                f"- Pulled Remote Pages: [bold yellow]{report.pulled_pages}[/bold yellow]\n"
                f"- Conflicts Resolved: [bold yellow]{report.conflicts_resolved}[/bold yellow]",
                title="[bold green]Cloud Sync Report[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                "[bold red]Sync encountered errors:[/bold red]\n" + "\n".join(report.errors),
                title="[bold red]Sync Error[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)


@db_app.command("export-to-fs")
def db_export_to_fs(
    output_path: Path = typer.Option(DEFAULT_PIPELINE_STATE_FILE, "--output", "-o"),
):
    """Export database state to pipeline_state.json format."""
    store = get_data_store()
    pages = store.get_all_pages()

    pages_dict: dict[str, Any] = {}
    summary: dict[str, int] = {}
    for p in pages:
        summary[p.status] = summary.get(p.status, 0) + 1
        pages_dict[p.page_id] = {
            "page_id": p.page_id,
            "page_number": p.page_number,
            "canonical_object": p.canonical_object,
            "display_label": p.display_label,
            "section": p.section,
            "status": p.status,
            "attempts": p.attempts,
            "max_attempts": p.max_attempts,
            "positive_prompt": p.positive_prompt,
            "negative_prompt": p.negative_prompt,
            "raw_image_path": p.raw_image_path,
            "rescued_image_path": p.rescued_image_path,
            "composite_image_path": p.composite_image_path,
            "qa_score": p.qa_score,
            "qa_passed": p.qa_passed,
            "violations": p.violations,
            "last_updated": p.last_updated,
        }

    export_data = {
        "total_pages": len(pages_dict),
        "summary": summary,
        "pages": pages_dict,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)

    console.print(
        f"[bold green]Exported {len(pages_dict)} pages from DB to {output_path}![/bold green]"
    )
