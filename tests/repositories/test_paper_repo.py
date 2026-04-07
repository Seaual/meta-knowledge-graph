# tests/repositories/test_paper_repo.py
"""
PaperRepository tests
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


def test_add_paper(test_db):
    """测试添加论文"""
    doi = test_db.papers.add({
        "doi": "10.1234/test",
        "title": "Test Paper"
    })
    assert doi == "10.1234/test"

    paper = test_db.papers.get("10.1234/test")
    assert paper is not None
    assert paper["title"] == "Test Paper"


def test_get_paper_by_s2_id(test_db):
    """测试通过 S2 ID 获取论文"""
    test_db.papers.add({
        "doi": "10.1234/s2test",
        "title": "S2 Test Paper",
        "s2_paper_id": "abc123"
    })

    paper = test_db.papers.get_by_s2_id("abc123")
    assert paper is not None
    assert paper["title"] == "S2 Test Paper"


def test_update_status(test_db):
    """测试更新论文状态"""
    test_db.papers.add({"doi": "10.1234/status", "title": "Status Test"})

    test_db.papers.update_status("10.1234/status", "processed")

    paper = test_db.papers.get("10.1234/status")
    assert paper["status"] == "processed"


def test_move_to_folder(test_db):
    """测试移动论文到文件夹"""
    folder_id = test_db.folders.create("Test Folder")
    test_db.papers.add({"doi": "10.1234/folder", "title": "Folder Test"})

    test_db.papers.move_to_folder("10.1234/folder", folder_id)

    papers = test_db.papers.get_by_folder(folder_id)
    assert len(papers) == 1
    assert papers[0]["title"] == "Folder Test"


def test_backward_compatibility(test_db):
    """测试向后兼容方法"""
    # 使用旧的 Database 方法
    doi = test_db.add_paper({"doi": "10.1234/compat", "title": "Compat Test"})
    assert doi == "10.1234/compat"

    paper = test_db.get_paper("10.1234/compat")
    assert paper["title"] == "Compat Test"