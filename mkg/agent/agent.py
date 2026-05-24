"""Main DeepAgent configuration and builder."""

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
