"""
Agent Memory 模块测试
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from mkg.database import Database
from mkg.memory import AgentMemory


@pytest.fixture
def test_db():
    db = Database(":memory:")
    db.connect()
    db.conn.execute("PRAGMA foreign_keys=OFF")
    yield db
    db.close()


def test_user_preferences_table_exists(test_db):
    """user_preferences 表应存在"""
    cursor = test_db.execute_read("SELECT name FROM sqlite_master WHERE type='table' AND name='user_preferences'")
    assert cursor.fetchone() is not None


def test_conversation_context_table_exists(test_db):
    """conversation_context 表应存在"""
    cursor = test_db.execute_read("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_context'")
    assert cursor.fetchone() is not None


# ========== UserPreferences 测试 ==========


@pytest.fixture
def memory(test_db):
    return AgentMemory(test_db)


def test_preferences_set_and_get(memory):
    """设置和获取偏好"""
    memory.preferences.set("focus_areas", ["AI", "ML"])
    result = memory.preferences.get("focus_areas")
    assert result == ["AI", "ML"]


def test_preferences_get_nonexistent(memory):
    """获取不存在的偏好应返回 None"""
    assert memory.preferences.get("nonexistent") is None


def test_preferences_delete(memory):
    """删除偏好"""
    memory.preferences.set("test_key", "test_value")
    memory.preferences.delete("test_key")
    assert memory.preferences.get("test_key") is None


def test_preferences_get_all(memory):
    """获取所有偏好"""
    memory.preferences.set("key1", "value1")
    memory.preferences.set("key2", ["a", "b"])
    all_prefs = memory.preferences.get_all()
    assert "key1" in all_prefs
    assert all_prefs["key1"] == "value1"
    assert all_prefs["key2"] == ["a", "b"]


# ========== ConversationContext 测试 ==========


def test_conversation_context_get_empty(memory):
    """不存在的对话上下文应返回 None"""
    result = memory.context.get("nonexistent-conv")
    assert result is None


def test_conversation_context_save_and_get(memory):
    """保存和获取对话上下文"""
    conv_id = "test-conv-1"
    memory.context._save(
        conv_id=conv_id,
        summary="Test summary",
        key_concepts=["concept1", "concept2"],
        research_interests=["AI", "ML"],
    )
    result = memory.context.get(conv_id)
    assert result is not None
    assert result["summary"] == "Test summary"
    assert result["key_concepts"] == ["concept1", "concept2"]
    assert result["research_interests"] == ["AI", "ML"]


def test_conversation_context_update_interests(memory):
    """更新研究兴趣"""
    conv_id = "test-conv-2"
    memory.context._save(conv_id, "summary", [], [])
    memory.context.update_interests(conv_id, ["NLP", "Transformers"])
    result = memory.context.get(conv_id)
    assert result["research_interests"] == ["NLP", "Transformers"]


# ========== ResearchMemory 测试 ==========


def test_research_memory_add(memory):
    """添加研究记忆"""
    mem_id = memory.research.add(
        title="Transformer attention mechanism",
        content="Multi-head attention improves representation",
        memory_type="discovery",
        tags=["transformer", "attention"],
        concept_ids=["transformer", "attention"],
        paper_doi="10.1234/test",
        source_section="abstract",
    )
    assert mem_id is not None


def test_research_memory_search_by_tags(memory):
    """按标签搜索记忆"""
    memory.research.add(
        title="Test memory 1",
        content="content",
        memory_type="discovery",
        tags=["transformer", "attention"],
        paper_doi="10.1234/test1",
    )
    memory.research.add(
        title="Test memory 2",
        content="content",
        memory_type="method",
        tags=["CNN", "vision"],
        paper_doi="10.1234/test2",
    )
    results = memory.research.search_by_tags(["transformer"])
    assert len(results) == 1
    assert "Test memory 1" in results[0]["title"]


def test_research_memory_search_by_concept(memory):
    """按概念搜索记忆"""
    memory.research.add(
        title="Concept memory",
        content="content",
        memory_type="discovery",
        tags=["test"],
        concept_ids=["concept-a", "concept-b"],
        paper_doi="10.1234/test",
    )
    results = memory.research.search_by_concept("concept-a")
    assert len(results) == 1
    assert "Concept memory" in results[0]["title"]


def test_research_memory_search_by_type(memory):
    """按类型搜索记忆"""
    memory.research.add(
        title="Discovery",
        content="content",
        memory_type="discovery",
        tags=["test"],
        paper_doi="10.1234/d1",
    )
    memory.research.add(
        title="Method",
        content="content",
        memory_type="method",
        tags=["test"],
        paper_doi="10.1234/m1",
    )
    results = memory.research.search_by_type("discovery")
    assert len(results) == 1
    assert results[0]["memory_type"] == "discovery"


def test_research_memory_delete(memory):
    """删除研究记忆"""
    mem_id = memory.research.add(
        title="To delete",
        content="content",
        memory_type="discovery",
        tags=["test"],
        paper_doi="10.1234/delete",
    )
    memory.research.delete(mem_id)
    results = memory.research.get_related("10.1234/delete")
    assert len(results) == 0


def test_research_memory_get_related(memory):
    """按论文 DOI 获取相关记忆"""
    memory.research.add(
        title="Paper 1 memory",
        content="content",
        memory_type="insight",
        tags=["test"],
        paper_doi="10.1234/shared",
    )
    results = memory.research.get_related("10.1234/shared")
    assert len(results) == 1


def test_research_memory_invalid_type(memory):
    """无效的记忆类型应返回 None"""
    mem_id = memory.research.add(
        title="Invalid",
        content="content",
        memory_type="invalid_type",
        tags=["test"],
    )
    assert mem_id is None
