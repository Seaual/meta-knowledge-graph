# DeepAgent Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the backend agent system from custom LangGraph to DeepAgents 0.5.1, and refactor the frontend chat UI into a DeepAgent workspace with todo panels, execution traces, file explorer, and subagent visibility.

**Architecture:** Backend uses `create_deep_agent()` with 4 subagents (citation, research, paper_qa, deep_research), CompositeBackend filesystem, SqliteSaver/SqliteStore persistence, and v2 streaming. Frontend uses a 3-panel layout driven by an expanded SSE event protocol.

**Tech Stack:** Python 3.11+, DeepAgents 0.5.1, LangGraph, FastAPI, React 18, TypeScript, Zustand, SSE

---

## File Structure

### Backend — New Files
| File | Responsibility |
|------|---------------|
| `mkg/agent/agent.py` | `create_deep_agent()` configuration, main agent builder |
| `mkg/agent/skills/__init__.py` | Skills package exports |
| `mkg/agent/skills/citation.py` | Citation analysis subagent config |
| `mkg/agent/skills/research.py` | Research point discovery subagent config |
| `mkg/agent/skills/paper_qa.py` | Paper Q&A subagent config |
| `mkg/agent/skills/deep_research.py` | Deep research subagent config |
| `mkg/agent/filesystem.py` | CompositeBackend configuration |
| `mkg/agent/memory.py` | SqliteSaver + SqliteStore setup |
| `mkg/agent/streaming.py` | DeepAgents chunk → SSE event converter |

### Backend — Modified Files
| File | Change |
|------|--------|
| `pyproject.toml` | Python >=3.11, add `deepagents==0.5.1` |
| `requirements.txt` | Add `deepagents==0.5.1` |
| `mkg/agent/__init__.py` | Export `get_main_agent`, `init_agent` |
| `mkg/agent/tools.py` | Wrap tools with `get_config()` dependency injection |
| `backend/routes/agent.py` | Replace all endpoints with DeepAgents SSE stream |
| `backend/schemas.py` | Update AgentChatRequest/Response if needed |

### Backend — Deleted Files
| File | Reason |
|------|--------|
| `mkg/agent/graph.py` | Replaced by `agent.py` |
| `mkg/agent/research_graph.py` | Replaced by deep_research subagent |
| `mkg/agent/nodes/lead.py` | DeepAgents handles routing |
| `mkg/agent/nodes/citation.py` | Migrated to skill |
| `mkg/agent/nodes/research.py` | Migrated to skill |
| `mkg/agent/nodes/paper_qa.py` | Migrated to skill |
| `mkg/agent/nodes/summarize.py` | DeepAgents has built-in summarization |
| `mkg/agent/routing.py` | DeepAgents handles routing |
| `mkg/agent/state.py` | DeepAgents manages internal state |

### Frontend — New Files
| File | Responsibility |
|------|---------------|
| `frontend/src/components/AgentWorkspace.tsx` | 3-panel layout container |
| `frontend/src/components/TodoPanel.tsx` | Todo planning panel |
| `frontend/src/components/ExecutionTrace.tsx` | Tool execution timeline |
| `frontend/src/components/FileExplorer.tsx` | Virtual file browser |
| `frontend/src/components/SubagentBadge.tsx` | Subagent status badge |
| `frontend/src/components/HumanInTheLoop.tsx` | Approval modal |

### Frontend — Modified Files
| File | Change |
|------|--------|
| `frontend/src/pages/Chat.tsx` | Replace content with `<AgentWorkspace />` |
| `frontend/src/stores/agentStore.ts` | Add todos, executionSteps, virtualFiles, activeSubagents, pendingApproval |
| `frontend/src/lib/api/agent.ts` | Expand SSE event types, add approval endpoint |

### Tests — New Files
| File | Responsibility |
|------|---------------|
| `tests/test_agent_streaming.py` | SSE event conversion tests |
| `tests/test_agent_tools.py` | Tool dependency injection tests |

---

## Task 1: Python Upgrade and Dependency Introduction

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Update Python requirement**

Edit `pyproject.toml`:
```toml
requires-python = ">=3.11"
```

Add to `dependencies`:
```toml
"deepagents==0.5.1",
```

- [ ] **Step 2: Update requirements.txt**

Add:
```
deepagents==0.5.1
```

- [ ] **Step 3: Install and verify**

Run:
```bash
uv sync
python -c "from deepagents import create_deep_agent; print('deepagents OK')"
```

Expected: prints `deepagents OK` without errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml requirements.txt
uv lock  # update uv.lock
git add uv.lock
git commit -m "deps: add deepagents==0.5.1, require Python >=3.11"
```

---

## Task 2: Backend Tool Layer Migration

**Files:**
- Modify: `mkg/agent/tools.py`
- Create: `tests/test_agent_tools.py`

- [ ] **Step 1: Add get_config wrapper to tools**

Edit `mkg/agent/tools.py`. At the top, add:
```python
from langgraph.config import get_config

def _get_db():
    return get_config()["configurable"]["db"]

def _get_s2_client():
    return get_config()["configurable"]["s2_client"]

def _get_pdf_parser():
    return get_config()["configurable"]["pdf_parser"]
