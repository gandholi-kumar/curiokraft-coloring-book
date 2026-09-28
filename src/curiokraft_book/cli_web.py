"""Web Publishing Studio CLI management commands for CurioKraft.

Commands:
- start: Start the production FastAPI API Gateway and WebSocket server with auto-browser launch.
- status: Check whether the CurioKraft Publishing Studio gateway is running and query /api/health.
"""

from __future__ import annotations

import threading
import time
import webbrowser

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from curiokraft_book import __version__

web_app = typer.Typer(help="[Studio Web UI] Interactive Web Publishing Studio gateway & server")
console = Console(force_terminal=True, legacy_windows=False)


def _open_browser_delayed(url: str, delay_seconds: float = 1.2) -> None:
    """Open the web browser in a background thread once the server starts."""

    def _target():
        time.sleep(delay_seconds)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_target, daemon=True).start()


@web_app.command("start")
def start_web_server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address for the gateway"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port number for the gateway"),
    reload: bool = typer.Option(
        False, "--reload", "-r", help="Enable auto-reload on code changes (development)"
    ),
    open_browser: bool = typer.Option(
        True,
        "--open-browser/--no-open-browser",
        help="Automatically open web browser to the studio dashboard",
    ),
    db_url: str | None = typer.Option(
        None, "--db-url", help="Database URL override (PostgreSQL or SQLite)"
    ),
):
    """[Studio Gateway] Launch the CurioKraft Publishing Studio API & WebSocket server."""
    base_url = f"http://{host}:{port}"
    docs_url = f"{base_url}/docs"
    ws_url = f"ws://{host}:{port}/ws"

    console.print(
        Panel.fit(
            f"[bold cyan]CurioKraft Publishing Studio Gateway v{__version__}[/bold cyan]\n\n"
            f"  • [bold white]Web Studio URL:[/]   [bold green]{base_url}[/bold green]\n"
            f"  • [bold white]Interactive Docs:[/] [bold blue]{docs_url}[/bold blue]\n"
            f"  • [bold white]WebSocket Channel:[/] [bold magenta]{ws_url}[/bold magenta]\n\n"
            f"[dim]Press Ctrl+C to gracefully stop the gateway server.[/dim]",
            title="[bold yellow]CurioKraft Studio Web Server[/bold yellow]",
            border_style="cyan",
        )
    )

    if open_browser:
        _open_browser_delayed(base_url)

    # Launch uvicorn server
    uvicorn.run(
        "curiokraft_book.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@web_app.command("status")
def check_web_status(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address to probe"),
    port: int = typer.Option(8000, "--port", "-p", help="Port number to probe"),
):
    """[Health Diagnostic] Probe the local CurioKraft Studio gateway for status."""
    import httpx

    target_url = f"http://{host}:{port}/api/health"
    try:
        resp = httpx.get(target_url, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            table = Table(
                title=f"CurioKraft Studio Gateway Online ({target_url})", border_style="green"
            )
            table.add_column("Property", style="bold cyan")
            table.add_column("Value", style="green")

            table.add_row("Status", str(data.get("status", "ok")).upper())
            table.add_row("Version", str(data.get("version", __version__)))
            table.add_row("Database", str(data.get("db_status", "connected")))
            table.add_row("Storage Backend", str(data.get("storage_backend", "local_disk")))
            table.add_row("Probe Timestamp", str(data.get("timestamp", "")))

            console.print(table)
        else:
            console.print(
                Panel.fit(
                    f"[bold yellow]Gateway returned unexpected HTTP {resp.status_code}[/bold yellow]\n{resp.text}",
                    title="CurioKraft Studio Health Warning",
                    border_style="yellow",
                )
            )
    except Exception as e:
        console.print(
            Panel.fit(
                f"[bold red]CurioKraft Studio Gateway is not running on {host}:{port}[/bold red]\n\n"
                f"[dim]Error: {e}[/dim]\n\n"
                f"Start the server with: [bold green]curiokraft-book web start[/bold green]",
                title="CurioKraft Studio Offline",
                border_style="red",
            )
        )
