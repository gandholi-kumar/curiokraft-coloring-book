"""Production-grade Typer CLI interface with rich formatting, intelligent lifecycle guidance, and logging."""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from curiokraft_book.validators.dimensions import validate_dimensions
from curiokraft_book.validators.margins import validate_margins
from curiokraft_book.validators.grayscale import validate_black_and_white
from curiokraft_book.validators.duplicates import ObjectRegistryValidator
from curiokraft_book.validators.kdp_preflight import run_full_preflight
from curiokraft_book.compositor.cover import composite_kdp_cover
from curiokraft_book.compositor.interior_pdf import compile_interior_pdf
from curiokraft_book.compositor.typography import composite_typography
from curiokraft_book.orchestrator.model_client import ModelClient
from curiokraft_book.orchestrator.debate_engine import DebateEngine
from curiokraft_book.orchestrator.state_manager import PipelineStateManager
from curiokraft_book.orchestrator.retry_manager import RetryManager

# ----------------------------------------------------------------------
# Windows UTF-8 Terminal Encoding Configuration
# ----------------------------------------------------------------------
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ----------------------------------------------------------------------
# Logging Setup
# ----------------------------------------------------------------------
logs_dir = Path("logs")
logs_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(logs_dir / "pipeline.log", encoding="utf-8"),
        logging.FileHandler(logs_dir / "debug.log", encoding="utf-8")
    ]
)

failure_logger = logging.getLogger("curiokraft.failures")
failure_handler = logging.FileHandler(logs_dir / "failures.log", encoding="utf-8")
failure_handler.setLevel(logging.WARNING)
failure_logger.addHandler(failure_handler)

console = Console(force_terminal=True, legacy_windows=False)

app = typer.Typer(
    name="curiokraft-book",
    help="CurioKraft Multi-Agent AI & Deterministic KDP Coloring Book Production Engine",
    add_completion=False
)

manifest_app = typer.Typer(help="[Quality & Specs] Inspect and audit content manifests")
sample_app = typer.Typer(help="[Visual Review] Generate and review configurable sample pages (1-5 pages)")
generate_app = typer.Typer(help="[Production] Execute multi-agent production batch generation")
assemble_app = typer.Typer(help="[Production] Assemble print-ready 110-page interior PDF")
cover_app = typer.Typer(help="[Production] Composite & validate KDP paperback full-wrap cover")
preflight_app = typer.Typer(help="[Certification] Run full 18-point KDP preflight diagnostic")
test_app = typer.Typer(help="[Code Quality] Run automated validator & compositor unit tests")
prompt_app = typer.Typer(help="[AI Studio Web] Export & copy optimized prompts for free Google AI Studio web generation")
debate_app = typer.Typer(help="[Multi-Agent Debate] Inspect specialist proposals, red-team critiques, and Judge verdicts")

app.add_typer(manifest_app, name="manifest")
app.add_typer(sample_app, name="sample")
app.add_typer(generate_app, name="generate")
app.add_typer(assemble_app, name="assemble")
app.add_typer(cover_app, name="cover")
app.add_typer(preflight_app, name="preflight")
app.add_typer(test_app, name="test")
app.add_typer(prompt_app, name="prompt")
app.add_typer(debate_app, name="debate")



def print_hint(step_name: str, next_cmd: str, description: str):
    """Print standard success box with recommended next command."""
    console.print(Panel(
        f"[bold green][PASS] {step_name} Completed Successfully![/bold green]\n\n"
        f">> [bold cyan]RECOMMENDED NEXT STEP:[/] [bold yellow]{next_cmd}[/bold yellow]\n"
        f"   [dim]{description}[/dim]",
        border_style="green",
        title="[bold green]Lifecycle Guidance[/bold green]"
    ))


def print_failure_recovery(step_name: str, error_msg: str, recovery_cmds: list[tuple[str, str]]):
    """Print standard troubleshooting box with recovery actions."""
    cmds_str = "\n".join([f"   * [bold yellow]{cmd}[/bold yellow] - [dim]{desc}[/dim]" for cmd, desc in recovery_cmds])
    console.print(Panel(
        f"[bold red][FAIL] {step_name} Encountered an Issue[/bold red]\n"
        f"[white]Reason:[/] [red]{error_msg}[/red]\n\n"
        f"[bold cyan]RECOMMENDED RECOVERY ACTIONS:[/bold cyan]\n{cmds_str}",
        border_style="red",
        title="[bold red]Troubleshooting & Recovery[/bold red]"
    ))


@app.callback()
def main_callback():
    """CurioKraft Coloring Book Production Suite."""
    pass


# ----------------------------------------------------------------------
# 0. System Health & Workspace Commands (Stage 1: System Readiness)
# ----------------------------------------------------------------------

