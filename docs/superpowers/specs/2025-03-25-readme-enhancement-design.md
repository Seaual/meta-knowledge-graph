# README Enhancement Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform README into a professional landing page with demo GIF, architecture diagram, Docker deployment, and bilingual support.

**Architecture:** Single Docker container with both frontend and backend. README structured as: Header/Badges → Demo GIF → Architecture Diagram → Quick Start (Docker) → Features → Detailed Docs → Separator → English Version.

**Tech Stack:** Markdown, Docker (single container), GIF for demo

---

## Deliverables

### 1. README.md Structure

```
┌─────────────────────────────────────┐
│ Title + Badges (Docker/License/Ver) │
├─────────────────────────────────────┤
│ Demo GIF (5 core features)          │
├─────────────────────────────────────┤
│ Architecture Diagram                │
│ - Layered view (Frontend/Backend/LLM)│
│ - Data flow (PDF→Extract→Graph→Export)│
├─────────────────────────────────────┤
│ Quick Start (Docker one-liner)      │
├─────────────────────────────────────┤
│ Features Grid (with icons)          │
├─────────────────────────────────────┤
│ Detailed Usage (中文)               │
├─────────────────────────────────────┤
│ Project Structure / API Docs        │
├─────────────────────────────────────┤
│ ─────────── Separator ───────────── │
├─────────────────────────────────────┤
│ Full English Version                │
└─────────────────────────────────────┘
```

### 2. Dockerfile (Single Container)

- Base: `python:3.11-slim`
- Frontend: Build with Node.js, serve static files via FastAPI
- Backend: FastAPI on port 8088
- Single port exposure (8088) with frontend served at `/` and API at `/api`
- Environment variables for LLM API keys
- Volume mount for data persistence

### 3. Demo GIF Requirements

Record these 5 operations (user will record, we provide guidance):

1. **Upload Paper** - Click upload, select PDF, show processing
2. **Knowledge Graph** - Drag nodes, zoom, click concept
3. **Research Points** - Click "发现研究点", show LLM analysis
4. **Dedup** - Click "去重扫描", show suggestions, merge
5. **Export** - Click export dropdown, select HTML, download

### 4. Architecture Diagram

ASCII/Mermaid diagram embedded in Markdown:

```
┌─────────────────────────────────────────────────┐
│                  Frontend                        │
│         React + TypeScript + D3.js               │
└─────────────────────┬───────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────┐
│                  Backend                         │
│      FastAPI + SQLite + PyMuPDF                  │
└─────────────────────┬───────────────────────────┘
                      │ LLM API
┌─────────────────────▼───────────────────────────┐
│                 LLM Layer                        │
│         Claude / Gemini / Qwen                   │
└─────────────────────────────────────────────────┘
```

Data flow: `PDF → Extract → Knowledge Graph → Export`

---

## Implementation Tasks

### Task 1: Create Dockerfile
- Multi-stage build (Node.js for frontend, Python for backend)
- Single container serving both
- Port 8088
- Environment variables support

### Task 2: Create docker-compose.yml (optional, for convenience)
- Simplify docker run command
- Environment file support

### Task 3: Update README.md
- Add badges
- Add demo GIF placeholder
- Add architecture diagram
- Add Docker quick start
- Restructure features section
- Add separator and full English version

### Task 4: Create demo recording guide
- Document which operations to record
- Suggested tools (ScreenToGif on Windows)
- Frame rate and size recommendations

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `Dockerfile` | Create | Multi-stage build for single container |
| `docker-compose.yml` | Create | Optional convenience file |
| `.dockerignore` | Create | Exclude unnecessary files |
| `README.md` | Modify | Complete rewrite with new structure |
| `docs/demo-recording-guide.md` | Create | Instructions for recording demo GIF |

---

## Docker Commands

**Build:**
```bash
docker build -t seaual/meta-knowledge-graph:latest .
```

**Run:**
```bash
docker run -d -p 8088:8088 \
  -e ANTHROPIC_API_KEY=sk-ant-xxx \
  -v ./data:/app/data \
  seaual/meta-knowledge-graph:latest
```

**Access:** http://localhost:8088