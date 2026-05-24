# tests/repositories/test_concept_repo.py
"""
ConceptRepository tests
"""


def test_add_concept(test_db):
    """测试添加概念"""
    concept_id = test_db.concepts.add({"text": "Machine Learning"})

    # concept_id depends on pypinyin availability (machine-learning vs machinelearning)
    assert concept_id is not None
    assert len(concept_id) > 0

    concept = test_db.concepts.get(concept_id)
    assert concept is not None
    assert concept["text"] == "Machine Learning"


def test_concept_hierarchy(test_db):
    """测试概念层级关系"""
    # 添加父子概念，使用固定 ID 避免 pypinyin 差异
    test_db.concepts.add({"id": "ai", "text": "AI"})
    test_db.concepts.add({"id": "ml", "text": "Machine Learning"})
    test_db.concepts.add({"id": "dl", "text": "Deep Learning"})

    # 建立关系
    test_db.concepts.add_relation("ai", "ml")
    test_db.concepts.add_relation("ml", "dl")

    # 测试获取子概念
    children = test_db.concepts.get_children("ai")
    assert len(children) == 1
    assert children[0]["text"] == "Machine Learning"

    # 测试获取父概念
    parents = test_db.concepts.get_parents("dl")
    assert len(parents) == 1
    assert parents[0]["text"] == "Machine Learning"


def test_root_concepts(test_db):
    """测试根概念"""
    test_db.concepts.add({"id": "rootconcept", "text": "Root Concept"})
    test_db.concepts.add({"id": "childconcept", "text": "Child Concept"})
    test_db.concepts.add_relation("rootconcept", "childconcept")

    roots = test_db.concepts.get_root()
    root_ids = [r["id"] for r in roots]

    assert "rootconcept" in root_ids
    assert "childconcept" not in root_ids


def test_backward_compatibility(test_db):
    """测试通过 Database 类添加概念（直接实现）"""
    concept_id = test_db.add_concept({"id": "backwardcompat", "text": "Backward Compat"})
    assert concept_id == "backwardcompat"

    concept = test_db.get_concept("backwardcompat")
    assert concept["text"] == "Backward Compat"