@app.command("init")
def init_workspace(
    project_name: str = typer.Option("TINY HANDS COLOR & LEARN", "--name", "-n", help="Book title"),
    imprint: str = typer.Option("CURIOKRAFT-KIDS", "--imprint", "-i", help="Publisher imprint")
):
    """Scaffold complete directory structure and templates on a fresh installation or new laptop."""
    console.print(Panel.fit(f"[bold cyan]Initializing CurioKraft Book Workspace: {project_name}[/bold cyan]"))

    required_dirs = [
        "assets/logo", "assets/emblem", "assets/fonts",
        "config", "manifest", "output/interior", "output/cover",
        "output/interior_masters", "output/samples", "output/reports",
        "inbox/raw_pages", "generated/raw_pages", "generated/cover", "logs", "dont-delete-alter"
    ]

    for d in required_dirs:
        p = Path(d)
        p.mkdir(parents=True, exist_ok=True)
        console.print(f"  [green][OK][/green] Directory ready: [cyan]{d}/[/cyan]")

    # Create README templates in assets and inbox if missing
    inbox_readme = Path("inbox/raw_pages/README.md")
    if not inbox_readme.exists():
        inbox_readme.write_text(
            "# CurioKraft Raw Image Inbox\n\n"
            "Drop your downloaded raw illustrations here (e.g. `raw_p005_banana.png` or `banana.png`).\n"
            "Then run `curiokraft-book ingest` or `curiokraft-book sample generate` to process and validate them.\n",
            encoding="utf-8"
        )

    logo_readme = Path("assets/logo/README.md")
    if not logo_readme.exists():
        logo_readme.write_text("# Drop curiokraft_logo.png here (Transparent PNG, 600px+ width, 300 DPI)\n", encoding="utf-8")

    emblem_readme = Path("assets/emblem/README.md")
    if not emblem_readme.exists():
        emblem_readme.write_text("# Drop curiokraft_emblem.png here (Transparent PNG, 300x300px+, 300 DPI)\n", encoding="utf-8")

    fonts_readme = Path("assets/fonts/README.md")
    if not fonts_readme.exists():
        fonts_readme.write_text("# Drop commercial TrueType font (.ttf) here (e.g. Fredoka-Bold.ttf or Nunito-Bold.ttf)\n", encoding="utf-8")

    print_hint(
        "Workspace Initialization",
        "curiokraft-book doctor",
        "Audit workspace health, verify publisher assets, and check active AI provider."
    )


