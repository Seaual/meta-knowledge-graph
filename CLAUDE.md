# Claude Code — Project Context

> This file provides project-level context for Claude Code when working with the Meta Knowledge Graph (MKG) codebase.
> Reference tree: https://github.com/Seaual/meta-knowledge-graph/tree/codex/release-0.1.1

## Project Overview

**Meta Knowledge Graph** is an LLM-driven academic knowledge graph engine. Researchers upload PDFs, and the system automatically extracts hierarchical concepts (8-level taxonomy) and builds an interactive knowledge graph for research opportunity discovery via AI Agents.

- **Repository**: https://github.com/Seaual/meta-knowledge-graph
- **Version**: 0.1.0
- **License**: MIT

## Architecture

```
frontend/          React 18 + TypeScript + Vite + TailwindCSS + D3.js
backend/           FastAPI + SQLite (WAL mode) + LangGraph agents
mkg/               Core domain library
├── database/           SQLite database package (core, schema, migrations, compat)
├── repositories/       Data access layer (papers, concepts, folders, ...)
├── agent/              LangGraph multi-agent system
│   ├── nodes/          Lead, Research, Citation, Paper QA, Summarize
│   ├── tools.py        Agent tools
│   └── research_graph.py  Async deep research orchestration
├── dedup/              Concept deduplication (synonym, absorption, translation)
├── llm.py              LLMClient + MKGChatModel adapter (native HTTP, OpenAI/Anthropic)
├── resilience.py       Retry wrapper for external calls
├── semantic_scholar.py S2 API client for metadata enhancement
└── concept_extractor.py  Two-stage concept extraction pipeline
```

## Coding Conventions

### Python
- Target Python 3.10+
- Type annotations required on public APIs
- `ruff` for lint/format (line length 120)
- `pyright` for type checking (standard mode)
- First-party imports: `backend`, `mkg`
- Database access goes through `mkg/repositories/`, not raw SQL in routes

### TypeScript / React
- React 18 with functional components and hooks
- `zustand` for state management
- API clients live in `frontend/src/lib/api/`
- Components use `clsx` + `tailwind-merge` for class composition
- `prettier` + `eslint` enforced in CI

## Common Tasks

### Add a new API endpoint
1. Add Pydantic schemas to `backend/schemas.py` if needed
2. Add route handler in `backend/routes/` (follow existing router patterns)
3. Register router in `backend/main.py`
4. Add API client in `frontend/src/lib/api/` if frontend consumes it

### Add a new LLM provider
1. Update `mkg/llm_client.py` — add new `_call_*` method
2. Add config fields in `backend/routes/llm.py` if UI config needed

### Database schema changes
1. Update `mkg/database/schema.py` schema definitions
2. Add migration logic in `mkg/database/migrations.py` or `mkg/database/compat.py`
3. Update repositories in `mkg/repositories/` as needed

## Security Notes
- API Keys are stored locally in SQLite; encryption should be confirmed before server deployment
- CORS is restricted to known origins in production (see `backend/main.py`)
- No built-in auth yet; Docker deploys should use reverse proxy + Basic Auth

## GitNexus
This project uses GitNexus for code intelligence. See `AGENTS.md` for GitNexus-specific tooling rules and impact analysis requirements.
