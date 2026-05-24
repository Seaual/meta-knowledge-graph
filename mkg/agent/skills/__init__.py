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