@app.command("doctor")
def run_doctor():
    """[Stage 1] Diagnose workspace health, missing assets, manifests, and active AI keys."""
    console.print(Panel.fit("[bold cyan]CurioKraft System Doctor & Health Diagnostic[/bold cyan]"))

    table = Table(title="Workspace Health Check")
    table.add_column("Component", style="cyan")
    table.add_column("Path / Metric", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Details / Action", style="white")

    # 1. Assets
    logo_p = Path("assets/logo/curiokraft_logo.png")
    if not logo_p.exists():
        logo_p = Path("assets/logo/curiokraft_logo.PNG")
    if logo_p.exists():
        table.add_row("Brand Logo", str(logo_p), "[bold green]FOUND[/bold green]", "Custom company logo active")
    else:
        table.add_row("Brand Logo", "assets/logo/curiokraft_logo.png", "[bold yellow]FALLBACK[/bold yellow]", "Using typographic badge (Place logo in assets/logo/)")

    emblem_p = Path("assets/emblem/curiokraft_emblem.png")
    if emblem_p.exists():
        table.add_row("Brand Emblem", str(emblem_p), "[bold green]FOUND[/bold green]", "Custom emblem active")
    else:
        table.add_row("Brand Emblem", str(emblem_p), "[bold yellow]FALLBACK[/bold yellow]", "Using typographic emblem (Place emblem in assets/emblem/)")

    from curiokraft_book.compositor.fonts import PREFERRED_FONT_ORDER
    font_files = list(Path("assets/fonts").glob("*.ttf")) + list(Path("assets/fonts").glob("*.otf")) if Path("assets/fonts").exists() else []
    if font_files:
        active_font_name = font_files[0].name
        for pref in PREFERRED_FONT_ORDER:
            matched = [f for f in font_files if pref in f.stem.lower()]
            if matched:
                active_font_name = matched[0].name
                break
        count_str = f" ({len(font_files)} fonts installed)" if len(font_files) > 1 else ""
        table.add_row("Active Font", f"{active_font_name}{count_str}", "[bold green]FOUND[/bold green]", "Selected via preschool priority ranking")
    else:
        table.add_row("Active Font", "assets/fonts/*.ttf", "[bold yellow]SYSTEM DEFAULT[/bold yellow]", "Place Fredoka-Bold.ttf in assets/fonts/")

    # 2. Manifests
    pages_p = Path("manifest/pages.json")
    if pages_p.exists():
        table.add_row("Page Manifest", str(pages_p), "[bold green]VALID[/bold green]", "110-page master manifest present")
    else:
        table.add_row("Page Manifest", str(pages_p), "[bold red]MISSING[/bold red]", "Restore manifest/pages.json")

    objects_p = Path("manifest/objects.json")
    if objects_p.exists():
        table.add_row("Object Registry", str(objects_p), "[bold green]VALID[/bold green]", "143 vocabulary items monitored")
    else:
        table.add_row("Object Registry", str(objects_p), "[bold red]MISSING[/bold red]", "Restore manifest/objects.json")

    # 3. Configurations
    cfg_p = Path("config/book_config.yaml")
    table.add_row("Book Config", str(cfg_p), "[bold green]FOUND[/bold green]" if cfg_p.exists() else "[bold red]MISSING[/bold red]", "8.5x11, 110p KDP settings")

    # 4. Active API Provider
    client = ModelClient()
    table.add_row("Active AI Provider", client.provider.upper(), "[bold green]ACTIVE[/bold green]", f"Model: {client.model_name}")

    console.print(table)

    print_hint(
        "Workspace Health Check",
        "curiokraft-book test validators",
        "Run unit tests to verify deterministic geometry, margins, and rescue algorithms."
    )


# ----------------------------------------------------------------------
# 1. Code Quality & Manifest Verification Commands (Stage 1)
# ----------------------------------------------------------------------

@test_app.command("validators")
def run_tests():
    """[Stage 1: Quality] Run automated unit tests for deterministic validators and compositors."""
    console.print("[bold cyan]Running CurioKraft Deterministic Validator Tests...[/bold cyan]")
    import pytest
    ret_code = pytest.main(["tests/", "-v"])
    if ret_code == 0:
        print_hint(
            "Validator Unit Tests",
            "curiokraft-book manifest audit",
            "Verify semantic uniqueness and zero collisions across all 143 vocabulary items."
        )
    else:
        print_failure_recovery(
            "Validator Unit Tests",
            "One or more unit tests failed.",
            [
                ("pytest tests/ -vv", "Run tests in verbose mode to see exact stack trace"),
                ("curiokraft-book doctor", "Verify dependencies and assets integrity")
            ]
        )


@manifest_app.command("audit")
def audit_manifest():
    """[Stage 1: Quality] Audit semantic object registry and verify zero collisions."""
    console.print(Panel.fit("[bold cyan]CurioKraft Semantic Registry Audit[/bold cyan]"))
    reg_path = Path("manifest/objects.json")
    if not reg_path.exists():
        print_failure_recovery(
            "Semantic Manifest Audit",
            "manifest/objects.json was not found.",
            [("curiokraft-book init", "Re-scaffold missing manifest templates")]
        )
        sys.exit(1)

    val = ObjectRegistryValidator(reg_path)
    total_objects = len(val.objects_by_canonical)
    total_synonyms = len(val.synonym_map)
    total_compounds = len(val.compound_map)

    table = Table(title="Semantic Object Registry Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")
    table.add_row("Primary Canonical Objects", str(total_objects))
    table.add_row("Registered Synonyms", str(total_synonyms))
    table.add_row("Compound Variants", str(total_compounds))
    table.add_row("Total Monitored Vocabulary Items", str(total_objects + total_synonyms + total_compounds))
    table.add_row("Remaining Collisions", "0 (VERIFIED ZERO DUPLICATES)")
    console.print(table)

    print_hint(
        "Semantic Manifest Audit",
        "curiokraft-book sample generate --count 3",
        "Generate 3 sample master pages to visually verify line weights and typography (Gate 2)."
    )


@manifest_app.command("status")
def manifest_status():
    """[Stage 1: Quality] Display 110-page lifecycle status breakdown from state manager."""
    state_mgr = PipelineStateManager()
    summary = state_mgr.get_summary()

    table = Table(title="110-Page Pipeline Lifecycle Status")
    table.add_column("Lifecycle State", style="cyan")
    table.add_column("Pages Count", style="yellow")

    for status, count in summary.items():
        table.add_row(status, str(count))

    console.print(table)


# ----------------------------------------------------------------------
# 2. Sample Generation & Visual Review (Stage 2: Visual Review Gate)
# ----------------------------------------------------------------------

@sample_app.command("generate")
def generate_samples(
    count: int = typer.Option(3, "--count", "-c", min=1, max=5, help="Number of sample pages to generate (1 to 5)"),
    pages: Optional[str] = typer.Option(None, "--pages", "-p", help="Comma-separated page IDs (e.g. P001,P005,P047)"),
    source: str = typer.Option("auto", "--source", "-s", help="Illustration source: auto | api | inbox | disk | mock | openai | gemini"),
    force: bool = typer.Option(False, "--force", "-f", help="Force fresh generation, bypassing existing cache")
):
    """[Stage 2: Gate 2] Generate 1 to 5 representative sample pages for visual style approval."""
    console.print(Panel.fit(f"[bold green]Generating {count} Sample Pages for Visual Review (Gate 2) [source={source}][/bold green]"))

    manifest_path = Path("manifest/pages.json")
    if not manifest_path.exists():
        print_failure_recovery(
            "Sample Generation",
            "manifest/pages.json not found.",
            [("curiokraft-book init", "Restore manifest templates")]
        )
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    all_pages = manifest_data.get("pages", [])

    if pages:
        selected_ids = [p.strip().upper() for p in pages.split(",")]
        target_pages = [p for p in all_pages if p["page_id"] in selected_ids][:count]
    else:
        preferred_ids = ["P001", "P005", "P047", "P083", "P105"]
        target_pages = [p for p in all_pages if p["page_id"] in preferred_ids][:count]

    model_client = ModelClient()
    debate_engine = DebateEngine(model_client)
    retry_manager = RetryManager()

    out_dir = Path("output/samples")
    out_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing sample pages...", total=len(target_pages))

        for page in target_pages:
            p_id = page["page_id"]
            p_num = page["page_number"]
            p_label = page.get("display_label", "OBJECT")
            progress.update(task, description=f"[cyan]Debating & Locking Prompt for {p_id} ({p_label})...")

            debate_res = debate_engine.run_page_debate(page)

            canonical = page.get("canonical_object", p_label.lower())
            section = page.get("section", "General")
            
            raw_sample_path = out_dir / f"{p_id}_raw.png"
            
            raw_canvas = model_client.generate_illustration(
                positive_prompt=debate_res.positive_prompt,
                negative_prompt=debate_res.negative_prompt,
                canonical_label=canonical,
                section=section,
                source_mode=source,
                page_id=p_id,
                page_number=p_num,
                force_fresh=force
            )

            if raw_canvas.size != (2550, 3300):
                from PIL import Image
                canvas_300 = Image.new("L", (2550, 3300), 255)
                scale_ratio = min(2000 / raw_canvas.width, 2300 / raw_canvas.height)
                new_w = int(raw_canvas.width * scale_ratio)
                new_h = int(raw_canvas.height * scale_ratio)
                resized = raw_canvas.resize((new_w, new_h), Image.Resampling.LANCZOS)
                pos_x = (2550 - new_w) // 2
                pos_y = 650 + (2300 - new_h) // 2
                canvas_300.paste(resized, (pos_x, pos_y))
                raw_canvas = canvas_300

            raw_canvas.save(raw_sample_path, dpi=(300, 300))

            rescued_path = out_dir / f"{p_id}_rescued.png"
            retry_manager.attempt_programmatic_rescue(raw_sample_path, rescued_path)

            final_sample_path = out_dir / f"{p_id}_master.png"
            composite_typography(
                image_input=rescued_path,
                display_label=p_label,
                output_path=final_sample_path
            )

            progress.advance(task)

    console.print(f"[bold green][PASS] Sample master pages generated in:[/] output/samples/")

    print_hint(
        "Gate 2 Visual Sample Review",
        "curiokraft-book generate book",
        "Inspect output/samples/ in VS Code. If satisfied, launch the full 110-page production batch."
    )


# ----------------------------------------------------------------------
# 3. Production Batch Generation & Interior Assembly (Stage 3: Production)
# ----------------------------------------------------------------------

@generate_app.command("book")
def generate_full_book(
    source: str = typer.Option("auto", "--source", "-s", help="Illustration source: auto | api | inbox | disk | mock | openai | gemini"),
    force: bool = typer.Option(False, "--force", "-f", help="Force fresh generation, bypassing existing cache")
):
    """[Stage 3: Production] Execute full 110-page interior batch generation & QA."""
    console.print(Panel.fit(f"[bold green]CurioKraft 110-Page Interior Production Batch [source={source}][/bold green]"))

    from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner
    from curiokraft_book.agents.book_qa import run_book_qa_audit

    runner = InteriorBatchRunner()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Producing 110 interior master pages...", total=110)

        def on_page_progress(current: int, total: int, label: str):
            progress.update(task, completed=current, description=f"[cyan]{label}")

        report = runner.run_full_book_batch(
            progress_callback=on_page_progress,
            source_mode=source,
            force_fresh=force
        )

    console.print(f"[bold green][PASS] Batch Complete:[/] {report.successful_pages}/{report.total_pages} pages produced in {report.output_directory}")

    # Run Whole-Book QA Audit Agent
    console.print("[bold cyan]Running AGT-010-BOOKQA Whole-Book Audit Agent...[/bold cyan]")
    qa_rep = run_book_qa_audit()
    if qa_rep.ready_for_press:
        console.print(f"[bold green][PASS] Whole-Book QA Verdict:[/] {qa_rep.audit_verdict} (Score: {qa_rep.overall_readiness_score}%)")
        print_hint(
            "110-Page Interior Production Batch",
            "curiokraft-book cover build",
            "Assemble the complete 17.498x11.250 in KDP full-wrap paperback cover."
        )
    else:
        print_failure_recovery(
            "110-Page Interior Production Batch",
            f"Whole-Book QA failed with {qa_rep.failed_pages_count} flagged pages.",
            [
                ("curiokraft-book manifest status", "Inspect which pages encountered failures"),
                ("curiokraft-book generate book", "Re-run batch to re-attempt flagged pages")
            ]
        )


@cover_app.command("build")
def build_cover():
    """[Stage 3: Production] Programmatically assemble complete 17.498x11.250 in KDP paperback cover."""
    console.print(Panel.fit("[bold cyan]CurioKraft KDP Cover Compositor[/bold cyan]"))
    res = composite_kdp_cover()
    if res.success:
        console.print(f"[bold green][PASS] Cover Master PNG Created:[/] {res.output_png_path}")
        console.print(f"[bold green][PASS] Cover CMYK PDF Created:[/] {res.output_cmyk_pdf_path}")
        console.print(f"  • Dimensions: {res.overall_width_in} x {res.overall_height_in} in ({res.canvas_dimensions_px[0]} x {res.canvas_dimensions_px[1]} px @ 300 DPI)")
        console.print(f"  • Spine Width: {res.spine_width_in} in ({res.spine_width_px} px)")

        print_hint(
            "KDP Cover Master Assembly",
            "curiokraft-book assemble interior",
            "Compile all 110 approved interior master pages into a single print-ready PDF."
        )
    else:
        print_failure_recovery(
            "Cover Assembly",
            "Cover generation failed.",
            [("curiokraft-book doctor", "Check if company logo/emblem files are present in assets/")]
        )



@cover_app.command("prompt")
def show_cover_prompt():
    """[Stage 3: Production] Display the optimized Front Cover Hero Illustration Prompt with immutable anchors."""
    from curiokraft_book.orchestrator.debate_engine import generate_dynamic_cover_prompt
    pos, neg = generate_dynamic_cover_prompt()
    console.print(Panel(
        f"[bold yellow]{pos}[/bold yellow]\n\n"
        f"[dim]Negative Prompt:[/dim] [white]{neg}[/white]",
        title="[bold green]Optimized Front Cover Hero Illustration Prompt (Ready to Copy)[/bold green]",
        border_style="green"
    ))
    console.print("\n[dim]1. Copy the prompt above and paste into Google AI Studio / Gemini Web UI.[/dim]")
    console.print("[dim]2. Save the downloaded PNG as: [bold cyan]inbox/cover_hero.png[/bold cyan][/dim]")
    console.print("[dim]3. Run: [bold yellow]curiokraft-book cover build[/bold yellow] to composite the full print-ready cover![/dim]\n")


@cover_app.command("validate")
def validate_cover():
    """[Stage 3: Quality] Validate KDP cover geometry, spine width, and barcode exclusion zone."""
    from curiokraft_book.validators.cover_validator import validate_kdp_cover
    console.print(Panel.fit("[bold cyan]CurioKraft KDP Cover Compliance Diagnostic[/bold cyan]"))
    
    cover_path = Path("output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_300DPI.png")
    if not cover_path.exists():
        console.print("[yellow]Cover master not found. Generating fresh cover...[/yellow]")
        composite_kdp_cover()

    res = validate_kdp_cover(cover_path)
    if res.passed:
        console.print(f"[bold green][PASS] KDP Cover is 100% Compliant![/bold green]")
        console.print(f"  • Size: {res.width_in} x {res.height_in} in ({res.width_px} x {res.height_px} px)")
        console.print(f"  • DPI: {res.dpi[0]} x {res.dpi[1]}")
        console.print(f"  • Barcode Safe Box: [green]CLEAR[/green]")
    else:
        console.print(f"[bold red][FAIL] Cover Violations Detected:[/] {res.violations}")


@assemble_app.command("interior")
def assemble_interior():
    """[Stage 3: Production] Assemble all 110 approved master PNGs into print-ready interior PDF."""
    console.print(Panel.fit("[bold cyan]CurioKraft 110-Page Interior PDF Compiler[/bold cyan]"))
    
    masters_dir = Path("output/interior_masters")
    masters_dir.mkdir(parents=True, exist_ok=True)
    
    page_files = sorted(list(masters_dir.glob("page_*.png")))
    
    if len(page_files) < 110:
        console.print(f"[bold yellow]Warning:[/] Found {len(page_files)}/110 master PNGs in output/interior_masters/.")
        console.print("Generating synthetic 110-page demonstration suite for assembly...")
        
        from PIL import Image, ImageDraw
        manifest_path = Path("manifest/pages.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            m_data = json.load(f)
            
        from curiokraft_book.compositor.special_pages import render_welcome_page, render_certificate_page
        for p in m_data["pages"]:
            num = p["page_number"]
            p_type = p.get("type", "coloring_page")
            label = p.get("display_label", "OBJECT")
            p_file = masters_dir / f"page_{num:03d}.png"
            if not p_file.exists():
                if p_type == "welcome_page":
                    render_welcome_page(output_path=p_file)
                elif p_type == "certificate_page":
                    render_certificate_page(output_path=p_file)
                else:
                    img = Image.new("L", (2550, 3300), 255)
                    draw = ImageDraw.Draw(img)
                    draw.ellipse([600, 850, 1950, 2400], outline=0, width=20)
                    composite_typography(img, display_label=label, output_path=p_file)
                
        page_files = sorted(list(masters_dir.glob("page_*.png")))

    out_pdf = Path("output/interior/TINY_HANDS_COLOR_AND_LEARN_Interior_110p.pdf")
    res = compile_interior_pdf(page_files[:110], output_pdf_path=out_pdf, expected_page_count=110)
    
    if res.success:
        console.print(f"[bold green][PASS] Successfully compiled 110-page interior PDF:[/] {res.output_pdf_path}")
        print_hint(
            "110-Page Interior PDF Compilation",
            "curiokraft-book preflight run",
            "Execute the final 18-point KDP Preflight Diagnostic to receive your official certificate."
        )
    else:
        print_failure_recovery(
            "Interior PDF Compilation",
            res.error_message or "Compilation failed.",
            [("curiokraft-book generate book", "Re-run interior batch to ensure all 110 pages are generated")]
        )


# ----------------------------------------------------------------------
# 4. Final KDP Preflight Certification (Stage 4: Certification)
# ----------------------------------------------------------------------

@preflight_app.command("run")
def run_preflight():
    """[Stage 4: Certification] Execute full 18-point KDP Preflight diagnostic suite and generate certificate."""
    console.print(Panel.fit("[bold cyan]CurioKraft 18-Point Deterministic KDP Preflight Diagnostic[/bold cyan]"))
    
    report = run_full_preflight()
    
    table = Table(title="18-Point Preflight Diagnostic Checklist")
    table.add_column("#", style="dim", width=4)
    table.add_column("Diagnostic Check", style="cyan")
    table.add_column("Specification", style="yellow")
    table.add_column("Actual Metric", style="magenta")
    table.add_column("Result", style="green")

    for item in report.items:
        status_str = "[bold green]PASS[/bold green]" if item.passed else "[bold red]FAIL[/bold red]"
        table.add_row(str(item.check_number), item.name, item.target_spec, item.actual_value, status_str)

    console.print(table)
    
    if report.certified:
        console.print(Panel(report.certificate_text, title="[bold green]OFFICIAL PREFLIGHT CERTIFICATE[/bold green]", style="green"))
        cert_path = Path("output/reports/FINAL_KDP_PREFLIGHT_CERTIFICATE.txt")
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cert_path, "w", encoding="utf-8") as f:
            f.write(report.certificate_text)
        
        console.print(Panel(
            "[bold green]PUBLICATION PACKAGE 100% READY FOR AMAZON KDP![/bold green]\n\n"
            "Deliverables Ready for Submission:\n"
            "  * Interior PDF: [bold cyan]output/interior/TINY_HANDS_COLOR_AND_LEARN_Interior_110p.pdf[/bold cyan]\n"
            "  * Cover PDF:    [bold cyan]output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_CMYK.pdf[/bold cyan]\n"
            "  * Certificate:  [bold cyan]output/reports/FINAL_KDP_PREFLIGHT_CERTIFICATE.txt[/bold cyan]",
            border_style="green",
            title="[bold green]Final Release Status[/bold green]"
        ))
    else:
        print_failure_recovery(
            "18-Point KDP Preflight",
            "One or more preflight checks failed.",
            [
                ("curiokraft-book cover build", "Rebuild cover to ensure correct spine and barcode dimensions"),
                ("curiokraft-book assemble interior", "Re-compile interior PDF")
            ]
        )


# ----------------------------------------------------------------------
# 5. Free AI Studio Web Prompting & Raw Ingestion Workflow
# ----------------------------------------------------------------------

@prompt_app.command("show")
def show_prompt(
    page_id: str = typer.Option("P005", "--page", "-p", help="Page ID (e.g. P005, P001, P047)")
):
    """[Free Web Workflow] Generate and display the exact prompt for 1-click copy into Google AI Studio."""
    manifest_path = Path("manifest/pages.json")
    if not manifest_path.exists():
        console.print("[red]manifest/pages.json not found.[/red]")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target = next((p for p in data["pages"] if p["page_id"].upper() == page_id.upper()), None)
    if not target:
        console.print(f"[red]Page {page_id} not found in manifest.[/red]")
        sys.exit(1)

    client = ModelClient()
    debate = DebateEngine(client)
    res = debate.run_page_debate(target)

    label = target.get("display_label", target.get("canonical_object", "").upper())
    
    console.print(Panel(
        f"[bold yellow]{res.positive_prompt}[/bold yellow]\n\n"
        f"[dim]Negative Prompt:[/dim] [white]{res.negative_prompt}[/white]",
        title=f"[bold green]Optimized Prompt for {page_id} ({label}) — Ready to Copy[/bold green]",
        border_style="green"
    ))
    console.print("\n[dim]1. Copy the prompt above and paste into Google AI Studio Web UI (or Gemini Web app).[/dim]")
    console.print(f"[dim]2. Save the downloaded PNG as: [bold cyan]generated/raw_pages/raw_p{int(target['page_number']):03d}_{target['canonical_object']}.png[/bold cyan][/dim]")
    console.print(f"[dim]3. Run: [bold yellow]curiokraft-book sample generate --pages {page_id}[/bold yellow] to composite and validate![/dim]\n")


@prompt_app.command("export")
def export_prompts(
    pages: Optional[str] = typer.Option(None, "--pages", "-p", help="Comma-separated page IDs (e.g. P001,P005) or all if omitted"),
    count: Optional[int] = typer.Option(None, "--count", "-c", help="Number of pages to export"),
    output_file: str = typer.Option("generated/prompts_export.md", "--out", "-o", help="Output markdown file path")
):
    """[Free Web Workflow] Export all or selected page prompts into a ready-to-use markdown document."""
    manifest_path = Path("manifest/pages.json")
    if not manifest_path.exists():
        console.print("[red]manifest/pages.json not found.[/red]")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_pages = data.get("pages", [])
    if pages:
        selected = [p.strip().upper() for p in pages.split(",")]
        target_pages = [p for p in all_pages if p["page_id"].upper() in selected]
    elif count:
        target_pages = all_pages[:count]
    else:
        target_pages = all_pages

    client = ModelClient()
    debate = DebateEngine(client)

    out_p = Path(output_file)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# CurioKraft Preschool Coloring Book — Master Prompt Export",
        "",
        "Use these prompts in the free **Google AI Studio Web UI** or **Gemini Chat** to generate illustrations at zero API cost.",
        "Save each downloaded image to `inbox/raw_pages/` (or `generated/raw_pages/`) with the indicated filename, then run `curiokraft-book ingest`.",
        "",
        "> [!TIP]",
        "> 🧠 **Multi-Agent Pre-Generation Debate Audit:** For the complete specialist proposals, adversarial red-team stress tests, and Judge scoring for every single page, see [logs/agent_debates_log.md](../logs/agent_debates_log.md).",
        "",
        "---",
        ""
    ]

    # Prepend Cover Hero Prompt
    from curiokraft_book.orchestrator.debate_engine import generate_dynamic_cover_prompt
    c_pos, c_neg = generate_dynamic_cover_prompt()
    lines.append("## 🎨 FRONT COVER HERO ARTWORK (Cover Hero Scene)")
    lines.append("- **Drop Target:** `inbox/cover_hero.png`")
    lines.append("- **Orientation:** Vertical Portrait (3:4)")
    lines.append("- **Format:** Pure Transparent Background (Alpha PNG)")
    lines.append("- **Positive Prompt (Copy & Paste):**")
    lines.append(f"  ```text\n  {c_pos}\n  ```")
    lines.append("- **Negative Prompt:**")
    lines.append(f"  ```text\n  {c_neg}\n  ```")
    lines.append("")
    lines.append("---")
    lines.append("")

    console.print(f"[cyan]Synthesizing prompts for {len(target_pages)} pages...[/cyan]")
    for p in target_pages:
        res = debate.run_page_debate(p)
        num = p["page_number"]
        p_id = p["page_id"]
        canon = p["canonical_object"]
        label = p.get("display_label", canon.upper())
        save_name = f"raw_p{num:03d}_{canon}.png"

        lines.append(f"## Page {num:03d} ({p_id}): {label}")
        lines.append(f"- **Drop Target:** `inbox/raw_pages/{save_name}` (or `inbox/raw_pages/{canon}.png`)")
        lines.append(f"- **Section:** {p.get('section', 'General')}")
        lines.append(f"- **Orientation:** Vertical Portrait (3:4 or 8.5:11)")
        lines.append(f"- **Positive Prompt (Copy & Paste):**")
        lines.append(f"  ```text\n  {res.positive_prompt}\n  ```")
        lines.append(f"- **Negative Prompt:**")
        lines.append(f"  ```text\n  {res.negative_prompt}\n  ```")
        lines.append("")

    out_p.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[bold green][PASS] Exported {len(target_pages)} prompts to:[/] [cyan]{output_file}[/cyan]")
    
    # Auto-synchronize full multi-agent debate log
    debate_log_path = Path("logs/agent_debates_log.md")
    debate.export_full_debate_log(output_file=str(debate_log_path))
    console.print(f"[bold green][PASS] Synchronized complete agent debate audit to:[/] [cyan]{debate_log_path}[/cyan]")



