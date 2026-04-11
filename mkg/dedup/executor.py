"""
合并执行器 - 执行概念合并操作
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger("mkg.dedup")


@dataclass
class MergeResult:
    """合并结果"""
    source_id: str
    target_id: str
    status: str  # success / failed
    message: str = ""


# 合并历史表 DDL
MERGE_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS merge_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    source_text TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_text TEXT NOT NULL,
    merge_type TEXT,
    confidence REAL,
    rationale TEXT,
    parents_count INTEGER,
    children_count INTEGER,
    papers_transferred INTEGER,
    merged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


class MergeExecutor:
    """合并执行器"""

    def __init__(self, db):
        self.db = db

    def execute(self, source_id: str, target_id: str) -> MergeResult:
        """执行合并操作

        Args:
            source_id: 被吸收的概念 ID（将被删除）
            target_id: 保留的概念 ID
        """
        try:
            # 获取概念名称用于日志
            source_concept = self.db.get_concept(source_id)
            target_concept = self.db.get_concept(target_id)
            source_text = source_concept['text'] if source_concept else source_id
            target_text = target_concept['text'] if target_concept else target_id

            logger.info(f"开始合并: '{source_text}' -> '{target_text}'")

            # 使用线程安全的方式执行事务
            with self.db._lock:
                cursor = self.db.conn.cursor()
                cursor.execute("BEGIN TRANSACTION")

                try:
                    # ========== 1. 迁移论文关联 ==========
                    cursor.execute("""
                        INSERT OR IGNORE INTO paper_concepts (paper_doi, concept_id, confidence, source)
                        SELECT paper_doi, ?, confidence, source
                        FROM paper_concepts WHERE concept_id = ?
                    """, (target_id, source_id))

                    # 获取转移的论文数
                    cursor.execute("SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?", (source_id,))
                    papers_transferred = cursor.fetchone()[0]

                    cursor.execute("DELETE FROM paper_concepts WHERE concept_id = ?", (source_id,))

                    # 更新 paper_count
                    cursor.execute("""
                        UPDATE concepts SET paper_count = (
                            SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?
                        ) WHERE id = ?
                    """, (target_id, target_id))

                    # ========== 2. 获取当前关系 ==========
                    # 源概念的父节点（source 的 parent）
                    cursor.execute("SELECT parent_id FROM concept_relations WHERE child_id = ?", (source_id,))
                    source_parents: set[str] = set(row[0] for row in cursor.fetchall())

                    # 目标概念的父节点（target 的 parent）
                    cursor.execute("SELECT parent_id FROM concept_relations WHERE child_id = ?", (target_id,))
                    target_parents: set[str] = set(row[0] for row in cursor.fetchall())

                    # 源概念的子节点（source 是它们的 parent）
                    cursor.execute("SELECT child_id FROM concept_relations WHERE parent_id = ?", (source_id,))
                    source_children: set[str] = set(row[0] for row in cursor.fetchall())

                    # 目标概念的子节点（target 是它们的 parent）
                    cursor.execute("SELECT child_id FROM concept_relations WHERE parent_id = ?", (target_id,))
                    target_children: set[str] = set(row[0] for row in cursor.fetchall())

                    # ========== 3. 计算合并后的关系 ==========
                    # 合并父节点（两者并集，排除自引用）
                    merged_parents = (source_parents | target_parents) - {target_id, source_id}

                    # 合并子节点（两者并集，排除自引用）
                    merged_children = (source_children | target_children) - {target_id, source_id}

                    # ========== 4. 检测循环依赖 ==========
                    if self._detect_cycle(target_id, merged_parents, merged_children):
                        self.db.conn.rollback()
                        logger.error("循环依赖检测失败，回滚合并")
                        return MergeResult(
                            source_id=source_id,
                            target_id=target_id,
                            status='failed',
                            message='检测到循环依赖，拒绝合并'
                        )

                    # ========== 5. 重建关系 ==========
                    # 删除源概念的所有关系
                    cursor.execute("DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?", (source_id, source_id))

                    # 删除目标概念的旧关系（准备重建）
                    cursor.execute("DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?", (target_id, target_id))

                    # 插入合并后的父节点关系
                    for parent_id in merged_parents:
                        cursor.execute("""
                            INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
                            VALUES (?, ?)
                        """, (parent_id, target_id))

                    # 插入合并后的子节点关系
                    for child_id in merged_children:
                        cursor.execute("""
                            INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
                            VALUES (?, ?)
                        """, (target_id, child_id))

                    # ========== 6. 删除源概念 ==========
                    cursor.execute("DELETE FROM concepts WHERE id = ?", (source_id,))

                    # ========== 7. 记录合并历史 ==========
                    cursor.execute(MERGE_HISTORY_DDL)
                    cursor.execute("""
                        INSERT INTO merge_history
                        (source_id, source_text, target_id, target_text, parents_count, children_count, papers_transferred)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (source_id, source_text, target_id, target_text, len(merged_parents), len(merged_children), papers_transferred))

                    self.db.conn.commit()

                    logger.info(
                        f"合并完成: '{source_text}' -> '{target_text}' | "
                        f"parents={len(merged_parents)}, children={len(merged_children)}, papers={papers_transferred}"
                    )

                    return MergeResult(
                        source_id=source_id,
                        target_id=target_id,
                        status='success',
                        message=f"成功合并，转移 {papers_transferred} 篇论文"
                    )

                except Exception as e:
                    self.db.conn.rollback()
                    logger.error(f"合并事务失败: {e}")
                    raise e

        except Exception as e:
            logger.exception(f"合并执行失败: {e}")
            return MergeResult(
                source_id=source_id,
                target_id=target_id,
                status='failed',
                message=str(e)
            )

    def _detect_cycle(self, concept_id: str, merged_parents: set[str], merged_children: set[str]) -> bool:
        """检测合并后的层级关系是否会产生循环

        循环情况：
        1. 新的父节点是 concept_id 的后代
        2. 新的子节点是 concept_id 的祖先
        """
        for parent_id in merged_parents:
            if self._is_descendant(concept_id, parent_id):
                logger.warning(f"循环检测: {parent_id} 是 {concept_id} 的后代")
                return True

        for child_id in merged_children:
            if self._is_ancestor(concept_id, child_id):
                logger.warning(f"循环检测: {child_id} 是 {concept_id} 的祖先")
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
