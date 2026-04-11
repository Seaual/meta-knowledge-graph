"""
Neo4j 概念图谱存储层

与 SQLite 形成双存储架构：
- SQLite: 论文 CRUD、文件夹、配置的主存储
- Neo4j: 概念树、研究点发现、图谱导出的图查询引擎
"""

import logging
import os

logger = logging.getLogger(__name__)


class Neo4jStore:
    """Neo4j 概念图谱存储"""

    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        self.driver = None
        self.connected = False

        if uri is None:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        if user is None:
            user = os.getenv("NEO4J_USER", "neo4j")
        if password is None:
            password = os.getenv("NEO4J_PASSWORD", "password")

        try:
            from neo4j import GraphDatabase

            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.connected = True
            self._init_schema()
            logger.info("Neo4j connected")
        except ImportError:
            logger.warning("neo4j package not installed")
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")

    def _init_schema(self):
        """创建索引和约束"""
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS concept_id_unique FOR (c:Concept) REQUIRE c.id IS UNIQUE")
            session.run("CREATE INDEX IF NOT EXISTS concept_text_idx FOR (c:Concept) ON (c.text)")
            session.run("CREATE INDEX IF NOT EXISTS concept_category_idx FOR (c:Concept) ON (c.category)")

    def close(self):
        if self.driver:
            self.driver.close()
            self.connected = False

    def sync_concept(self, concept_data: dict) -> bool:
        """
        同步单个概念到 Neo4j（幂等）

        Args:
            concept_data: {id, text, text_en, text_zh, category, paper_count}

        Returns:
            True if synced, False if not connected
        """
        if not self.connected:
            return False
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MERGE (c:Concept {id: $id})
                    SET c.text = $text,
                        c.text_en = coalesce($text_en, c.text_en),
                        c.text_zh = coalesce($text_zh, c.text_zh),
                        c.category = $category,
                        c.paper_count = coalesce($paper_count, 0),
                        c.updated_at = datetime()
                """,
                    {
                        "id": concept_data.get("id"),
                        "text": concept_data.get("text", ""),
                        "text_en": concept_data.get("text_en"),
                        "text_zh": concept_data.get("text_zh"),
                        "category": concept_data.get("category"),
                        "paper_count": concept_data.get("paper_count", 0),
                    },
                )
            return True
        except Exception as e:
            logger.error(f"Failed to sync concept: {e}")
            return False

    def sync_relation(self, parent_id: str, child_id: str, relation_type: str = "parent-child") -> bool:
        """
        同步概念层级关系到 Neo4j（幂等）

        Args:
            parent_id: 父概念 ID
            child_id: 子概念 ID
            relation_type: 关系类型

        Returns:
            True if synced, False if not connected
        """
        if not self.connected:
            return False
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MERGE (parent:Concept {id: $parent_id})
                    MERGE (child:Concept {id: $child_id})
                    MERGE (parent)-[r:HAS_SUB]->(child)
                    SET r.relation_type = $relation_type
                """,
                    {
                        "parent_id": parent_id,
                        "child_id": child_id,
                        "relation_type": relation_type,
                    },
                )
            return True
        except Exception as e:
            logger.error(f"Failed to sync relation: {e}")
            return False

    def get_tree(self, root_id: str | None = None, max_depth: int = 10) -> dict:
        """
        从 Neo4j 获取概念树

        Args:
            root_id: 根概念 ID（可选，默认取第一个根概念）
            max_depth: 最大深度

        Returns:
            概念树字典
        """
        if not self.connected:
            return {}
        try:
            with self.driver.session() as session:
                if root_id is None:
                    result = session.run("""
                        MATCH (c:Concept)
                        WHERE NOT EXISTS { (c)<-[:HAS_SUB]-() }
                        RETURN c.id as id, c.text as text, c.category as category,
                               c.paper_count as paper_count
                        ORDER BY c.paper_count DESC LIMIT 1
                    """)
                    record = result.single()
                    if not record:
                        return {}
                    root_id = record["id"]

                return self._build_tree(session, root_id, 0, max_depth)
        except Exception as e:
            logger.error(f"Failed to get tree from Neo4j: {e}")
            return {}

    def _build_tree(self, session, concept_id: str, depth: int, max_depth: int) -> dict:
        """递归构建概念树"""
        if depth > max_depth:
            return {"id": concept_id, "truncated": True}

        result = session.run(
            """
            MATCH (c:Concept {id: $id})
            RETURN c.id as id, c.text as text, c.text_en as text_en,
                   c.text_zh as text_zh, c.category as category,
                   c.paper_count as paper_count
        """,
            {"id": concept_id},
        )
        record = result.single()
        if not record:
            return {}

        node = dict(record)

        children_result = session.run(
            """
            MATCH (parent:Concept {id: $id})-[:HAS_SUB]->(child:Concept)
            RETURN child.id as id, child.text as text, child.category as category,
                   child.paper_count as paper_count
            ORDER BY child.paper_count DESC
        """,
            {"id": concept_id},
        )

        node["children"] = []
        for child in children_result:
            child_node = self._build_tree(session, child["id"], depth + 1, max_depth)
            if child_node:
                node["children"].append(child_node)

        return node

    def get_children(self, concept_id: str) -> list[dict]:
        """获取子概念列表"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (parent:Concept {id: $id})-[:HAS_SUB]->(child:Concept)
                    RETURN child.id as id, child.text as text, child.text_en as text_en,
                           child.text_zh as text_zh, child.category as category,
                           child.paper_count as paper_count
                    ORDER BY child.paper_count DESC
                """,
                    {"id": concept_id},
                )
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to get children from Neo4j: {e}")
            return []

    def get_parents(self, concept_id: str) -> list[dict]:
        """获取父概念列表"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (child:Concept {id: $id})<-[:HAS_SUB]-(parent:Concept)
                    RETURN parent.id as id, parent.text as text, parent.text_en as text_en,
                           parent.text_zh as text_zh, parent.category as category,
                           parent.paper_count as paper_count
                """,
                    {"id": concept_id},
                )
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to get parents from Neo4j: {e}")
            return []

    def get_root_concepts(self) -> list[dict]:
        """获取根概念（没有父节点的概念）"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c:Concept)
                    WHERE NOT EXISTS { (c)<-[:HAS_SUB]-() }
                    RETURN c.id as id, c.text as text, c.category as category,
                           c.paper_count as paper_count
                    ORDER BY c.paper_count DESC
                """)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to get roots from Neo4j: {e}")
            return []

    def get_all_concepts(self) -> list[dict]:
        """获取所有概念"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c:Concept)
                    RETURN c.id as id, c.text as text, c.text_en as text_en,
                           c.text_zh as text_zh, c.category as category,
                           c.paper_count as paper_count
                    ORDER BY c.paper_count DESC
                """)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to get all concepts from Neo4j: {e}")
            return []

    def get_graph_data(self) -> dict:
        """
        获取图谱数据（nodes + edges），用于前端 D3 可视化

        Returns:
            {'nodes': [...], 'edges': [...]}
        """
        if not self.connected:
            return {"nodes": [], "edges": []}
        try:
            with self.driver.session() as session:
                nodes_result = session.run("""
                    MATCH (c:Concept)
                    RETURN c.id as id, c.text as label, c.text_en as label_en,
                           c.category as category, c.paper_count as paper_count
                """)
                nodes = [dict(r) for r in nodes_result]

                edges_result = session.run("""
                    MATCH (parent:Concept)-[r:HAS_SUB]->(child:Concept)
                    RETURN parent.id as source, child.id as target
                """)
                edges = [dict(r) for r in edges_result]

                return {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.error(f"Failed to get graph data from Neo4j: {e}")
            return {"nodes": [], "edges": []}

    def sync_all_from_sqlite(self, db) -> dict:
        """
        从 SQLite 全量同步到 Neo4j

        Args:
            db: Database 实例

        Returns:
            {'concepts_synced': N, 'relations_synced': M}
        """
        if not self.connected:
            return {"concepts_synced": 0, "relations_synced": 0, "error": "Not connected"}

        count = 0
        concepts = db.concepts.get_all()
        for concept in concepts:
            self.sync_concept(concept)
            count += 1

        rel_count = 0
        try:
            cursor = db.conn.execute("SELECT parent_id, child_id, relation_type FROM concept_relations")
            for row in cursor.fetchall():
                self.sync_relation(row["parent_id"], row["child_id"], row["relation_type"])
                rel_count += 1
        except Exception as e:
            logger.error(f"Failed to sync relations from SQLite: {e}")

        return {"concepts_synced": count, "relations_synced": rel_count}

    def clear_all(self) -> None:
        """Wipe all Concept nodes and HAS_SUB relationships from Neo4j.

        Safe for isolated test environments. Does NOT touch other node
        labels or relationship types — only Concept / HAS_SUB.
        """
        if not self.connected:
            return
        try:
            with self.driver.session() as session:
                # Delete relationships first, then nodes.
                session.run("MATCH ()-[r:HAS_SUB]-() DELETE r")
                session.run("MATCH (c:Concept) DELETE c")
        except Exception as e:
            logger.error(f"Failed to clear Neo4j: {e}")

    def get_stats(self) -> dict:
        """获取 Neo4j 图谱统计"""
        if not self.connected:
            return {}
        try:
            with self.driver.session() as session:
                total = session.run("MATCH (c:Concept) RETURN count(c) as count").single()["count"]
                relations = session.run("MATCH ()-[r:HAS_SUB]->() RETURN count(r) as count").single()["count"]
                roots = session.run("""
                    MATCH (c:Concept)
                    WHERE NOT EXISTS { (c)<-[:HAS_SUB]-() }
                    RETURN count(c) as count
                """).single()["count"]
                return {
                    "total_concepts": total,
                    "total_relations": relations,
                    "root_concepts": roots,
                }
        except Exception as e:
            logger.error(f"Failed to get stats from Neo4j: {e}")
            return {}

    def update_paper_count(self, concept_id: str, count: int) -> bool:
        """更新概念的论文计数"""
        if not self.connected:
            return False
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (c:Concept {id: $id})
                    SET c.paper_count = $count
                """,
                    {"id": concept_id, "count": count},
                )
            return True
        except Exception as e:
            logger.error(f"Failed to update paper count: {e}")
            return False

    def search_concepts(self, query: str, limit: int = 20) -> list[dict]:
        """搜索概念"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (c:Concept)
                    WHERE c.text CONTAINS $query
                       OR c.text_en CONTAINS $query
                       OR c.text_zh CONTAINS $query
                    RETURN c.id as id, c.text as text, c.category as category,
                           c.paper_count as paper_count
                    ORDER BY c.paper_count DESC
                    LIMIT $limit
                """,
                    {"query": query, "limit": limit},
                )
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to search concepts from Neo4j: {e}")
            return []