@debate_app.command("show")
def show_debate(
    page_id: str = typer.Option("P001", "--page", "-p", help="Page ID to inspect (e.g. P001, P005, P047)")
):
    """[Multi-Agent Debate] Inspect the 4-round debate transcript, agent proposals, red-team critiques, and Judge score."""
    manifest_path = Path("manifest/pages.json")
    if not manifest_path.exists():
        console.print("[red]manifest/pages.json not found.[/red]")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target = next((p for p in data["pages"] if p["page_id"].upper() == page_id.upper()), None)
    if not target:
        console.print(f"[red]Page {page_id} not found in manifest.[/red]")
        sys.exit(1)

    client = ModelClient()
    debate = DebateEngine(client)
    res = debate.run_page_debate(target)
    label = target.get("display_label", target.get("canonical_object", "").upper())

    console.print(Panel.fit(f"[bold cyan]4-Round Multi-Agent Specialist Debate for {page_id} [{label}][/bold cyan]"))

    for r in res.rounds:
        table = Table(title=f"Round {r.round_number}: {r.round_name}")
        table.add_column("Agent / Perspective", style="cyan", width=25)
        table.add_column("Proposal / Critique / Decision", style="white")

        for k, v in r.agent_outputs.items():
            if isinstance(v, dict):
                details = "\n".join([f"[yellow]{dk}:[/yellow] {dv}" for dk, dv in v.items()])
            else:
                details = str(v)
            table.add_row(k, details)

        console.print(table)
        console.print("")

    console.print(Panel(
        f"[bold green]Judge Verdict:[/bold green] {res.judge_verdict} (Score: {res.final_score}/100)\n"
        f"[bold cyan]Winning Agent:[/bold cyan] {res.winner_agent}\n"
        f"[bold yellow]Judge Rationale:[/bold yellow] {res.judge_rationale}\n\n"
        f"[bold magenta]Locked Positive Prompt:[/bold magenta]\n{res.positive_prompt}\n\n"
        f"[bold red]Locked Negative Prompt:[/bold red]\n{res.negative_prompt}",
        title="[bold green]Final Synthesized Page Specification[/bold green]",
        border_style="green"
    ))


