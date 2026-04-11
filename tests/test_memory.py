"""
Agent Memory 模块测试
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from mkg.database import Database


@pytest.fixture
def test_db():
    db = Database(":memory:")
    db.connect()
    yield db
    db.close()


def test_user_preferences_table_exists(test_db):
    """user_preferences 表应存在"""
    cursor = test_db.execute_read(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_preferences'"
    )
    assert cursor.fetchone() is not None


def test_conversation_context_table_exists(test_db):
    """conversation_context 表应存在"""
    cursor = test_db.execute_read(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_context'"
    )
    assert cursor.fetchone() is not None


def test_research_memories_table_exists(test_db):
    """research_memories 表应存在"""
    cursor = test_db.execute_read(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='research_memories'"
    )
    assert cursor.fetchone() is not None
