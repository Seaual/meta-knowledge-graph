# tests/repositories/test_concept_repo.py
"""
ConceptRepository tests
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database


@pytest.fixture
def test_db():
    """创建测试数据库"""
    db = Database(":memory:")
    db.connect()
    yield db
    db.close()


def test_add_concept(test_db):
    """测试添加概念"""
    concept_id = test_db.concepts.add({"text": "Machine Learning"})

    assert concept_id == "machine-learning"

    concept = test_db.concepts.get("machine-learning")
    assert concept is not None
    assert concept["text"] == "Machine Learning"


def test_concept_hierarchy(test_db):
    """测试概念层级关系"""
    # 添加父子概念
    test_db.concepts.add({"text": "AI"})
    test_db.concepts.add({"text": "Machine Learning"})
    test_db.concepts.add({"text": "Deep Learning"})

    # 建立关系
    test_db.concepts.add_relation("ai", "machine-learning")
    test_db.concepts.add_relation("machine-learning", "deep-learning")

    # 测试获取子概念
    children = test_db.concepts.get_children("ai")
    assert len(children) == 1
    assert children[0]["text"] == "Machine Learning"

    # 测试获取父概念
    parents = test_db.concepts.get_parents("deep-learning")
    assert len(parents) == 1
    assert parents[0]["text"] == "Machine Learning"


def test_root_concepts(test_db):
    """测试根概念"""
    test_db.concepts.add({"text": "Root Concept"})
    test_db.concepts.add({"text": "Child Concept"})
    test_db.concepts.add_relation("root-concept", "child-concept")

    roots = test_db.concepts.get_root()
    root_ids = [r["id"] for r in roots]

    assert "root-concept" in root_ids
    assert "child-concept" not in root_ids


def test_backward_compatibility(test_db):
    """测试向后兼容方法"""
    concept_id = test_db.add_concept({"text": "Backward Compat"})
    assert concept_id == "backward-compat"

    concept = test_db.get_concept("backward-compat")
    assert concept["text"] == "Backward Compat"