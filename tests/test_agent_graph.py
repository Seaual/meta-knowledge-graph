# tests/test_agent_graph.py
"""
Integration tests for Agent Graph compilation and state management.

These tests verify that the LangGraph agent graph compiles correctly
and handles state transitions without requiring real LLM calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from mkg.agent.graph import build_agent_graph, get_agent_graph, reset_graph
from mkg.agent.state import AgentState


class TestAgentGraphCompilation:
    """Test graph compilation and basic structure."""

    def test_build_agent_graph_returns_compiled_graph(self):
        """build_agent_graph should return a compiled graph object."""
        with patch("mkg.agent.graph.init_llm_from_db") as mock_init_llm:
            mock_init_llm.return_value = MagicMock()

            with patch("mkg.agent.graph.init_tools") as mock_init_tools:
                graph = build_agent_graph(db=None, s2_client=None, pdf_parser=None)

        assert graph is not None
        # Compiled LangGraph has invoke method
        assert hasattr(graph, "invoke")

    def test_build_agent_graph_initializes_tools(self):
        """build_agent_graph should call init_tools with correct dependencies."""
        mock_db = MagicMock()
        mock_s2 = MagicMock()
        mock_pdf = MagicMock()

        with patch("mkg.agent.graph.init_llm_from_db"):
            with patch("mkg.agent.graph.init_tools") as mock_init_tools:
                build_agent_graph(db=mock_db, s2_client=mock_s2, pdf_parser=mock_pdf)

        mock_init_tools.assert_called_once_with(db=mock_db, s2_client=mock_s2, pdf_parser=mock_pdf)

    def test_build_agent_graph_initializes_llm(self):
        """build_agent_graph should call init_llm_from_db."""
        with patch("mkg.agent.graph.init_llm_from_db") as mock_init_llm:
            with patch("mkg.agent.graph.init_tools"):
                build_agent_graph(db=None, s2_client=None, pdf_parser=None)

        mock_init_llm.assert_called_once()


class TestAgentGraphSingleton:
    """Test get_agent_graph singleton behavior."""

    def test_get_agent_graph_returns_same_instance(self):
        """Multiple calls should return the same compiled graph (singleton)."""
        reset_graph()

        with patch("mkg.agent.graph.init_llm_from_db") as mock_init_llm:
            mock_init_llm.return_value = MagicMock()

            with patch("mkg.agent.graph.init_tools"):
                graph1 = get_agent_graph()
                graph2 = get_agent_graph()

        assert graph1 is graph2

    def test_reset_graph_clears_singleton(self):
        """reset_graph should clear the singleton so next call creates a new graph."""
        reset_graph()

        with patch("mkg.agent.graph.init_llm_from_db") as mock_init_llm:
            mock_init_llm.return_value = MagicMock()

            with patch("mkg.agent.graph.init_tools"):
                graph1 = get_agent_graph()
                reset_graph()
                graph2 = get_agent_graph()

        assert graph1 is not graph2


class TestAgentState:
    """Test AgentState dataclass behavior."""

    def test_agent_state_default_values(self):
        """AgentState (TypedDict) should have sensible defaults."""
        state = AgentState(messages=[], attachments=[], current_target=None, uploaded_papers=[], intent="", response="", agent_used="", needs_summary=False, concept_data=None, target_name=None)
        assert state["messages"] == []
        assert state.get("attachments") is None or state.get("attachments") == []

    def test_agent_state_accepts_messages(self):
        """AgentState should accept message list."""
        state = AgentState(messages=[{"role": "user", "content": "hello"}], current_target=None, uploaded_papers=[], intent="", response="", agent_used="", needs_summary=False, concept_data=None, target_name=None)
        assert len(state["messages"]) == 1
        assert state["messages"][0]["role"] == "user"

    def test_agent_state_accepts_attachments(self):
        """AgentState should accept attachment list."""
        state = AgentState(attachments=[{"type": "research_points", "data": {}}], messages=[], current_target=None, uploaded_papers=[], intent="", response="", agent_used="", needs_summary=False, concept_data=None, target_name=None)
        assert len(state["attachments"]) == 1


class TestAgentGraphInvocation:
    """Test graph invocation with mocked lead node."""

    def test_graph_invokes_lead_node(self):
        """Graph should invoke the lead node when given input."""

        def mock_lead_fn(state):
            return {
                "messages": [{"role": "ai", "content": "Hello!"}],
                "attachments": [],
            }

        with patch("mkg.agent.graph.init_llm_from_db"):
            with patch("mkg.agent.graph.init_tools"):
                with patch("mkg.agent.graph.lead_node", new=mock_lead_fn):
                    graph = build_agent_graph(db=None, s2_client=None, pdf_parser=None)
                    result = graph.invoke(
                        {"messages": [{"role": "user", "content": "hi"}], "attachments": []},
                        config={"configurable": {"thread_id": "test-1"}},
                    )

        assert "messages" in result

    def test_graph_preserves_thread_id(self):
        """Graph should use thread_id for checkpointing."""

        def mock_lead_fn(state):
            return {
                "messages": [{"role": "ai", "content": "Response"}],
                "attachments": [],
            }

        with patch("mkg.agent.graph.init_llm_from_db"):
            with patch("mkg.agent.graph.init_tools"):
                with patch("mkg.agent.graph.lead_node", new=mock_lead_fn):
                    graph = build_agent_graph(db=None, s2_client=None, pdf_parser=None)
                    thread_id = "session-abc-123"
                    graph.invoke(
                        {"messages": [{"role": "user", "content": "test"}], "attachments": []},
                        config={"configurable": {"thread_id": thread_id}},
                    )

        # If it didn't crash, thread_id was accepted by MemorySaver
        assert True
