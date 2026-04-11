"""
ConceptRepository Neo4j 同步行为测试
"""
from unittest.mock import MagicMock

import pytest

from mkg.repositories.concept_repo import ConceptRepository


@pytest.fixture
def concept_repo(test_db):
    return ConceptRepository(test_db)


def test_add_concept_calls_neo4j_sync(concept_repo, test_db):
    """添加概念时应调用 Neo4jStore.sync_concept"""
    mock_store = MagicMock()
    test_db._neo4j_store = mock_store

    concept_repo.add({"id": "test-concept", "text": "Test Concept", "category": "field"})

    mock_store.sync_concept.assert_called_once()
    call_args = mock_store.sync_concept.call_args[0][0]
    assert call_args["id"] == "test-concept"
    assert call_args["text"] == "Test Concept"


def test_add_relation_calls_neo4j_sync(concept_repo, test_db):
    """添加关系时应调用 Neo4jStore.sync_relation"""
    mock_store = MagicMock()
    test_db._neo4j_store = mock_store

    # 先添加两个概念
    concept_repo.add({"id": "parent", "text": "Parent", "category": "field"})
    concept_repo.add({"id": "child", "text": "Child", "category": "direction"})

    concept_repo.add_relation("parent", "child")

    mock_store.sync_relation.assert_called_once_with("parent", "child", "parent-child")


def test_no_neo4j_when_disabled(concept_repo, test_db):
    """Neo4j 未连接时不影响 SQLite 写入"""
    test_db._neo4j_store = None

    concept_repo.add({"id": "solo", "text": "Solo Concept", "category": "method"})

    result = concept_repo.get("solo")
    assert result is not None
    assert result["text"] == "Solo Concept"
