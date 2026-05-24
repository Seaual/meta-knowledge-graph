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
