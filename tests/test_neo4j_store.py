"""
Neo4jStore 单元测试（mock driver）
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from mkg.neo4j_store import Neo4jStore


@pytest.fixture
def mock_neo4j():
    """创建 mock 的 Neo4jStore"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.driver = MagicMock()
    store.connected = True
    yield store


def test_sync_concept_when_connected(mock_neo4j):
    """已连接时 sync_concept 应成功"""
    mock_neo4j.sync_concept({
        "id": "test-concept",
        "text": "Test Concept",
        "text_en": "Test",
        "text_zh": "测试",
        "category": "field",
        "paper_count": 5,
    })
    # 验证 driver.session 被调用
    mock_neo4j.driver.session.assert_called()


def test_sync_concept_when_not_connected():
    """未连接时 sync_concept 应返回 False"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.sync_concept({"id": "test", "text": "Test"})
    assert result is False


def test_sync_relation_when_connected(mock_neo4j):
    """已连接时 sync_relation 应成功"""
    mock_neo4j.sync_relation("parent", "child")
    mock_neo4j.driver.session.assert_called()


def test_sync_relation_when_not_connected():
    """未连接时 sync_relation 应返回 False"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.sync_relation("parent", "child")
    assert result is False


def test_get_tree_returns_empty_when_not_connected():
    """未连接时 get_tree 应返回空"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_tree()
    assert result == {}


def test_get_children_returns_empty_when_not_connected():
    """未连接时 get_children 应返回空列表"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_children("some-id")
    assert result == []


def test_get_parents_returns_empty_when_not_connected():
    """未连接时 get_parents 应返回空列表"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_parents("some-id")
    assert result == []


def test_get_root_concepts_returns_empty_when_not_connected():
    """未连接时 get_root_concepts 应返回空列表"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_root_concepts()
    assert result == []


def test_get_all_concepts_returns_empty_when_not_connected():
    """未连接时 get_all_concepts 应返回空列表"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_all_concepts()
    assert result == []


def test_get_graph_data_returns_empty_when_not_connected():
    """未连接时 get_graph_data 应返回空 nodes/edges"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_graph_data()
    assert result == {"nodes": [], "edges": []}


def test_get_stats_returns_empty_when_not_connected():
    """未连接时 get_stats 应返回空 dict"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_stats()
    assert result == {}


def test_update_paper_count_when_not_connected():
    """未连接时 update_paper_count 应返回 False"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.update_paper_count("test-id", 10)
    assert result is False


def test_search_concepts_when_not_connected():
    """未连接时 search_concepts 应返回空列表"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.search_concepts("test")
    assert result == []


def test_close_sets_connected_false(mock_neo4j):
    """close 应设置 connected 为 False"""
    assert mock_neo4j.connected is True
    mock_neo4j.close()
    assert mock_neo4j.connected is False


def test_sync_all_from_sqlite_returns_error_when_not_connected():
    """未连接时 sync_all_from_sqlite 应返回错误"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.sync_all_from_sqlite(MagicMock())
    assert result["concepts_synced"] == 0
    assert result["relations_synced"] == 0
    assert "error" in result