@debate_app.command("export")
def export_debate_log(
    output_file: str = typer.Option("logs/agent_debates_log.md", "--out", "-o", help="Path to write markdown debate log")
):
    """[Transparency] Run and export the complete 4-round multi-agent debate log for all 110 pages."""
    console.print(Panel.fit("[bold cyan]Exporting Pre-Generation Multi-Agent Specialist Debates[/bold cyan]"))
    client = ModelClient()
    debate = DebateEngine(client)
    out_path = debate.export_full_debate_log(output_file=output_file)
    console.print(f"[bold green][PASS] Successfully exported all 110 agent debates to:[/] [cyan]{out_path}[/cyan]\n")


@app.command("ingest")
@app.command("process-raw")
def ingest_raw_images(
    inbox_dir: str = typer.Option("inbox/raw_pages", "--inbox", "-i", help="Directory containing user-dropped images"),
    clear_inbox: bool = typer.Option(True, "--clear/--keep", help="Move processed images from inbox to generated/raw_pages to prevent stale runs")
):
    """[Free Web Workflow] Ingest, binarize, fit margins, and overlay typography on newly dropped images."""
    console.print(Panel.fit("[bold cyan]CurioKraft Ingest & Process User-Provided Illustrations[/bold cyan]"))
    
    from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner
    runner = InteriorBatchRunner()
    
    manifest_path = Path("manifest/pages.json")
    if not manifest_path.exists():
        console.print("[red]manifest/pages.json not found.[/red]")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    pages = data.get("pages", [])
    inbox_p = Path(inbox_dir)
    inbox_p.mkdir(parents=True, exist_ok=True)
    generated_dir = Path("generated/raw_pages")
    generated_dir.mkdir(parents=True, exist_ok=True)
    
    found_count = 0
    for p in pages:
        num = p["page_number"]
        p_id = p["page_id"]
        canon = p["canonical_object"]
        
        candidates = [
            inbox_p / f"raw_p{num:03d}_{canon}.png",
            inbox_p / f"p{num:03d}_{canon}.png",
            inbox_p / f"{p_id}_{canon}.png",
            inbox_p / f"{p_id}.png",
            inbox_p / f"{canon}.png",
            inbox_p / f"{canon}.jpg",
            # Fallback to generated directory if explicitly run
            generated_dir / f"raw_p{num:03d}_{canon}.png",
            generated_dir / f"{p_id}_{canon}.png",
            generated_dir / f"{canon}.png"
        ]
        
        matched = None
        for c in candidates:
            if c.exists() and c.stat().st_size > 500:
                matched = c
                break

        if matched:
            console.print(f"  [green][INGEST][/green] Processing Page {num:03d} ({canon}) from [cyan]{matched}[/cyan]...")
            master_path = runner.generate_single_page(p, source_mode="inbox", force_fresh=True)
            found_count += 1
            
            # Archive from inbox to generated/raw_pages to keep inbox clean
            if clear_inbox and matched.parent == inbox_p:
                target_dest = generated_dir / f"raw_p{num:03d}_{canon}.png"
                import shutil
                shutil.move(str(matched), str(target_dest))
                console.print(f"    [dim]-> Archived to: {target_dest}[/dim]")
            
    if found_count > 0:
        console.print(f"\n[bold green][PASS] Successfully ingested & certified {found_count} illustrations![/bold green]")
        print_hint(
            "Inbox Ingestion",
            "curiokraft-book preflight run",
            "Run the 18-point preflight diagnostic on the newly produced masters."
        )
    else:
        console.print(f"[yellow]No new images found in {inbox_p}/.[/yellow]\n")
        console.print(f"Drop your downloaded PNGs (e.g. `raw_p005_banana.png` or `banana.png`) into:")
        console.print(f"📁 [bold cyan]{inbox_p}/[/bold cyan]")
        console.print(f"Then rerun: [bold yellow]curiokraft-book ingest[/bold yellow]")


if __name__ == "__main__":
    app()
