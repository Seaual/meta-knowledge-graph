# mkg/repositories/concept_repo.py
"""
ConceptRepository - 概念相关数据库操作
"""

import hashlib
import re
from collections import deque

from .base import BaseRepository


class ConceptRepository(BaseRepository):
    """概念数据访问层"""

    # ========== CRUD 方法 ==========

    def add(self, concept_data: dict) -> str:
        """
        添加概念（如果不存在则创建，已存在则更新）

        Args:
            concept_data: 概念数据字典，包含 id, text, text_en, text_zh, category 等

        Returns:
            概念 ID (slug)
        """
        concept_id = concept_data.get('id')
        if not concept_id:
            concept_id = self._to_slug(concept_data.get('text', ''))

        # 检查概念是否已存在
        cursor = self.execute_read(
            "SELECT id FROM concepts WHERE id = ?",
            (concept_id,)
        )
        existing = cursor.fetchone()

        if existing:
            # 更新 text_en/text_zh 如果提供了且当前为空
            if concept_data.get('text_en'):
                self.execute_write("""
                    UPDATE concepts SET text_en = ?
                    WHERE id = ? AND (text_en IS NULL OR text_en = '')
                """, (concept_data['text_en'], concept_id))
            if concept_data.get('text_zh'):
                self.execute_write("""
                    UPDATE concepts SET text_zh = ?
                    WHERE id = ? AND (text_zh IS NULL OR text_zh = '')
                """, (concept_data['text_zh'], concept_id))
        else:
            # 插入新概念
            self.execute_write("""
                INSERT INTO concepts (id, text, text_en, text_zh, category, paper_count)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                concept_id,
                concept_data.get('text'),
                concept_data.get('text_en'),
                concept_data.get('text_zh'),
                concept_data.get('category'),
            ))

        # 同步到 Neo4j
        if self._db.neo4j_store:
            self._db.neo4j_store.sync_concept(concept_data)

        return concept_id

    def get(self, concept_id: str) -> dict | None:
        """
        获取概念

        Args:
            concept_id: 概念 ID (slug)

        Returns:
            概念字典，或 None
        """
        cursor = self.execute_read(
            "SELECT * FROM concepts WHERE id = ?",
            (concept_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_by_text(self, text: str) -> dict | None:
        """
        通过文本获取概念

        Args:
            text: 概念文本（显示名）

        Returns:
            概念字典，或 None
        """
        cursor = self.execute_read(
            "SELECT * FROM concepts WHERE LOWER(text) = LOWER(?)",
            (text,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all(self) -> list[dict]:
        """
        获取所有概念

        Returns:
            概念列表
        """
        cursor = self.execute_read(
            "SELECT * FROM concepts ORDER BY paper_count DESC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_root(self) -> list[dict]:
        """
        获取根概念（没有父节点的概念）

        Returns:
            根概念列表
        """
        cursor = self.execute_read("""
            SELECT c.* FROM concepts c
            LEFT JOIN concept_relations cr ON c.id = cr.child_id
            WHERE cr.parent_id IS NULL
            ORDER BY c.paper_count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_count(self, folder_id: str = None) -> int:
        """
        获取概念总数，可选按文件夹过滤

        Args:
            folder_id: 文件夹 ID（可选）

        Returns:
            概念数量
        """
        if folder_id and folder_id != 'default':
            cursor = self.execute_read("""
                SELECT COUNT(DISTINCT c.id) as count
                FROM concepts c
                JOIN paper_concepts pc ON c.id = pc.concept_id
                JOIN papers p ON pc.paper_doi = p.doi
                WHERE p.folder_id = ?
            """, (folder_id,))
        else:
            cursor = self.execute_read("SELECT COUNT(*) as count FROM concepts")
        return cursor.fetchone()['count']

    def delete(self, concept_id: str):
        """
        删除概念及其所有关联

        Args:
            concept_id: 概念 ID
        """
        # 删除论文关联
        self.execute_write(
            "DELETE FROM paper_concepts WHERE concept_id = ?",
            (concept_id,)
        )

        # 删除层级关系
        self.execute_write("""
            DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?
        """, (concept_id, concept_id))

        # 删除概念本身
        self.execute_write(
            "DELETE FROM concepts WHERE id = ?",
            (concept_id,)
        )

    # ========== 层级关系 ==========

    def get_children(self, concept_id: str) -> list[dict]:
        """
        获取概念的子节点

        Args:
            concept_id: 概念 ID

        Returns:
            子概念列表
        """
        cursor = self.execute_read("""
            SELECT c.* FROM concepts c
            JOIN concept_relations cr ON c.id = cr.child_id
            WHERE cr.parent_id = ?
            ORDER BY c.paper_count DESC
        """, (concept_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_parents(self, concept_id: str) -> list[dict]:
        """
        获取概念的父节点

        Args:
            concept_id: 概念 ID

        Returns:
            父概念列表
        """
        cursor = self.execute_read("""
            SELECT c.* FROM concepts c
            JOIN concept_relations cr ON c.id = cr.parent_id
            WHERE cr.child_id = ?
        """, (concept_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_tree(self, root_id: str = None) -> dict:
        """
        获取概念树状结构

        Args:
            root_id: 根概念 ID（可选，默认从根概念开始）

        Returns:
            概念树字典
        """
        # 如果没有指定根节点，从根概念开始
        if root_id is None:
            roots = self.get_root()
            if roots:
                root_id = roots[0]['id']
            else:
                return {}

        concept = self.get(root_id)
        if not concept:
            return {}

        # 递归获取子节点
        children = self.get_children(root_id)
        concept['children'] = [self.get_tree(child['id']) for child in children]

        # 获取关联论文
        cursor = self.execute_read("""
            SELECT p.doi, p.title FROM papers p
            JOIN paper_concepts pk ON p.doi = pk.paper_doi
            WHERE pk.concept_id = ?
        """, (root_id,))
        concept['papers'] = [{'doi': row['doi'], 'title': row['title']}
                            for row in cursor.fetchall()]

        return concept

    def add_relation(self, parent_id: str, child_id: str,
                     relation_type: str = "parent-child"):
        """
        添加概念层级关系（父子关系）

        Args:
            parent_id: 父概念 ID
            child_id: 子概念 ID
            relation_type: 关系类型（默认 parent-child）
        """
        # 转换关系类型：外部使用 parent-child，内部使用 is_subconcept_of
        internal_type = 'is_subconcept_of' if relation_type == 'parent-child' else relation_type
        self.execute_write("""
            INSERT OR REPLACE INTO concept_relations (parent_id, child_id, relation_type)
            VALUES (?, ?, ?)
        """, (parent_id, child_id, internal_type))

        # 同步到 Neo4j
        if self._db.neo4j_store:
            self._db.neo4j_store.sync_relation(parent_id, child_id, relation_type)

    def update_relations(self, concept_id: str, relations: dict):
        """
        更新概念的父子关系

        Args:
            concept_id: 概念 ID
            relations: {"parents": [...], "children": [...]}
        """
        # 删除现有的父子关系
        self.execute_write("""
            DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?
        """, (concept_id, concept_id))

        # 添加新的父关系
        for parent_id in relations.get("parents", []):
            self.execute_write("""
                INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
                VALUES (?, ?)
            """, (parent_id, concept_id))

        # 添加新的子关系
        for child_id in relations.get("children", []):
            self.execute_write("""
                INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
                VALUES (?, ?)
            """, (concept_id, child_id))

    # ========== 分类与文件夹 ==========

    def get_by_category(self, category: str) -> list[dict]:
        """
        按类别获取概念

        Args:
            category: 概念类别 (field/direction/subdirection/task/method/technique)

        Returns:
            概念列表
        """
        cursor = self.execute_read("""
            SELECT * FROM concepts WHERE category = ? ORDER BY paper_count DESC
        """, (category,))
        return [dict(row) for row in cursor.fetchall()]

    def get_by_category_and_folder(self, category: str, folder_id: str) -> list[dict]:
        """
        按类别和文件夹获取概念

        Args:
            category: 概念类别
            folder_id: 文件夹 ID

        Returns:
            概念列表
        """
        cursor = self.execute_read("""
            SELECT DISTINCT c.id, c.text, c.category, c.paper_count, c.depth_cache
            FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            JOIN papers p ON pc.paper_doi = p.doi
            WHERE c.category = ? AND p.folder_id = ?
            ORDER BY c.paper_count DESC
        """, (category, folder_id))
        return [dict(row) for row in cursor.fetchall()]

    def get_by_folder(self, folder_id: str) -> list[dict]:
        """
        获取指定文件夹中的论文关联的所有概念

        Args:
            folder_id: 文件夹 ID

        Returns:
            概念列表
        """
        cursor = self.execute_read("""
            SELECT DISTINCT c.id, c.text, c.category, c.paper_count, c.depth_cache
            FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            JOIN papers p ON pc.paper_doi = p.doi
            WHERE p.folder_id = ?
        """, (folder_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_relations_by_folder(self, folder_id: str) -> list[dict]:
        """
        获取指定文件夹中的概念关系（确保两端节点都在文件夹中）

        Args:
            folder_id: 文件夹 ID

        Returns:
            概念关系列表
        """
        # 先获取该文件夹中所有概念的 ID 集合
        cursor = self.execute_read("""
            SELECT DISTINCT c.id
            FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            JOIN papers p ON pc.paper_doi = p.doi
            WHERE p.folder_id = ?
        """, (folder_id,))
        concept_ids: set[str] = set(row['id'] for row in cursor.fetchall())

        # 获取所有关系，然后过滤
        cursor = self.execute_read("""
            SELECT DISTINCT cr.parent_id, cr.child_id
            FROM concept_relations cr
            JOIN paper_concepts pc1 ON cr.parent_id = pc1.concept_id
            JOIN papers p1 ON pc1.paper_doi = p1.doi
            WHERE p1.folder_id = ?
        """, (folder_id,))

        # 只返回两端节点都在文件夹中的关系
        relations = []
        for row in cursor.fetchall():
            if row['parent_id'] in concept_ids and row['child_id'] in concept_ids:
                relations.append(dict(row))
        return relations

    # ========== 论文关联 ==========

    def get_papers(self, concept_id: str) -> list[dict]:
        """
        获取概念关联的论文

        Args:
            concept_id: 概念 ID

        Returns:
            论文列表
        """
        cursor = self.execute_read("""
            SELECT p.* FROM papers p
            JOIN paper_concepts pk ON p.doi = pk.paper_doi
            WHERE pk.concept_id = ?
            ORDER BY p.published_date DESC
        """, (concept_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_paper_concept(self, paper_doi: str, concept_id: str,
                          relevance: float = 1.0) -> None:
        """
        添加论文 - 概念关联

        Args:
            paper_doi: 论文 DOI
            concept_id: 概念 ID
            relevance: 相关度/置信度（默认 1.0）
        """
        self.execute_write("""
            INSERT OR IGNORE INTO paper_concepts (paper_doi, concept_id, confidence)
            VALUES (?, ?, ?)
        """, (paper_doi, concept_id, relevance))

        # 更新 paper_count
        self._update_paper_count(concept_id)

    # ========== 概念提取 ==========

    def save_extraction(self, paper_doi: str, hierarchy: dict,
                       raw_response: str) -> None:
        """
        保存 LLM 提取的概念层级结构

        Args:
            paper_doi: 论文 DOI
            hierarchy: 概念层级字典
            raw_response: LLM 原始响应
        """
        self.execute_write("""
            INSERT INTO concept_extractions (paper_doi, concept_hierarchy, raw_llm_response)
            VALUES (?, ?, ?)
        """, (paper_doi, self._serialize_json(hierarchy), raw_response))

    def get_extraction(self, paper_doi: str) -> dict | None:
        """
        获取已保存的概念提取结果

        Args:
            paper_doi: 论文 DOI

        Returns:
            提取结果字典，包含 concept_hierarchy（已解析），或 None
        """
        cursor = self.execute_read("""
            SELECT * FROM concept_extractions WHERE paper_doi = ?
        """, (paper_doi,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['concept_hierarchy'] = self._deserialize_json(
                result.get('concept_hierarchy'), {}
            )
            return result
        return None

    # ========== 深度缓存 ==========

    def recalculate_depth_cache(self, concept_id: str = None) -> None:
        """
        重新计算概念的深度缓存

        使用 BFS 从根节点开始计算所有概念的深度

        Args:
            concept_id: 可选，指定重新计算某个概念及其子树的深度
        """
        # 重置所有 depth_cache
        self.execute_write("UPDATE concepts SET depth_cache = -1")

        # 获取根概念（没有父节点的概念）
        cursor = self.execute_read("""
            SELECT id FROM concepts c
            LEFT JOIN concept_relations cr ON c.id = cr.child_id
            WHERE cr.parent_id IS NULL
        """)
        roots = [row['id'] for row in cursor.fetchall()]

        # BFS 计算深度
        queue = deque([(root_id, 0) for root_id in roots])

        while queue:
            node_id, depth = queue.popleft()

            # 更新深度
            self.execute_write("""
                UPDATE concepts SET depth_cache = ? WHERE id = ?
            """, (depth, node_id))

            # 获取子节点
            cursor = self.execute_read("""
                SELECT child_id FROM concept_relations WHERE parent_id = ?
            """, (node_id,))
            children = [row['child_id'] for row in cursor.fetchall()]

            for child_id in children:
                queue.append((child_id, depth + 1))

    # ========== 内部方法 ==========

    def _build_tree(self, parent_id: str) -> dict:
        """
        递归构建概念树（内部方法）

        Args:
            parent_id: 父概念 ID

        Returns:
            概念树节点字典
        """
        concept = self.get(parent_id)
        if not concept:
            return {}

        children = self.get_children(parent_id)
        concept['children'] = [self._build_tree(child['id']) for child in children]

        return concept

    def _update_paper_count(self, concept_id: str) -> None:
        """
        更新概念的论文计数（内部方法）

        Args:
            concept_id: 概念 ID
        """
        self.execute_write("""
            UPDATE concepts SET paper_count = (
                SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?
            ) WHERE id = ?
        """, (concept_id, concept_id))

        # 同步到 Neo4j
        if self._db.neo4j_store:
            count = self.execute_read(
                "SELECT COUNT(DISTINCT paper_doi) as count FROM paper_concepts WHERE concept_id = ?",
                (concept_id,)
            ).fetchone()['count']
            self._db.neo4j_store.update_paper_count(concept_id, count)

    def _calculate_depth(self, concept_id: str, visited: set[str] = None) -> int:
        """
        计算概念的深度（从根节点到该节点的层数）

        Args:
            concept_id: 概念 ID
            visited: 已访问的概念集合（防止循环）

        Returns:
            概念深度（根节点为 0）
        """
        if visited is None:
            visited = set()

        if concept_id in visited:
            return 0  # 防止循环

        visited.add(concept_id)

        parents = self.get_parents(concept_id)
        if not parents:
            return 0  # 根节点

        # 深度 = 最深父节点的深度 + 1
        max_parent_depth = 0
        for parent in parents:
            parent_depth = self._calculate_depth(parent['id'], visited)
            max_parent_depth = max(max_parent_depth, parent_depth)

        return max_parent_depth + 1

    def _delete_orphaned(self, concept_id: str) -> None:
        """
        删除孤立概念（没有任何论文关联的概念）

        Args:
            concept_id: 概念 ID
        """
        cursor = self.execute_read(
            "SELECT COUNT(*) as count FROM paper_concepts WHERE concept_id = ?",
            (concept_id,)
        )
        count = cursor.fetchone()['count']

        if count == 0:
            # 没有论文关联，删除该概念
            self.delete(concept_id)

    def _to_slug(self, text: str) -> str:
        """
        将文本转换为 slug ID（支持中文）

        Args:
            text: 概念文本

        Returns:
            slug ID（小写，连字符分隔）
        """
        # 尝试转换为拼音（如果安装了 pypinyin）
        try:
            from pypinyin import lazy_pinyin
            slug = '-'.join(lazy_pinyin(text))
            slug = slug.lower()
            slug = re.sub(r'[^a-z0-9-]', '', slug)
            slug = re.sub(r'-+', '-', slug)
            slug = slug.strip('-')
            if slug:
                return slug[:100]
        except ImportError:
            pass

        # 回退：使用文本的 hash 作为 ID
        # 对于英文，尝试正常转换
        slug = text.lower()
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = slug.strip('-')

        if slug:
            return slug[:100]

        # 如果是纯中文或其他非拉丁字符，使用 hash
        return hashlib.md5(text.encode()).hexdigest()[:12]