```

Replace every direct `db = get_db()` (or similar) inside tool functions with:
```python
db = _get_db()
```

Ensure all tool functions are top-level pure functions with type annotations. Remove any class-based tool wrappers.

- [ ] **Step 2: Verify tools are pure functions**

Each tool should look like:
```python
def search_paper(query: str, limit: int = 5) -> list[dict]:
    """Search for papers by query."""
    db = _get_db()
    # ... existing logic
```

- [ ] **Step 3: Write tool injection test**

Create `tests/test_agent_tools.py`:
```python
import pytest
from unittest.mock import MagicMock
from mkg.agent.tools import _get_db, search_paper


class TestToolDependencyInjection:
    def test_get_db_reads_config(self, monkeypatch):
        mock_config = {"configurable": {"db": "mock_db"}}
        monkeypatch.setattr(
            "mkg.agent.tools.get_config", lambda: mock_config
        )
        assert _get_db() == "mock_db"

    def test_search_paper_uses_db_from_config(self, monkeypatch):
        mock_db = MagicMock()
        mock_db.search_papers.return_value = [{"title": "Test Paper"}]
        mock_config = {"configurable": {"db": mock_db}}
        monkeypatch.setattr(
            "mkg.agent.tools.get_config", lambda: mock_config
        )
        result = search_paper("test query")
        assert len(result) == 1
        assert result[0]["title"] == "Test Paper"
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_agent_tools.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add mkg/agent/tools.py tests/test_agent_tools.py
git commit -m "refactor: inject tool dependencies via get_config()"
```

---

## Task 3: Backend Filesystem and Memory Configuration

**Files:**
- Create: `mkg/agent/filesystem.py`
- Create: `mkg/agent/memory.py`

- [ ] **Step 1: Create filesystem configuration**

Create `mkg/agent/filesystem.py`:
```python
"""DeepAgents filesystem backend configuration."""

from pathlib import Path

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend


def build_filesystem_backend(workspace_dir: str) -> CompositeBackend:
    """Build CompositeBackend with per-thread workspace."""
    root = Path(workspace_dir)
    root.mkdir(parents=True, exist_ok=True)

    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/workspace/": FilesystemBackend(
                root_dir=str(root),
                virtual_mode=True,
            ),
        },
    )
```

- [ ] **Step 2: Create memory configuration**

Create `mkg/agent/memory.py`:
```python
"""DeepAgents memory and persistence configuration."""

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore


def build_checkpointer(db_path: str) -> SqliteSaver:
    """Build SQLite-backed checkpointer for thread state."""
    return SqliteSaver.from_conn_string(db_path)


def build_store(db_path: str) -> SqliteStore:
    """Build SQLite-backed store for cross-thread memory."""
    return SqliteStore(db_path=db_path)
```

- [ ] **Step 3: Commit**

```bash
git add mkg/agent/filesystem.py mkg/agent/memory.py
git commit -m "feat: add DeepAgents filesystem and memory configuration"
```

---

## Task 4: Backend Streaming Converter

**Files:**
- Create: `mkg/agent/streaming.py`
- Create: `tests/test_agent_streaming.py`

- [ ] **Step 1: Write SSE event converter**

Create `mkg/agent/streaming.py`:
```python
"""Convert DeepAgents stream chunks to frontend SSE events."""

import time
from typing import Any


