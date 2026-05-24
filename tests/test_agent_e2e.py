import sys
from contextlib import contextmanager
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.language_models.chat_models import BaseChatModel

from mkg.agent.agent import build_main_agent


class TestDeepAgentEndToEnd:
    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock(spec=BaseChatModel)
        mock.invoke.return_value = MagicMock(content="Test response")
        mock.profile = None
        mock.bind_tools = MagicMock(return_value=mock)
        return mock

    @contextmanager
    def _patch_llm(self, mock_llm):
        """Patch get_llm_or_raise in all namespaces that import it."""
        targets = [
            "mkg.llm.get_llm_or_raise",
            "mkg.agent.agent.get_llm_or_raise",
            "mkg.agent.skills.citation.get_llm_or_raise",
            "mkg.agent.skills.research.get_llm_or_raise",
            "mkg.agent.skills.paper_qa.get_llm_or_raise",
            "mkg.agent.skills.deep_research.get_llm_or_raise",
        ]
        patches = []
        try:
            for target in targets:
                try:
                    p = patch(target, return_value=mock_llm)
                    p.start()
                    patches.append(p)
                except Exception:
                    pass
            yield
        finally:
            for p in patches:
                try:
                    p.stop()
                except Exception:
                    pass

    def test_agent_builds_without_errors(self, tmp_path, mock_llm):
        with self._patch_llm(mock_llm):
            agent = build_main_agent(
                db_path=str(tmp_path / "test.db"),
                workspace_dir=str(tmp_path / "workspace"),
            )
        assert agent is not None

    def test_agent_has_stream_method(self, tmp_path, mock_llm):
        with self._patch_llm(mock_llm):
            agent = build_main_agent(
                db_path=str(tmp_path / "test.db"),
                workspace_dir=str(tmp_path / "workspace"),
            )
        assert hasattr(agent, "stream")
        assert callable(agent.stream)
