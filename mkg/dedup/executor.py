"""
合并执行器 - 执行概念合并操作
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class MergeResult:
    """合并结果"""
    source_id: str
    target_id: str
    status: str  # success / failed
    message: Optional[str] = None


class MergeExecutor:
    """合并执行器"""

    def __init__(self, db):
        self.db = db

    def execute(self, source_id: str, target_id: str, merged_relations: Dict) -> MergeResult:
        """执行合并操作"""
        try:
            # 检查循环依赖
            if self._detect_cycle(target_id, merged_relations):
                return MergeResult(
                    source_id=source_id,
                    target_id=target_id,
                    status='failed',
                    message='检测到循环依赖，拒绝合并'
                )

            # 使用线程安全的方式执行事务
            with self.db._lock:
                cursor = self.db.conn.cursor()
                cursor.execute("BEGIN TRANSACTION")

                try:
                    # 迁移论文关联
                    cursor.execute("""
                        INSERT OR IGNORE INTO paper_concepts (paper_doi, concept_id, confidence, source)
                        SELECT paper_doi, ?, confidence, source
                        FROM paper_concepts WHERE concept_id = ?
                    """, (target_id, source_id))

                    cursor.execute("DELETE FROM paper_concepts WHERE concept_id = ?", (source_id,))

                    # 更新 paper_count
                    cursor.execute("""
                        UPDATE concepts SET paper_count = (
                            SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?
                        ) WHERE id = ?
                    """, (target_id, target_id))

                    # 更新层级关系
                    cursor.execute("DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?", (source_id, source_id))

                    for parent_id in merged_relations.get("parents", []):
                        cursor.execute("""
                            INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
                            VALUES (?, ?)
                        """, (parent_id, target_id))

                    for child_id in merged_relations.get("children", []):
                        cursor.execute("""
                            INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
                            VALUES (?, ?)
                        """, (target_id, child_id))

                    # 删除源概念
                    cursor.execute("DELETE FROM concepts WHERE id = ?", (source_id,))

                    self.db.conn.commit()

                    # 重新计算深度缓存（在事务外执行）
                    self._recalculate_depth_cache_safe()

                    return MergeResult(source_id=source_id, target_id=target_id, status='success')
                except Exception as e:
                    self.db.conn.rollback()
                    raise e

        except Exception as e:
            return MergeResult(source_id=source_id, target_id=target_id, status='failed', message=str(e))

    def _recalculate_depth_cache_safe(self):
        """安全地重新计算深度缓存"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("UPDATE concepts SET depth_cache = -1")

            cursor.execute("""
                SELECT id FROM concepts c
                LEFT JOIN concept_relations cr ON c.id = cr.child_id
                WHERE cr.parent_id IS NULL
            """)
            roots = [row['id'] for row in cursor.fetchall()]

            from collections import deque
            queue = deque([(root_id, 0) for root_id in roots])

            while queue:
                node_id, depth = queue.popleft()
                cursor.execute("UPDATE concepts SET depth_cache = ? WHERE id = ?", (depth, node_id))
                cursor.execute("SELECT child_id FROM concept_relations WHERE parent_id = ?", (node_id,))
                children = [row['child_id'] for row in cursor.fetchall()]
                for child_id in children:
                    queue.append((child_id, depth + 1))

            self.db.conn.commit()
        except Exception as e:
            print(f"Warning: Failed to recalculate depth cache: {e}")

    def _detect_cycle(self, concept_id: str, merged_relations: Dict) -> bool:
        """检测合并后的层级关系是否会产生循环"""
        for parent_id in merged_relations.get('parents', []):
            if self._is_descendant(concept_id, parent_id):
                return True
        for child_id in merged_relations.get('children', []):
            if self._is_ancestor(concept_id, child_id):
                return True
        return False

    def _is_descendant(self, ancestor_id: str, node_id: str) -> bool:
        """检查 node_id 是否是 ancestor_id 的后代"""
        visited = set()
        queue = [ancestor_id]
        while queue:
            current = queue.pop(0)
            if current == node_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend([c['id'] for c in self.db.get_concept_children(current)])
        return False

    def _is_ancestor(self, descendant_id: str, node_id: str) -> bool:
        """检查 node_id 是否是 descendant_id 的祖先"""
        visited = set()
        queue = [descendant_id]
        while queue:
            current = queue.pop(0)
            if current == node_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend([p['id'] for p in self.db.get_concept_parents(current)])
        return False