"""
FastAPI backend for OpenClaw Web UI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.routes import papers, concepts, graph

app = FastAPI(
    title="Meta Knowledge Graph API",
    description="学术知识图谱引擎 API",
    version="0.1.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(papers.router)
app.include_router(concepts.router)
app.include_router(graph.router)


@app.get("/")
def root():
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