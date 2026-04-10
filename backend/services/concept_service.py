# backend/services/concept_service.py
"""
概念服务 - 概念 CRUD 操作
"""

import builtins

from mkg.database import Database


class ConceptService:
    """概念数据访问服务"""

    def __init__(self, db: Database):
        self.db = db

    def list(self) -> list[dict]:
        """获取所有概念"""
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.get_all_concepts()
            if results is not None:
                return results
        return self.db.concepts.get_all()

    def get(self, concept_id: str) -> dict | None:
        """获取单个概念（包含父子关系）"""
        concept = self.db.concepts.get(concept_id)
        if concept:
            concept['children'] = self.get_children(concept_id)
            concept['parents'] = self.get_parents(concept_id)
        return concept

    def search(self, query: str) -> builtins.list[dict]:
        """搜索概念"""
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.search_concepts(query)
            if results:
                return results
        # fallback to SQLite
        cursor = self.db.execute_read(
            "SELECT * FROM concepts WHERE text LIKE ? ORDER BY paper_count DESC LIMIT 50",
            (f"%{query}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_roots(self) -> builtins.list[dict]:
        """获取根概念"""
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.get_root_concepts()
            if results is not None:
                return results
        return self.db.concepts.get_root()

    def get_tree(self, root_id: str = None) -> dict:
        """获取概念树"""
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            tree = neo4j.get_tree(root_id)
            if tree:
                return tree
        return self.db.concepts.get_tree(root_id)

    def get_children(self, concept_id: str) -> builtins.list[dict]:
        """获取子概念"""
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.get_children(concept_id)
            if results is not None:
                return results
        return self.db.concepts.get_children(concept_id)

    def get_parents(self, concept_id: str) -> builtins.list[dict]:
        """获取父概念"""
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.get_parents(concept_id)
            if results is not None:
                return results
        return self.db.concepts.get_parents(concept_id)

    def get_papers(self, concept_id: str, limit: int = 20) -> builtins.list[dict]:
        """获取概念关联的论文"""
        papers = self.db.concepts.get_papers(concept_id)
        return papers[:limit]