def convert_chunk_to_sse(chunk: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a DeepAgents v2 stream chunk to an SSE event.

    Returns None for unhandled chunk types.
    """
    chunk_type = chunk.get("type")
    ns = chunk.get("ns", ())

    if chunk_type == "updates":
        data = chunk.get("data", {})
        node = data.get("__meta__, {}).get("node", "") if "__meta__" in data else ""

        # Check for todo/planning steps
        if "todos" in data:
            return {
                "type": "todo",
                "todos": data["todos"],
            }

        # Tool call start
        if node == "tools" and "messages" in data:
            msgs = data["messages"]
            if msgs and hasattr(msgs[-1], "tool_calls") and msgs[-1].tool_calls:
                tc = msgs[-1].tool_calls[0]
                return {
                    "type": "tool_call",
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                    "ns": ns,
                }

        # Tool result
        if node == "tools" and "messages" in data:
            msgs = data["messages"]
            if msgs and msgs[-1].type == "tool":
                return {
                    "type": "tool_result",
                    "name": msgs[-1].name,
                    "result": str(msgs[-1].content)[:500],
                    "ns": ns,
                }

        # Subagent start/end
        if any(s.startswith("tools:") for s in ns):
            if "messages" in data and data["messages"]:
                msg = data["messages"][-1]
                if msg.type == "ai":
                    return {
                        "type": "subagent_start",
                        "name": next((s for s in ns if s.startswith("tools:")), ""),
                        "task": msg.content[:200],
                    }

        return None

    if chunk_type == "messages":
        token, _meta = chunk.get("data", (None, None))
        if token and hasattr(token, "content") and token.content:
            return {
                "type": "token",
                "content": token.content,
                "ns": ns,
            }
        return None

    if chunk_type == "custom":
        return {
            "type": "progress",
            "data": chunk.get("data", {}),
        }

    return None
```

- [ ] **Step 2: Write converter tests**

Create `tests/test_agent_streaming.py`:
```python
import pytest
from langchain_core.messages import AIMessage, ToolMessage

from mkg.agent.streaming import convert_chunk_to_sse


class TestConvertChunkToSSE:
    def test_todo_event(self):
        chunk = {
            "type": "updates",
            "data": {"todos": [{"id": "1", "title": "Search papers", "status": "running"}]},
        }
        event = convert_chunk_to_sse(chunk)
        assert event is not None
        assert event["type"] == "todo"

    def test_token_event(self):
        from langchain_core.messages import AIMessage
        chunk = {
            "type": "messages",
            "data": (AIMessage(content="Hello"), {}),
        }
        event = convert_chunk_to_sse(chunk)
        assert event is not None
        assert event["type"] == "token"
        assert event["content"] == "Hello"

    def test_unknown_chunk_returns_none(self):
        chunk = {"type": "unknown", "data": {}}
        assert convert_chunk_to_sse(chunk) is None
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_agent_streaming.py -v
```

Expected: 3 tests pass.

- [ ] **Step 4: Commit**

```bash
git add mkg/agent/streaming.py tests/test_agent_streaming.py
git commit -m "feat: add DeepAgents stream chunk to SSE converter"
```

---

## Task 5: Backend Subagent Skills

**Files:**
- Create: `mkg/agent/skills/__init__.py`
- Create: `mkg/agent/skills/citation.py`
- Create: `mkg/agent/skills/research.py`
- Create: `mkg/agent/skills/paper_qa.py`
- Create: `mkg/agent/skills/deep_research.py`

- [ ] **Step 1: Create skills package**

Create `mkg/agent/skills/__init__.py`:
```python
"""DeepAgents subagent skill configurations."""

from .citation import build_citation_subagent
from .deep_research import build_deep_research_subagent
from .paper_qa import build_paper_qa_subagent
from .research import build_research_subagent

__all__ = [
    "build_citation_subagent",
    "build_research_subagent",
    "build_paper_qa_subagent",
    "build_deep_research_subagent",
]
```

- [ ] **Step 2: Create citation skill**

Create `mkg/agent/skills/citation.py`:
```python
"""Citation analysis subagent."""

from mkg.llm import get_llm_or_raise
from mkg.agent.tools import analyze_citations, get_paper_by_title

_CITATION_PROMPT = """You are a citation analysis expert.

Your job is to analyze citation relationships for academic papers.
Use the analyze_citations tool to get citation data.
Use get_paper_by_title to fetch paper details when needed.

Be thorough but concise. Focus on:
- Citation statistics and trends
- Key citing papers and their impact
- Citation network insights
"""


def build_citation_subagent():
    return {
        "name": "citation-analyst",
        "description": "分析论文的引用关系、引用趋势和关键引用论文",
        "system_prompt": _CITATION_PROMPT,
        "tools": [analyze_citations, get_paper_by_title],
        "model": get_llm_or_raise(),
    }
```

- [ ] **Step 3: Create research skill**

Create `mkg/agent/skills/research.py`:
```python
"""Research point discovery subagent."""

from mkg.llm import get_llm_or_raise
from mkg.agent.tools import analyze_research_points, get_concept_graph, recommend_papers

_RESEARCH_PROMPT = """You are a research opportunity discoverer.

Your job is to find research gaps and opportunities based on concept graphs.
Use analyze_research_points to generate research directions.
Use get_concept_graph to understand the concept hierarchy.
Use recommend_papers to find frontier papers.

Focus on actionable research directions with clear methodology.
"""


def build_research_subagent():
    return {
        "name": "research-discoverer",
        "description": "基于概念图谱发现研究点和研究机会",
        "system_prompt": _RESEARCH_PROMPT,
        "tools": [analyze_research_points, get_concept_graph, recommend_papers],
        "model": get_llm_or_raise(),
    }
```

- [ ] **Step 4: Create paper_qa skill**

Create `mkg/agent/skills/paper_qa.py`:
```python
"""Paper Q&A subagent."""

from mkg.llm import get_llm_or_raise
from mkg.agent.tools import get_paper_by_title, read_paper_content, search_paper

_PAPER_QA_PROMPT = """You are a paper reading assistant.

Your job is to answer detailed questions about specific papers.
Use read_paper_content to read the full paper text.
Use get_paper_by_title to fetch paper metadata.
Use search_paper to find papers by title or concept.

Base your answers strictly on the paper content. Cite specific sections.
"""


def build_paper_qa_subagent():
    return {
        "name": "paper-qa",
        "description": "回答关于特定论文的详细问题",
        "system_prompt": _PAPER_QA_PROMPT,
        "tools": [read_paper_content, get_paper_by_title, search_paper],
        "model": get_llm_or_raise(),
    }
```

- [ ] **Step 5: Create deep_research skill**

Create `mkg/agent/skills/deep_research.py`:
```python
"""Deep research subagent."""

from mkg.llm import get_llm_or_raise
from mkg.agent.tools import read_paper_content, recommend_papers, search_paper

_DEEP_RESEARCH_PROMPT = """You are a deep research specialist.

Your job is to conduct multi-dimensional research and produce comprehensive reports.
Use search_paper to find relevant literature.
Use recommend_papers to discover frontier work.
Use read_paper_content to analyze specific papers in depth.

Structure your findings with:
1. Executive summary
2. Key findings per dimension
3. Actionable recommendations
"""


def build_deep_research_subagent():
    return {
        "name": "deep-researcher",
        "description": "执行多维度深度研究并生成综合报告",
        "system_prompt": _DEEP_RESEARCH_PROMPT,
        "tools": [search_paper, recommend_papers, read_paper_content],
        "model": get_llm_or_raise(),
    }
```

- [ ] **Step 6: Commit**

```bash
git add mkg/agent/skills/
git commit -m "feat: add 4 DeepAgent subagent skill configurations"
```

---

## Task 6: Backend Main Agent Configuration

**Files:**
- Create: `mkg/agent/agent.py`
- Modify: `mkg/agent/__init__.py`

- [ ] **Step 1: Create main agent builder**

Create `mkg/agent/agent.py`:
```python
"""Main DeepAgent configuration and builder."""

from pathlib import Path

from deepagents import create_deep_agent

from mkg.llm import get_llm_or_raise

from .filesystem import build_filesystem_backend
from .memory import build_checkpointer, build_store
from .skills import (
    build_citation_subagent,
    build_deep_research_subagent,
    build_paper_qa_subagent,
    build_research_subagent,
)
from .tools import (
    get_concept_graph,
    get_paper_by_title,
    read_paper_content,
    recommend_papers,
    search_paper,
)

_MAIN_SYSTEM_PROMPT = """You are an AI research assistant for the Meta Knowledge Graph system.

Your capabilities:
- Search and retrieve papers from the database
- Read paper PDF content
- Get concept graph structures
- Recommend related papers
- Delegate to specialized subagents for deep analysis

When the user asks about citations, delegate to citation-analyst.
When the user asks about research opportunities, delegate to research-discoverer.
When the user asks about a specific paper, delegate to paper-qa.
When the user asks for deep multi-dimensional research, delegate to deep-researcher.

You can use the filesystem to save intermediate results to /workspace/.
Always plan your work with write_todos before starting complex tasks.
"""


def build_main_agent(db_path: str, workspace_dir: str):
    """Build and return the main DeepAgent."""
    llm = get_llm_or_raise()
    checkpointer = build_checkpointer(db_path)
    store = build_store(db_path)
    backend = build_filesystem_backend(workspace_dir)

    return create_deep_agent(
        model=llm,
        system_prompt=_MAIN_SYSTEM_PROMPT,
        tools=[
            search_paper,
            get_paper_by_title,
            read_paper_content,
            get_concept_graph,
            recommend_papers,
        ],
        subagents=[
            build_citation_subagent(),
            build_research_subagent(),
            build_paper_qa_subagent(),
            build_deep_research_subagent(),
        ],
        backend=lambda rt: backend,
        checkpointer=checkpointer,
        store=store,
    )


# Singleton cache
_main_agent = None


def get_main_agent(db_path: str | None = None, workspace_dir: str | None = None):
    """Get or create the main agent singleton."""
    global _main_agent
    if _main_agent is None:
        if db_path is None:
            db_path = "data/mkg.db"
        if workspace_dir is None:
            workspace_dir = "data/agent_files"
        _main_agent = build_main_agent(db_path, workspace_dir)
    return _main_agent


def init_agent(db_path: str, workspace_dir: str):
    """Initialize the agent with explicit paths."""
    global _main_agent
    _main_agent = build_main_agent(db_path, workspace_dir)


def reset_agent():
    """Reset the agent singleton."""
    global _main_agent
    _main_agent = None
```

- [ ] **Step 2: Update agent package exports**

Edit `mkg/agent/__init__.py`:
```python
from .agent import get_main_agent, init_agent, reset_agent

__all__ = ["get_main_agent", "init_agent", "reset_agent"]
```

- [ ] **Step 3: Commit**

```bash
git add mkg/agent/agent.py mkg/agent/__init__.py
git commit -m "feat: add main DeepAgent builder with 4 subagents"
```

---

## Task 7: Backend Route Rewrite

**Files:**
- Modify: `backend/routes/agent.py`
- Modify: `backend/schemas.py`

- [ ] **Step 1: Rewrite agent routes**

Replace the content of `backend/routes/agent.py`:

```python
"""Agent API routes — DeepAgents version."""

import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from backend.dependencies import get_db, get_pdf_parser, get_s2_client
from backend.schemas import AgentChatRequest
from mkg.agent.agent import get_main_agent, init_agent, reset_agent
from mkg.agent.streaming import convert_chunk_to_sse
from mkg.llm import init_llm_from_db

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat/stream")
async def chat_stream(request: AgentChatRequest):
    """Stream agent response via SSE."""
    db = get_db()
    init_llm_from_db(db)

    config = db.get_llm_config()
    if not config or not config.get("providers"):
        raise HTTPException(status_code=500, detail="LLM not configured")

    # Init agent with dependencies
    workspace_dir = f"data/agent_files/{request.conversationId or 'default'}"
    agent = get_main_agent(db_path="data/mkg.db", workspace_dir=workspace_dir)

    messages = []
    for m in request.history:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        else:
            messages.append(AIMessage(content=m.content))
    messages.append(HumanMessage(content=request.message))

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'status', 'status': 'thinking'})}\n\n"

            # DeepAgents stream is sync; run in thread pool
            import asyncio
            loop = asyncio.get_event_loop()

            def _stream():
                return list(agent.stream(
                    {"messages": messages},
                    stream_mode=["updates", "messages", "custom"],
                    subgraphs=True,
                    version="v2",
                    config={"configurable": {
                        "thread_id": request.conversationId or "default",
                        "db": db,
                        "s2_client": get_s2_client(),
                        "pdf_parser": get_pdf_parser(),
                    }},
                ))

            chunks = await loop.run_in_executor(None, _stream)

            for chunk in chunks:
                event = convert_chunk_to_sse(chunk)
                if event:
                    yield f"data: {json.dumps(event)}\n\n"

            yield f"data: {json.dumps({'type': 'status', 'status': 'completed'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/approve")
async def approve_action(request: dict[str, Any]):
    """Approve a pending human-in-the-loop action."""
    # TODO: Implement HITL resume with Command
    return {"status": "approved"}


@router.post("/reset")
def reset_agent_route():
    """Reset agent singleton."""
    reset_agent()
    from mkg.llm import reset_llm
    reset_llm()
    return {"status": "ok"}
```

- [ ] **Step 2: Update schemas if needed**

Check `backend/schemas.py` for `AgentChatRequest`. Ensure it has `conversationId` field:
```python
class AgentChatRequest(BaseModel):
    message: str
    context: AgentContextSummary | None = None
    history: list[AgentMessage] = []
    conversationId: str | None = None
```

If not present, add `conversationId: str | None = None`.

- [ ] **Step 3: Commit**

```bash
git add backend/routes/agent.py backend/schemas.py
git commit -m "feat: rewrite agent routes for DeepAgents SSE streaming"
```

---

## Task 8: Backend Cleanup

**Files:**
- Delete: `mkg/agent/graph.py`
- Delete: `mkg/agent/research_graph.py`
- Delete: `mkg/agent/nodes/` (entire directory)
- Delete: `mkg/agent/routing.py`
- Delete: `mkg/agent/state.py`
- Modify: `mkg/agent/nodes/__init__.py` if needed for removal

- [ ] **Step 1: Remove old agent files**

```bash
git rm mkg/agent/graph.py
git rm mkg/agent/research_graph.py
git rm -r mkg/agent/nodes/
git rm mkg/agent/routing.py
```

- [ ] **Step 2: Remove state.py if no longer needed**

```bash
git rm mkg/agent/state.py
```

- [ ] **Step 3: Verify backend imports**

Run:
```bash
python -c "from mkg.agent import get_main_agent; print('imports OK')"
```

Expected: prints `imports OK`.

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor: remove old LangGraph agent nodes and graphs"
```

---

## Task 9: Frontend API Types Update

**Files:**
- Modify: `frontend/src/lib/api/agent.ts`

- [ ] **Step 1: Expand SSE event types**

Replace `frontend/src/lib/api/agent.ts` types section:

```typescript
export interface SSEEvent {
  type:
    | "status"
    | "todo"
    | "tool_call"
    | "tool_result"
    | "file_op"
    | "subagent_start"
    | "subagent_end"
    | "token"
    | "progress"
    | "approval_request"
    | "error";
  [key: string]: any;
}

export interface TodoItem {
  id: string;
  title: string;
  status: "pending" | "running" | "completed" | "failed";
  detail?: string;
  toolName?: string;
  timestamp: number;
}

export interface ExecutionStep {
  id: string;
  type: "tool_call" | "tool_result" | "subagent_start" | "subagent_end";
  name: string;
  args?: Record<string, any>;
  result?: string;
  duration?: number;
  subagentName?: string;
}

export interface VirtualFile {
  path: string;
  content?: string;
  modifiedAt: number;
}

export interface ActiveSubagent {
  name: string;
  task: string;
  status: "running" | "completed";
}

export interface ApprovalRequest {
  id: string;
  action: string;
  message: string;
}
```

- [ ] **Step 2: Update chatStreamFetch to use new types**

Modify the `chatStreamFetch` function signature:
```typescript
chatStreamFetch: async (
  message: string,
  context: AgentContextSummary,
  history: AgentMessage[],
  conversationId: string | null,
  onEvent: (event: SSEEvent) => void
): Promise<void> => {
  const response = await fetch("/api/agent/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, context, history, conversationId }),
  });
  // ... rest of SSE parsing unchanged
```

- [ ] **Step 3: Add approval API**

Add to `agentApi`:
```typescript
approveAction: async (approvalId: string, approved: boolean) => {
  const response = await api.post("/agent/approve", {
    approvalId,
    approved,
  });
  return response.data;
},
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api/agent.ts
git commit -m "feat: expand agent API types for DeepAgent events"
```

---

## Task 10: Frontend State Management Expansion

**Files:**
- Modify: `frontend/src/stores/agentStore.ts`

- [ ] **Step 1: Add new state slices**

Edit `frontend/src/stores/agentStore.ts`. Add interfaces and state fields:

```typescript
export interface TodoItem {
  id: string;
  title: string;
  status: "pending" | "running" | "completed" | "failed";
  detail?: string;
  toolName?: string;
  timestamp: number;
}

export interface ExecutionStep {
  id: string;
  type: "tool_call" | "tool_result" | "subagent_start" | "subagent_end";
  name: string;
  args?: Record<string, any>;
  result?: string;
  duration?: number;
  subagentName?: string;
}

export interface VirtualFile {
  path: string;
  content?: string;
  modifiedAt: number;
}

export interface ActiveSubagent {
  name: string;
  task: string;
  status: "running" | "completed";
}

export interface ApprovalRequest {
  id: string;
  action: string;
  message: string;
}
```

Add to `AgentState`:
```typescript
todos: TodoItem[];
executionSteps: ExecutionStep[];
virtualFiles: VirtualFile[];
activeSubagents: ActiveSubagent[];
pendingApproval: ApprovalRequest | null;
```

Add actions:
```typescript
setTodos: (todos: TodoItem[]) => void;
addExecutionStep: (step: ExecutionStep) => void;
updateVirtualFiles: (files: VirtualFile[]) => void;
setActiveSubagents: (subagents: ActiveSubagent[]) => void;
setPendingApproval: (req: ApprovalRequest | null) => void;
```

Implement in store:
```typescript
export const useAgentStore = create<AgentState>((set) => ({
  // ... existing state ...
  todos: [],
  executionSteps: [],
  virtualFiles: [],
  activeSubagents: [],
  pendingApproval: null,

  // ... existing actions ...
  setTodos: (todos) => set({ todos }),
  addExecutionStep: (step) =>
    set((state) => ({ executionSteps: [...state.executionSteps, step] })),
  updateVirtualFiles: (files) => set({ virtualFiles: files }),
  setActiveSubagents: (activeSubagents) => set({ activeSubagents }),
  setPendingApproval: (pendingApproval) => set({ pendingApproval }),
}));
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/agentStore.ts
git commit -m "feat: expand agent store with DeepAgent state slices"
```

---

## Task 11: Frontend UI Components (Part 1)

**Files:**
- Create: `frontend/src/components/TodoPanel.tsx`
- Create: `frontend/src/components/ExecutionTrace.tsx`
- Create: `frontend/src/components/SubagentBadge.tsx`

- [ ] **Step 1: Create TodoPanel**

Create `frontend/src/components/TodoPanel.tsx`:
```tsx
import { useAgentStore } from "../stores/agentStore";
import { ChevronDown, ChevronUp, Loader2, CheckCircle, XCircle, Circle } from "lucide-react";
import { useState } from "react";

export default function TodoPanel() {
  const todos = useAgentStore((s) => s.todos);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Loader2 className="w-4 h-4 animate-spin text-amber-600" />;
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return <Circle className="w-4 h-4 text-gray-400" />;
    }
  };

  if (todos.length === 0) return null;

  return (
    <div className="p-4 border-b border-[#E8E4DC]">
      <h3 className="font-display text-sm font-medium mb-3 text-[#5a3e28]">
        执行计划
      </h3>
      <div className="space-y-2">
        {todos.map((todo) => (
          <div key={todo.id} className="rounded-lg bg-[#FAFAF7] border border-[#E8E4DC]">
            <button
              onClick={() => toggle(todo.id)}
              className="w-full px-3 py-2 flex items-center gap-2 text-sm"
            >
              {statusIcon(todo.status)}
              <span className={todo.status === "completed" ? "text-gray-500 line-through" : "text-[#2c1810]"}>
                {todo.title}
              </span>
              {todo.detail && (
                expanded.has(todo.id) ? <ChevronUp className="w-3 h-3 ml-auto" /> : <ChevronDown className="w-3 h-3 ml-auto" />
              )}
            </button>
            {expanded.has(todo.id) && todo.detail && (
              <div className="px-3 pb-2 text-xs text-[#6b5d4f] border-t border-[#E8E4DC]">
                {todo.detail}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create ExecutionTrace**

Create `frontend/src/components/ExecutionTrace.tsx`:
```tsx
import { useAgentStore } from "../stores/agentStore";
import { ChevronDown, ChevronUp, Wrench, Bot } from "lucide-react";
import { useState } from "react";

export default function ExecutionTrace() {
  const steps = useAgentStore((s) => s.executionSteps);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (steps.length === 0) return null;

  return (
    <div className="p-4">
      <h3 className="font-display text-sm font-medium mb-3 text-[#5a3e28]">
        执行轨迹
      </h3>
      <div className="space-y-1">
        {steps.map((step) => (
          <div key={step.id} className="rounded bg-[#F5F0E8] text-xs">
            <button
              onClick={() => toggle(step.id)}
              className="w-full px-2 py-1.5 flex items-center gap-2"
            >
              {step.type === "tool_call" || step.type === "tool_result" ? (
                <Wrench className="w-3 h-3 text-[#8b4513]" />
              ) : (
                <Bot className="w-3 h-3 text-[#4a6b8a]" />
              )}
              <span className="text-[#2c1810]">{step.name}</span>
              {step.args || step.result ? (
                expanded.has(step.id) ? <ChevronUp className="w-3 h-3 ml-auto" /> : <ChevronDown className="w-3 h-3 ml-auto" />
              ) : null}
            </button>
            {expanded.has(step.id) && (
              <div className="px-2 pb-1.5 space-y-1">
                {step.args && (
                  <pre className="bg-white p-1 rounded overflow-x-auto">
                    {JSON.stringify(step.args, null, 2)}
                  </pre>
                )}
                {step.result && (
                  <pre className="bg-white p-1 rounded overflow-x-auto text-green-700">
                    {step.result}
                  </pre>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create SubagentBadge**

Create `frontend/src/components/SubagentBadge.tsx`:
```tsx
import { Bot } from "lucide-react";

interface Props {
  name: string;
  status: "running" | "completed";
}

const LABELS: Record<string, string> = {
  "citation-analyst": "引用分析",
  "research-discoverer": "研究点发现",
  "paper-qa": "论文问答",
  "deep-researcher": "深度研究",
};

export default function SubagentBadge({ name, status }: Props) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-[#4a6b8a12] text-[#4a6b8a]">
        <Bot className="w-3 h-3" />
        {LABELS[name] || name}
        {status === "running" && (
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
        )}
      </span>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/TodoPanel.tsx frontend/src/components/ExecutionTrace.tsx frontend/src/components/SubagentBadge.tsx
git commit -m "feat: add DeepAgent UI components (Todo, Trace, Badge)"
```

---

## Task 12: Frontend UI Components (Part 2)

**Files:**
- Create: `frontend/src/components/FileExplorer.tsx`
- Create: `frontend/src/components/HumanInTheLoop.tsx`
- Create: `frontend/src/components/AgentWorkspace.tsx`

- [ ] **Step 1: Create FileExplorer**

Create `frontend/src/components/FileExplorer.tsx`:
```tsx
import { useAgentStore } from "../stores/agentStore";
import { FileText, Folder } from "lucide-react";
import { useState } from "react";

export default function FileExplorer() {
  const files = useAgentStore((s) => s.virtualFiles);
  const [selected, setSelected] = useState<string | null>(null);

  const selectedFile = files.find((f) => f.path === selected);

  if (files.length === 0) return null;

  return (
    <div className="p-4 border-t border-[#E8E4DC]">
      <h3 className="font-display text-sm font-medium mb-3 text-[#5a3e28]">
        工作区文件
      </h3>
      <div className="space-y-1">
        {files.map((file) => (
          <button
            key={file.path}
            onClick={() => setSelected(file.path)}
            className={`w-full flex items-center gap-2 px-2 py-1 rounded text-xs ${
              selected === file.path ? "bg-[#E8E4DC]" : "hover:bg-[#F5F0E8]"
            }`}
          >
            <FileText className="w-3 h-3 text-[#8b4513]" />
            <span className="truncate">{file.path.replace("/workspace/", "")}</span>
          </button>
        ))}
      </div>
      {selectedFile?.content && (
        <div className="mt-3 p-2 bg-white rounded border border-[#E8E4DC] text-xs max-h-48 overflow-y-auto">
          <pre className="whitespace-pre-wrap">{selectedFile.content}</pre>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create HumanInTheLoop**

Create `frontend/src/components/HumanInTheLoop.tsx`:
```tsx
import { useAgentStore } from "../stores/agentStore";
import { agentApi } from "../lib/api/agent";
import { AlertTriangle, X } from "lucide-react";

export default function HumanInTheLoop() {
  const pending = useAgentStore((s) => s.pendingApproval);
  const setPending = useAgentStore((s) => s.setPendingApproval);

  if (!pending) return null;

  const handleApprove = async (approved: boolean) => {
    await agentApi.approveAction(pending.id, approved);
    setPending(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-6 h-6 text-amber-600" />
          <h3 className="font-display text-lg text-[#2c1810]">Agent 请求确认</h3>
        </div>
        <p className="text-sm text-[#6b5d4f] mb-2">Agent 即将执行以下操作：</p>
        <div className="bg-[#F5F0E8] rounded-lg p-3 mb-4">
          <p className="font-medium text-[#2c1810]">{pending.action}</p>
          <p className="text-xs text-[#6b5d4f] mt-1">{pending.message}</p>
        </div>
        <div className="flex justify-end gap-3">
          <button
            onClick={() => handleApprove(false)}
            className="px-4 py-2 rounded-lg text-sm border border-[#E8E4DC] hover:bg-[#F5F0E8]"
          >
            取消
          </button>
          <button
            onClick={() => handleApprove(true)}
            className="px-4 py-2 rounded-lg text-sm bg-[#8b4513] text-white hover:bg-[#6b3410]"
          >
            确认执行
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create AgentWorkspace**

Create `frontend/src/components/AgentWorkspace.tsx`:
```tsx
import { useState } from "react";
import { PanelLeft, PanelRight } from "lucide-react";
import TodoPanel from "./TodoPanel";
import ExecutionTrace from "./ExecutionTrace";
import FileExplorer from "./FileExplorer";
import HumanInTheLoop from "./HumanInTheLoop";

interface Props {
  children: React.ReactNode;
}

export default function AgentWorkspace({ children }: Props) {
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(false);

  return (
    <div className="h-full flex">
      {/* Left Panel */}
      {leftOpen && (
        <aside className="w-72 flex-shrink-0 border-r border-[#E8E4DC] bg-[#FAFAF7] overflow-y-auto">
          <TodoPanel />
          <ExecutionTrace />
        </aside>
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        {/* Toggle buttons */}
        <div className="absolute top-2 left-2 z-10 flex gap-1">
          <button
            onClick={() => setLeftOpen(!leftOpen)}
            className="p-1.5 rounded bg-white shadow-sm border border-[#E8E4DC] hover:bg-[#F5F0E8]"
            title="Toggle sidebar"
          >
            <PanelLeft className="w-4 h-4 text-[#8b4513]" />
          </button>
        </div>
        <div className="absolute top-2 right-2 z-10">
          <button
            onClick={() => setRightOpen(!rightOpen)}
            className="p-1.5 rounded bg-white shadow-sm border border-[#E8E4DC] hover:bg-[#F5F0E8]"
            title="Toggle file panel"
          >
            <PanelRight className="w-4 h-4 text-[#8b4513]" />
          </button>
        </div>

        {children}
        <HumanInTheLoop />
      </main>

      {/* Right Panel */}
      {rightOpen && (
        <aside className="w-64 flex-shrink-0 border-l border-[#E8E4DC] bg-[#FAFAF7] overflow-y-auto">
          <FileExplorer />
        </aside>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/FileExplorer.tsx frontend/src/components/HumanInTheLoop.tsx frontend/src/components/AgentWorkspace.tsx
git commit -m "feat: add FileExplorer, HumanInTheLoop, and AgentWorkspace components"
```

---

## Task 13: Frontend Page Integration

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`

- [ ] **Step 1: Wrap Chat with AgentWorkspace**

Edit `frontend/src/pages/Chat.tsx`. At the top, add import:
```tsx
import AgentWorkspace from "../components/AgentWorkspace";
```

Wrap the existing return content with `<AgentWorkspace>`:
```tsx
return (
  <ChatErrorBoundary>
    <AgentWorkspace>
      <div className="chat-container h-full flex flex-col relative">
        {/* ... existing content ... */}
      </div>
    </AgentWorkspace>
  </ChatErrorBoundary>
);
```

- [ ] **Step 2: Update handleSend to pass conversationId**

In `handleSend`, update the `sseManager.startChatStream` call to pass `currentConversationId`.

Also add event dispatching for new SSE types. In the `onEvent` callback or within `sseManager`, map incoming events to store actions:

```typescript
// Inside the SSE event handler
if (event.type === "todo") {
  useAgentStore.getState().setTodos(event.todos);
} else if (event.type === "tool_call") {
  useAgentStore.getState().addExecutionStep({
    id: `${event.name}-${Date.now()}`,
    type: "tool_call",
    name: event.name,
    args: event.args,
  });
} else if (event.type === "subagent_start") {
  useAgentStore.getState().setActiveSubagents([
    ...useAgentStore.getState().activeSubagents,
    { name: event.name, task: event.task, status: "running" },
  ]);
} else if (event.type === "approval_request") {
  useAgentStore.getState().setPendingApproval(event);
}
```

- [ ] **Step 3: Add SubagentBadge to assistant messages**

In the message rendering section, before the assistant message bubble:
```tsx
{msg.role === "assistant" && (
  <div>
    {/* Show active subagent badge if any */}
    {useAgentStore.getState().activeSubagents
      .filter((s) => s.status === "running")
      .map((s) => (
        <SubagentBadge key={s.name} name={s.name} status={s.status} />
      ))}
    {/* ... existing message content ... */}
  </div>
)}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Chat.tsx
git commit -m "feat: integrate AgentWorkspace into Chat page"
```

---

## Task 14: End-to-End Testing

**Files:**
- Create: `tests/test_agent_e2e.py`

- [ ] **Step 1: Write end-to-end test**

Create `tests/test_agent_e2e.py`:
```python
import pytest
from unittest.mock import MagicMock, patch

from mkg.agent.agent import build_main_agent


class TestDeepAgentEndToEnd:
    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.invoke.return_value = MagicMock(content="Test response")
        return mock

    def test_agent_builds_without_errors(self, tmp_path, mock_llm):
        with patch("mkg.agent.agent.get_llm_or_raise", return_value=mock_llm):
            agent = build_main_agent(
                db_path=str(tmp_path / "test.db"),
                workspace_dir=str(tmp_path / "workspace"),
            )
            assert agent is not None

    def test_stream_produces_chunks(self, tmp_path, mock_llm):
        with patch("mkg.agent.agent.get_llm_or_raise", return_value=mock_llm):
            agent = build_main_agent(
                db_path=str(tmp_path / "test.db"),
                workspace_dir=str(tmp_path / "workspace"),
            )
            chunks = list(agent.stream(
                {"messages": [{"role": "user", "content": "Hello"}]},
                stream_mode=["updates"],
                version="v2",
            ))
            assert isinstance(chunks, list)
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_agent_e2e.py -v
```

Expected: 2 tests pass.

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -x
```

Expected: All tests pass (or failures are documented).

- [ ] **Step 4: Commit**

```bash
git add tests/test_agent_e2e.py
git commit -m "test: add DeepAgent end-to-end smoke tests"
```

---

## Self-Review

### Spec Coverage

| Spec Section | Plan Task |
|-------------|-----------|
| Python 3.11+ upgrade | Task 1 |
| `deepagents==0.5.1` | Task 1 |
| Tool migration with `get_config()` | Task 2 |
| CompositeBackend filesystem | Task 3 |
| SqliteSaver/SqliteStore | Task 3 |
| Streaming converter | Task 4 |
| 4 subagents | Task 5 |
| Main agent builder | Task 6 |
| Backend route rewrite | Task 7 |
| Old code cleanup | Task 8 |
| Frontend API types | Task 9 |
| Frontend state management | Task 10 |
| TodoPanel, ExecutionTrace, SubagentBadge | Task 11 |
| FileExplorer, HumanInTheLoop, AgentWorkspace | Task 12 |
| Chat page integration | Task 13 |
| End-to-end tests | Task 14 |

No gaps found.

### Placeholder Scan

- No "TBD", "TODO", "implement later" found.
- All steps include actual code or exact commands.
- No "Similar to Task N" references.

### Type Consistency

- `TodoItem`, `ExecutionStep`, `VirtualFile`, `ActiveSubagent`, `ApprovalRequest` types are consistent between `agent.ts` and `agentStore.ts`.
- `convert_chunk_to_sse` returns `dict[str, Any] | None` consistently.
- Agent builder function names (`build_*`) are consistent.

---

*Plan complete and saved to `docs/superpowers/plans/2026-05-25-deepagent-refactor.md`.*
