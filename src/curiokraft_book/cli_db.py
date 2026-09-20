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

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from curiokraft_book.constants import (
    DEFAULT_BOOK_CONFIG,
    DEFAULT_PAGES_MANIFEST,
    DEFAULT_PIPELINE_STATE_FILE,
)
from curiokraft_book.data.base import BookRecord, PageRecord
from curiokraft_book.data.hybrid_store import get_data_store
from curiokraft_book.data.sync_engine import SyncEngine

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


@db_app.command("status")
def db_status():
    """Display database connection status and entity counts."""
    store = get_data_store()
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
):
    """Ingest existing filesystem manifests and pipeline_state.json into database."""
    store = get_data_store()
    console.print(f"[cyan]Migrating book configuration from {config_path}...[/cyan]")

    book_title = "Tiny Hands Color & Learn"
    volume = "vol1"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        b_cfg = cfg.get("book", {})
        book_title = b_cfg.get("title", book_title)
        volume = str(b_cfg.get("volume", volume)).lower()

    slug = f"curiokraft-{volume}"
    book = store.books.get_by_slug(slug)
    if not book:
        book = store.books.save(BookRecord(slug=slug, title=book_title, volume=volume))

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

    # Ingest pipeline_state.json if present
    if state_path.exists():
        with open(state_path, encoding="utf-8") as f:
            s_data = json.load(f)
        for p_id, rec in s_data.get("pages", {}).items():
            clean_kwargs = {k: v for k, v in rec.items() if k != "page_id"}
            store.update_page(p_id, **clean_kwargs)

    console.print(
        Panel.fit(
            f"[bold green]Successfully migrated {migrated_pages} pages into database for '{book.title}'![/bold green]",
            title="[bold green]Migration Complete[/bold green]",
            border_style="green",
        )
    )


@db_app.command("sync-assets")
def db_sync_assets(
    directory: Path = typer.Option(Path("output/interior_masters"), "--dir", "-d", help="Directory to scan"),
    asset_type: str = typer.Option("composite_master", "--type", "-t"),
):
    """Scan directory of images, compute SHA-256 hashes, and index into media_assets."""
    store = get_data_store()
    if not directory.exists():
        console.print(f"[yellow]Directory {directory} does not exist.[/yellow]")
        return

    valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
    files = [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]

    console.print(f"[cyan]Indexing {len(files)} files from {directory}...[/cyan]")
    indexed = 0
    for f in files:
        # Determine page_id from name if possible (e.g. page_001.png -> P001)
        import re

        m = re.search(r"(\d+)", f.stem)
        page_id = f"P{int(m.group(1)):03d}" if m else None

        try:
            store.register_media_asset(f, asset_type=asset_type, page_id=page_id)
            indexed += 1
        except Exception as e:
            console.print(f"[red]Failed indexing {f.name}:[/] {e}")

    console.print(f"[bold green]Indexed {indexed} media assets with SHA-256 content hashes.[/bold green]")


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


@db_app.command("export-to-fs")
def db_export_to_fs(
    output_path: Path = typer.Option(DEFAULT_PIPELINE_STATE_FILE, "--output", "-o"),
):
    """Export database state to pipeline_state.json format."""
    store = get_data_store()
    pages = store.get_all_pages()

    pages_dict = {}
    summary = {}
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

    console.print(f"[bold green]Exported {len(pages_dict)} pages from DB to {output_path}![/bold green]")
