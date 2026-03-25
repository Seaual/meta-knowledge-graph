"""
FastAPI backend for OpenClaw Web UI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.routes import papers, concepts, graph, llm

app = FastAPI(
    title="Meta Knowledge Graph API",
    description="学术知识图谱引擎 API",
    version="0.1.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(papers.router)
app.include_router(concepts.router)
app.include_router(graph.router)
app.include_router(llm.router)


@app.get("/api")
def api_root():
    return {
        "name": "Meta Knowledge Graph API",
        "version": "0.1.0",
        "docs": "/docs"
    }


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

        print(f"Serving frontend from {frontend_dist}")


# Serve frontend index.html for all non-API routes (SPA support)
@app.get("/{path:path}")
async def serve_frontend(path: str):
    frontend_dist = os.environ.get("FRONTEND_DIST")
    if frontend_dist and Path(frontend_dist).exists():
        # Check if it's a static file request
        file_path = Path(frontend_dist) / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # For SPA, return index.html for all other routes
        index_path = Path(frontend_dist) / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))

    return {"error": "Frontend not available"}