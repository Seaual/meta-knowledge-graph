"""
FastAPI backend for Meta Knowledge Graph
"""

import base64
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.dependencies import set_language


def _get_basic_auth_credentials() -> tuple[str, str] | None:
    """Return (user, password) if BASIC_AUTH_USER and BASIC_AUTH_PASSWORD are set."""
    user = os.environ.get("BASIC_AUTH_USER")
    password = os.environ.get("BASIC_AUTH_PASSWORD")
    if user and password:
        return user, password
    return None


async def basic_auth_middleware(request: Request, call_next):
    """Optional Basic Auth middleware (enabled when BASIC_AUTH_USER/PASSWORD env vars are set)."""
    creds = _get_basic_auth_credentials()
    if creds:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Basic"},
            )
        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            provided_user, provided_pass = decoded.split(":", 1)
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication credentials"},
                headers={"WWW-Authenticate": "Basic"},
            )
        if provided_user != creds[0] or provided_pass != creds[1]:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication credentials"},
                headers={"WWW-Authenticate": "Basic"},
            )
    response = await call_next(request)
    return response

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.routes import (
    agent,
    concepts,
    concepts_research,
    concepts_tree,
    conversations,
    dedup,
    folders,
    graph,
    llm,
    memory,
    papers,
    papers_process,
    papers_upload,
    s2,
    semantic_scholar,
)

app = FastAPI(title="Meta Knowledge Graph API", description="学术知识图谱引擎 API", version="0.1.0")

# Optional Basic Auth (enabled via BASIC_AUTH_USER / BASIC_AUTH_PASSWORD env vars)
app.middleware("http")(basic_auth_middleware)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost:8089").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Accept-Language", "Authorization", "X-Requested-With"],
)

@app.middleware("http")
async def language_middleware(request, call_next):
    lang = request.headers.get("Accept-Language", "zh")[:2]
    if lang not in ("zh", "en"):
        lang = "zh"
    set_language(lang)
    response = await call_next(request)
    return response

# Include routers
# Papers routes
app.include_router(papers.router)
app.include_router(papers_upload.router)
app.include_router(papers_process.router)

# Concepts routes (order matters: tree routes before {concept_id})
app.include_router(concepts_tree.router)
app.include_router(concepts_research.router)
app.include_router(concepts.router)
app.include_router(dedup.router)

# Other routes
app.include_router(graph.router)
app.include_router(llm.router)
app.include_router(folders.router)
app.include_router(semantic_scholar.router)
app.include_router(s2.router)
app.include_router(agent.router)
app.include_router(conversations.router)
app.include_router(memory.router)


@app.get("/api")
def api_root():
    return {"name": "Meta Knowledge Graph API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


# Create papers directory on startup
@app.on_event("startup")
def startup():
    Path("papers").mkdir(exist_ok=True)

    # Serve static frontend files in Docker mode
    frontend_dist = os.environ.get("FRONTEND_DIST")
    if frontend_dist and Path(frontend_dist).exists():
        # Mount static files (JS, CSS, assets)
        assets_path = Path(frontend_dist) / "assets"
        if assets_path.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

        logging.getLogger(__name__).info("Serving frontend from %s", frontend_dist)


# Serve frontend index.html for all non-API routes (SPA support)
# Only handle non-api paths to avoid conflicting with API routes
def _is_safe_path(base: Path, target: Path) -> bool:
    """Verify target resolves to a location inside base (path traversal guard)."""
    try:
        return target.resolve().is_relative_to(base.resolve())
    except (ValueError, OSError):
        return False


@app.get("/{path:path}")
async def serve_frontend(path: str):
    # Skip API routes - they should be handled by routers
    if path.startswith("api/") or path == "api":
        # Let FastAPI handle 404 for unknown API routes
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="API endpoint not found")

    frontend_dist = os.environ.get("FRONTEND_DIST")
    if frontend_dist and Path(frontend_dist).exists():
        base = Path(frontend_dist)

        # Check if it's a static file request
        file_path = base / path
        if _is_safe_path(base, file_path) and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # For SPA, return index.html for all other routes
        index_path = base / "index.html"
        if _is_safe_path(base, index_path) and index_path.exists():
            return FileResponse(str(index_path))

    return {"error": "Frontend not available"}
