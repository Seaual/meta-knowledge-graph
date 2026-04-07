<p align="center">
  <img src="icon/mkg-icon-512.svg" alt="MKG Logo" width="150">
</p>

<h1 align="center">Meta Knowledge Graph</h1>

<p align="center">
  <a href="README_CN.md">简体中文</a> | <strong>English</strong>
</p>

<p align="center">
  <strong>LLM-powered Academic Knowledge Graph Engine</strong>
</p>

<p align="center">
  <a href="https://github.com/Seaual/meta-knowledge-graph/stargazers"><img src="https://img.shields.io/github/stars/Seaual/meta-knowledge-graph?style=social" alt="Stars" /></a>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker Ready">
  <img src="https://img.shields.io/github/license/Seaual/meta-knowledge-graph" alt="License">
  <img src="https://img.shields.io/github/v/release/Seaual/meta-knowledge-graph" alt="Release">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/LLM-Claude%20%7C%20Gemini%20%7C%20Qwen-8A2BE2" alt="LLM">
</p>

<p align="center">
  Automatically extract hierarchical concepts from PDF papers<br>
  with interactive force-directed graph visualization
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#key-features">Features</a> •
  <a href="#concept-hierarchy">Concepts</a> •
  <a href="#roadmap">Roadmap</a> •
  <a href="https://github.com/Seaual/meta-knowledge-graph/issues">Issues</a>
</p>

---

## What's New in v2.2

| Feature | Description |
|---------|-------------|
| 💬 **Chat Attachments** | LLM Agent conversation-driven with interactive cards for research points, paper details, recommendations, etc. |
| 🛠️ **Agent Tool Optimization** | Fixed LLM over-calling multiple tools, now processes one tool per turn |
| 🌐 **Full Bilingual Support** | Added `text_zh` database field for complete Chinese/English concept names |
| 🔧 **Improved Dedup Prompts** | Optimized prompts for concept merge judgment and floating concept fixing |

---

## What's New in v2.1

| Feature | Description |
|---------|-------------|
| 🧠 **Improved Extraction Prompt** | Two-stage prompt optimized for better background/novel concept distinction |
| 🌐 **Bilingual Concepts** | Concepts stored in both Chinese and English for better S2 paper search |
| 📚 **Paper Recommendation** | Search related papers by concept on Semantic Scholar |
| 🔍 **Enhanced Research Discovery** | Fixed research points discovery with S2 trend analysis |
| 🎨 **UI Improvements** | Fixed language switching, venue display overflow, and more |

---

## What's New in v2.0

| Feature | Description |
|---------|-------------|
| 🎨 **Academic Light Theme** | Warm cream/sepia color palette with elegant typography (Playfair Display + Source Sans) |
| 🌐 **Bilingual Support** | Full Chinese/English UI with automatic language detection |
| 📚 **Semantic Scholar Integration** | Auto-enhance paper metadata (DOI, citations, venue, authors) |
| 🔍 **Graph Search & Filter** | Search concepts by name, filter by category with visual highlighting |
| 📊 **Category-based Node Sizes** | Node sizes decrease by hierarchy (field → direction → ... → technique) |
| 🎓 **Onboarding Tutorial** | First-time user guide with demo data (10 classic LLM papers) |

---

## Demo

### Knowledge Graph Browsing

![Knowledge Graph Browsing](docs/概念浏览.gif)

*Drag nodes, zoom, search concepts, filter by category*

### Research Points Discovery

![Research Points Discovery](docs/研究点发现.gif)

*Click concept → Discover research points → View analysis context*

### Feature Overview

![Feature Overview](docs/功能展示.gif)

*Upload PDFs → Process → Explore graph → Export*

### LLM Configuration

![LLM Configuration](docs/配置LLM.gif)

*Configure API Key → Test connection → Start processing*

---

## Key Features

| Feature | Description |
|---------|-------------|
| 📄 **PDF Parsing** | Extract title, authors, abstract automatically |
| 🧠 **Two-Stage Extraction** | Stage 1: Paper understanding → Stage 2: Core concept extraction |
| 📊 **Visualization** | Obsidian/Neo4j-style force-directed graph with category-based node sizes |
| 🔍 **Research Discovery** | Four methodologies: gap filling, leaf extension, bottleneck, transfer |
| 🔄 **Smart Deduplication** | Three merge types: synonym, absorption, translation |
| 📤 **Multi-format Export** | HTML, Obsidian Canvas, Markdown |
| 📁 **Folder Management** | Collapsible sidebar for paper organization |
| ⚡ **Queue Processing** | Sequential batch processing with time estimation |
| 🌐 **Bilingual UI** | Full Chinese/English support with auto-detection |
| 📚 **S2 Enhancement** | Auto-fetch metadata from Semantic Scholar API |
| 🐳 **Docker Ready** | One-command deployment with Docker Hub image |

