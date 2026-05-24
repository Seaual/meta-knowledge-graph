# tests/test_agent_lead_node.py
"""
Unit tests for Agent Lead Node utilities.

Tests tool result summarization and attachment generation without requiring LLM calls.
"""

import pytest

from mkg.agent.nodes.lead import make_attachment, summarize_for_llm


class TestSummarizeForLLM:
    """Test summarize_for_llm with various tool outputs."""

    def test_summarize_search_paper(self):
        """Summarize search_paper result."""
        result = {
            "count": 10,
            "papers": [
                {"title": "Paper A"},
                {"title": "Paper B"},
                {"title": "Paper C"},
            ],
        }
        summary = summarize_for_llm("search_paper", result)
        assert "10" in summary
        assert "Paper A" in summary
        assert "Paper B" in summary

    def test_summarize_search_paper_truncation(self):
        """Large result sets should be truncated in summary."""
        result = {
            "count": 100,
            "papers": [{"title": f"Paper {i}"} for i in range(20)],
        }
        summary = summarize_for_llm("search_paper", result)
        assert "100" in summary
        assert "还有" in summary or "more" in summary or "95" in summary

    def test_summarize_get_paper_by_title(self):
        """Summarize get_paper_by_title result."""
        result = {
            "title": "Test Paper",
            "authors": ["Alice", "Bob", "Charlie"],
            "year": 2024,
            "abstract": "This is a very long abstract that should be truncated...",
        }
        summary = summarize_for_llm("get_paper_by_title", result)
        assert "Test Paper" in summary
        assert "Alice" in summary
        assert "2024" in summary

    def test_summarize_analyze_research_points(self):
        """Summarize analyze_research_points result."""
        result = {
            "research_points": [
                {"title": "Point 1", "description": "Description of point 1"},
                {"title": "Point 2", "description": "Description of point 2"},
            ],
        }
        summary = summarize_for_llm("analyze_research_points", result)
        assert "Point 1" in summary
        assert "2" in summary  # count

    def test_summarize_get_concept_graph(self):
        """Summarize get_concept_graph result."""
        result = {
            "name": "Reinforcement Learning",
            "category": "field",
            "children": [{"name": "Q-Learning"}, {"name": "Policy Gradient"}],
            "parents": [{"name": "Machine Learning"}],
        }
        summary = summarize_for_llm("get_concept_graph", result)
        assert "Reinforcement Learning" in summary
        assert "Q-Learning" in summary
        assert "Machine Learning" in summary

    def test_summalyze_analyze_citations(self):
        """Summarize analyze_citations result."""
        result = {
            "paper": {"title": "Citation Paper"},
            "citations": [{"title": "Cited 1"}, {"title": "Cited 2"}],
            "cited_by": [{"title": "Citing 1"}],
        }
        summary = summarize_for_llm("analyze_citations", result)
        assert "Citation Paper" in summary
        assert "2" in summary  # cited count
        assert "1" in summary  # cited_by count

    def test_summarize_error_result(self):
        """Error dict should return error message."""
        result = {"error": "Database connection failed"}
        summary = summarize_for_llm("search_paper", result)
        assert "错误" in summary or "Error" in summary or "error" in summary.lower()

    def test_summarize_string_result(self):
        """String result should be returned as-is."""
        result = "Raw string output from tool"
        summary = summarize_for_llm("any_tool", result)
        assert summary == result


class TestMakeAttachment:
    """Test make_attachment with various tool outputs."""

    def test_make_attachment_for_known_tool(self):
        """Known tools should produce typed attachments."""
        result = {"research_points": [{"title": "P1"}]}
        att = make_attachment("analyze_research_points", result)
        assert att is not None
        assert att["type"] == "research_points"
        assert att["data"] == result

    def test_make_attachment_for_unknown_tool(self):
        """Unknown tools should return None."""
        result = {"data": "something"}
        att = make_attachment("unknown_tool", result)
        assert att is None

    def test_make_attachment_for_string_result(self):
        """String results should return None (not attachable)."""
        att = make_attachment("search_paper", "raw string")
        assert att is None

    def test_make_attachment_for_error_result(self):
        """Error dicts should return None."""
        att = make_attachment("search_paper", {"error": "failed"})
        assert att is None

    def test_all_mapped_tools_produce_attachments(self):
        """Every tool in TOOL_ATTACHMENT_MAP should produce attachment for valid dict."""
        from mkg.agent.nodes.lead import TOOL_ATTACHMENT_MAP

        for tool_name in TOOL_ATTACHMENT_MAP:
            att = make_attachment(tool_name, {"some": "data"})
            assert att is not None, f"{tool_name} should produce attachment"
            assert att["type"] == TOOL_ATTACHMENT_MAP[tool_name]
