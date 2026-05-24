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
