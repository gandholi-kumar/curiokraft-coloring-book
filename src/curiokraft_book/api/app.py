"""FastAPI Application Factory for CurioKraft Publishing Studio.

Provides:
- Lifespan management for database & storage connections
- Permissive CORS configuration for decoupled SPA development
- Static asset serving for compiled React application
- Fallback SPA HTML routing
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from curiokraft_book import __version__
from curiokraft_book.api.routes import api_router, websocket_endpoint
from curiokraft_book.api.websocket_manager import ws_manager
from curiokraft_book.data.hybrid_store import HybridDataStore

logger = logging.getLogger("curiokraft.api.app")


def create_app(
    db_url: str | None = None,
    static_dir: str | Path | None = None,
    test_mode: bool = False,
) -> FastAPI:
    """Factory creating and configuring the production FastAPI instance."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage initialization and teardown of shared store and workers."""
        logger.info("Initializing CurioKraft API Gateway...")
        # Initialize Hybrid Data Store if not already injected
        if not hasattr(app.state, "store") or app.state.store is None:
            app.state.store = HybridDataStore(db_url=db_url)

        await ws_manager.broadcast_log(
            level="INFO",
            message=f"CurioKraft Studio API v{__version__} started",
            component="server",
            context={"version": __version__, "test_mode": test_mode},
        )
        yield
        logger.info("CurioKraft API Gateway shutting down...")
        await ws_manager.broadcast_log(
            level="INFO",
            message="CurioKraft Studio API stopping",
            component="server",
        )

    app = FastAPI(
        title="CurioKraft Publishing Studio API",
        description="High-performance backend gateway for CurioKraft coloring book production",
        version=__version__,
        lifespan=lifespan,
    )

    # --------------------------------------------------------------------------
    # CORS Middleware (Fully Permissive for Decoupled Web UI)
    # --------------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --------------------------------------------------------------------------
    # API Routes & WebSocket Mounting
    # --------------------------------------------------------------------------
    app.include_router(api_router)
    # Also expose /ws at root path for simple client connection
    app.add_api_websocket_route("/ws", websocket_endpoint)

    # --------------------------------------------------------------------------
    # Static Inbox & Generated Asset Directories
    # --------------------------------------------------------------------------
    inbox_path = Path("inbox")
    inbox_path.mkdir(parents=True, exist_ok=True)
    app.mount("/inbox", StaticFiles(directory=str(inbox_path)), name="inbox")

    generated_path = Path("generated")
    generated_path.mkdir(parents=True, exist_ok=True)
    app.mount("/generated", StaticFiles(directory=str(generated_path)), name="generated")

    # --------------------------------------------------------------------------
    # Static Assets & SPA Routing
    # --------------------------------------------------------------------------
    resolved_static = None
    if static_dir:
        resolved_static = Path(static_dir)
    else:
        # Check standard web/dist locations
        candidates = [
            Path.cwd() / "web" / "dist",
            Path(__file__).parent.parent.parent.parent / "web" / "dist",
        ]
        for c in candidates:
            if c.exists() and (c / "index.html").exists():
                resolved_static = c
                break

    if resolved_static and resolved_static.exists():
        assets_dir = resolved_static / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> FileResponse:
            """Catch-all route returning index.html for SPA client-side routing."""
            file_candidate = resolved_static / full_path
            if file_candidate.is_file() and file_candidate.exists():
                return FileResponse(file_candidate)
            return FileResponse(resolved_static / "index.html")
    else:

        @app.get("/", include_in_schema=False)
        async def root_status() -> HTMLResponse:
            """Friendly landing page when frontend is running independently in dev mode."""
            return HTMLResponse(
                f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CurioKraft Publishing Studio API</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0B0E14;
      color: #F8FAFC;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }}
    .card {{
      background: #151A23;
      border: 1px solid #232936;
      border-radius: 16px;
      padding: 40px;
      max-width: 540px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
      text-align: center;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      background: #0284C7;
      color: white;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-bottom: 16px;
    }}
    h1 {{ font-size: 24px; margin: 0 0 12px 0; color: #FFFFFF; }}
    p {{ color: #94A3B8; font-size: 14px; line-height: 1.6; margin-bottom: 24px; }}
    .links {{ display: flex; gap: 12px; justify-content: center; }}
    .btn {{
      display: inline-block;
      padding: 10px 20px;
      border-radius: 8px;
      text-decoration: none;
      font-size: 14px;
      font-weight: 600;
      transition: all 0.2s ease;
    }}
    .btn-primary {{ background: #0284C7; color: white; }}
    .btn-primary:hover {{ background: #0369A1; }}
    .btn-secondary {{ background: #232936; color: #CBD5E1; }}
    .btn-secondary:hover {{ background: #2E3848; color: white; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">CurioKraft Studio Gateway v{__version__}</div>
    <h1>Publishing Studio Gateway Online</h1>
    <p>The FastAPI backend and real-time WebSocket channel are operational. Connect your decoupled React frontend on port 5173 or inspect the interactive API documentation.</p>
    <div class="links">
      <a href="/docs" class="btn btn-primary">Swagger OpenAPI Docs</a>
      <a href="/api/health" class="btn btn-secondary">Health Check</a>
    </div>
  </div>
</body>
</html>"""
            )

    return app
