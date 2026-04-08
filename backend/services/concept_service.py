# backend/services/concept_service.py
"""
概念服务 - 概念 CRUD 操作
"""

from typing import Optional, List, Dict
from mkg.database import Database


class ConceptService:
    """概念数据访问服务"""

    def __init__(self, db: Database):
        self.db = db

    def list(self) -> List[Dict]:
        """获取所有概念"""
        return self.db.concepts.get_all()

    def get(self, concept_id: str) -> Optional[Dict]:
        """获取单个概念（包含父子关系）"""
        concept = self.db.concepts.get(concept_id)
        if concept:
            concept['children'] = self.db.concepts.get_children(concept_id)
            concept['parents'] = self.db.concepts.get_parents(concept_id)
        return concept

    def search(self, query: str) -> List[Dict]:
        """搜索概念"""
        cursor = self.db.execute_read(
            "SELECT * FROM concepts WHERE text LIKE ? ORDER BY paper_count DESC LIMIT 50",
            (f"%{query}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_roots(self) -> List[Dict]:
        """获取根概念"""
        return self.db.concepts.get_root()

    def get_tree(self, root_id: str = None) -> Dict:
        """获取概念树"""
        return self.db.concepts.get_tree(root_id)

    def get_children(self, concept_id: str) -> List[Dict]:
        """获取子概念"""
        return self.db.concepts.get_children(concept_id)

    def get_parents(self, concept_id: str) -> List[Dict]:
        """获取父概念"""
        return self.db.concepts.get_parents(concept_id)

    def get_papers(self, concept_id: str, limit: int = 20) -> List[Dict]:
        """获取概念关联的论文"""
        papers = self.db.concepts.get_papers(concept_id)
        return papers[:limit]