---

## Architecture

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
                      │ LLM API / S2 API
┌─────────────────────▼───────────────────────────┐
│              External Services                   │
│   LLM: Claude/Gemini/Qwen   S2: Metadata API    │
└─────────────────────────────────────────────────┘
```

**Data Flow:** `PDF → S2 Enhancement → LLM Extract (Two-Stage) → Knowledge Graph → Export`

---

## Quick Start

### One-Click Deploy (Recommended)

**Linux / Mac:**
```bash
curl -fsSL https://raw.githubusercontent.com/Seaual/meta-knowledge-graph/main/deploy.sh | bash
```

**Windows:**
```cmd
curl -fsSL https://raw.githubusercontent.com/Seaual/meta-knowledge-graph/main/deploy.bat -o deploy.bat && deploy.bat
```

Or download and run:
- Linux/Mac: `chmod +x deploy.sh && ./deploy.sh`
- Windows: Double-click `deploy.bat`

Open http://localhost:8088

**Configure LLM**: Go to **Settings** page in the browser to configure your API Key (supports Claude, OpenAI, Gemini, Qwen, DeepSeek, etc.)

> 💡 API Keys are saved locally in the database, no environment variables needed.

### Docker Manual

```bash
# Pull and run
docker pull danceinsophy/meta-knowledge-graph:latest
docker run -d -p 8088:8088 \
  -v mkg-data:/app/data \
  -v mkg-papers:/app/papers \
  --restart unless-stopped \
  danceinsophy/meta-knowledge-graph:latest
```

Open http://localhost:8088

### Docker Compose

```bash
# Clone and run
git clone https://github.com/Seaual/meta-knowledge-graph.git
cd meta-knowledge-graph/docker

# Start
docker-compose up -d
```

### Manual Setup

<details>
<summary>Click to expand</summary>

```bash
# Clone
git clone https://github.com/Seaual/meta-knowledge-graph.git
cd meta-knowledge-graph

# Backend
python -m venv venv
source venv/bin/activate  # Linux/Mac, or: venv\Scripts\activate (Windows)
pip install -r requirements.txt

# Start Backend
python -m uvicorn backend.main:app --port 8088 --reload &

# Start Frontend
cd frontend && npm run dev
```

Open http://localhost:5173 and configure your API Key in **Settings** page.

</details>

---

## Feature Details

### Two-Stage Concept Extraction

```
Stage 1: Paper Understanding
├── Research context identification
├── Core contribution distinction
├── Background/novel concept classification
└── Bilingual output (English + Chinese)

