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
