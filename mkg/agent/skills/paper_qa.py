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