Stage 2: Concept Extraction
├── Anchor path (paper positioning)
├── Contribution subtree (actual contributions)
├── Contribution role annotation (proposed/improved/applied/analyzed)
└── Category assignment (field/direction/subdirection/task/method/technique/dataset/finding)
```

### Research Point Discovery Methods

| Method | Description |
|--------|-------------|
| 🔍 **Gap Filling** | Missing connections between related branches |
| 🌱 **Leaf Extension** | Leaf nodes applied to other branches |
| 🔥 **Bottleneck** | Node with many children but few siblings |
| 🔄 **Transfer** | Mature methods transferred to unsolved problems |

### Concept Hierarchy

| Category | Description | Example | Node Size |
|----------|-------------|---------|-----------|
| field | Major domain | Artificial Intelligence | Largest |
| direction | Research direction | Multi-Agent RL | Large |
| subdirection | Sub-direction | Value Decomposition | Medium |
| task | Research task | Credit Assignment | Small |
| method | Algorithm | QMIX | Smaller |
| technique | Technical detail | Attention-weighted mixing | Smallest |
| dataset | Benchmark/Dataset | ImageNet, SMAC | Medium |
| finding | Key discovery | Scaling Laws | Medium |

---

## Usage

### Upload Papers
1. Go to **Papers** page
2. Click upload button, select PDF files (batch supported)
3. Papers appear in **Pending** list with auto-enhanced metadata from Semantic Scholar

### Process Papers
1. Click **Process** or **Batch Process**
2. LLM extracts concept tree with bilingual names
3. Concepts added to knowledge graph

### Explore Graph
1. Go to **Concepts** page
2. Drag nodes, scroll to zoom
3. Use search box to find concepts, filter by category
4. Click concept for details

### Discover Research Points
1. Click a concept node
2. Click **Discover Research Points**
3. LLM analyzes graph structure, generates 3-5 research directions with S2 trend analysis

### Find Related Papers
1. Click a concept node
2. Click **Search Papers**
3. View related papers from Semantic Scholar (searches using English concept names)

### Deduplicate
1. Click **Dedup Scan**
2. Review merge suggestions (synonym/absorption/translation)
3. Execute selected merges

### Export Graph
- **HTML** - Interactive D3.js force-directed graph (standalone)
- **Canvas** - Obsidian Canvas format
- **Markdown** - Double-link format notes

---

## Supported LLM Providers

| Provider | Type | Configuration |
|----------|------|---------------|
| **Anthropic Claude** | Native API | `ANTHROPIC_API_KEY` |
| **Claude CLI** | Local CLI | Automatic |
| **Google Gemini** | Native API | `GOOGLE_API_KEY` |
| **Alibaba DashScope** | OpenAI Compatible | `DASHSCOPE_API_KEY` |
| **OpenRouter** | OpenAI Compatible | `OPENAI_API_KEY` + base_url |
| **DeepSeek** | OpenAI Compatible | Custom base_url |
| **MiniMax** | OpenAI Compatible | Custom base_url |

---

## Tech Stack

**Backend:** Python 3.10+ • FastAPI • SQLite • PyMuPDF

**Frontend:** React 18 • TypeScript • Vite • TailwindCSS • D3.js

**LLM:** Claude / Gemini / Qwen / DeepSeek / OpenRouter

**External APIs:** Semantic Scholar (paper metadata enhancement)

---

## Project Structure

```
meta-knowledge-graph/
├── backend/           # FastAPI backend
│   ├── main.py        # App entry
│   ├── routes/        # API routes
│   └── schemas.py     # Data models
├── frontend/          # React frontend
│   └── src/
│       ├── pages/     # Page components
│       ├── components/
│       └── i18n/      # Internationalization (zh/en)
├── mkg/               # Core library
│   ├── database.py    # Database operations
│   ├── graph.py       # Graph operations
│   ├── pdf_parser.py  # PDF parsing & LLM extraction
│   ├── semantic_scholar.py  # S2 API client
│   └── dedup/         # Deduplication module
├── papers/            # Paper storage
├── scripts/           # Utility scripts (demo data, etc.)
├── icon/              # Project icons
└── PROMPT_GUIDE.md    # Prompt engineering guide
```

---

## API Reference

Access http://localhost:8088/docs after starting

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/papers/upload` | POST | Upload PDF |
| `/api/papers/batch-upload` | POST | Batch upload |
| `/api/papers/batch-process` | POST | Batch process |
| `/api/s2/papers/{doi}/enhance` | POST | Enhance metadata from S2 |
| `/api/concepts/` | GET | Get all concepts |
| `/api/concepts/{id}/research-points` | GET | Discover research points |
| `/api/concepts/{id}/search-papers` | GET | Search papers by concept |
| `/api/concepts/dedup/scan` | POST | Scan duplicates |
| `/api/graph/export/obsidian/html` | GET | Export HTML |

---

## Roadmap

- [x] More LLM backends (DeepSeek, OpenRouter, MiniMax)
- [x] Concept deduplication
- [x] Multi-format export
- [x] Batch processing
- [x] Two-stage concept extraction
- [x] Research point discovery methodologies
- [x] Academic light theme UI
- [x] Bilingual support (Chinese/English)
- [x] Semantic Scholar metadata enhancement
- [x] Graph search and filter
- [x] Bilingual concept names for better S2 search
- [x] Paper recommendation by concept
- [ ] Collaboration features
- [ ] Neo4j support

---

## Contributing

Issues and Pull Requests welcome!

## License

MIT License

---

<p align="center">
  <img src="icon/mkg-logo-horizontal.svg" alt="MKG Logo" width="200">
</p>

<p align="center">
  Made with ❤️ by <a href="https://github.com/Seaual">Seaual</a>
</p>