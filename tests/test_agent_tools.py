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
        mock_db.get_papers_by_status.return_value = [
            {"title": "Test Paper", "abstract": "test", "authors": ["A"]}
        ]
        mock_config = {"configurable": {"db": mock_db}}
        monkeypatch.setattr(
            "mkg.agent.tools.get_config", lambda: mock_config
        )
        result = search_paper("test")
        assert "papers" in result
        assert result["count"] >= 1
        assert result["papers"][0]["title"] == "Test Paper"

    def test_search_paper_returns_error_when_no_db(self, monkeypatch):
        monkeypatch.setattr("mkg.agent.tools._db", None)
        monkeypatch.setattr(
            "mkg.agent.tools.get_config", lambda: {"configurable": {}}
        )
        result = search_paper("test")
        assert "error" in result
