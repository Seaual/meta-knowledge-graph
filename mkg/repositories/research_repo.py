# mkg/repositories/research_repo.py
"""
ResearchRepository - 研究会话相关数据库操作
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class ResearchRepository(BaseRepository):
    """研究会话数据访问层"""

    # ========== 研究会话 CRUD ==========

    def create_session(self, session_id: str, target_type: str,
                       target_id: str, query: str) -> str:
        """
        创建研究会话

        Args:
            session_id: 会话 ID
            target_type: 目标类型（paper/concept）
            target_id: 目标 ID
            query: 用户查询

        Returns:
            session_id
        """
        self.execute_write("""
            INSERT INTO research_sessions (id, target_type, target_id, user_query)
            VALUES (?, ?, ?, ?)
        """, (session_id, target_type, target_id, query))

        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """
        获取研究会话

        Args:
            session_id: 会话 ID

        Returns:
            会话字典，或 None
        """
        cursor = self.execute_read(
            "SELECT * FROM research_sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        if row:
            session = dict(row)
            # 解析 dimensions JSON
            session['dimensions'] = self._deserialize_json(session.get('dimensions'), [])
            return session

        return None

    def update_progress(self, session_id: str, progress: int,
                        dimensions: List[str] = None) -> bool:
        """
        更新研究会话进度

        Args:
            session_id: 会话 ID
            progress: 进度百分比
            dimensions: 维度列表（可选）

        Returns:
            是否更新成功
        """
        if dimensions:
            self.execute_write("""
                UPDATE research_sessions
                SET progress = ?, dimensions = ?
                WHERE id = ?
            """, (progress, self._serialize_json(dimensions), session_id))
        else:
            self.execute_write("""
                UPDATE research_sessions
                SET progress = ?
                WHERE id = ?
            """, (progress, session_id))

        return True

    def complete_session(self, session_id: str, report_path: str = None) -> bool:
        """
        完成研究会话

        Args:
            session_id: 会话 ID
            report_path: 报告路径（可选）

        Returns:
            是否更新成功
        """
        self.execute_write("""
            UPDATE research_sessions
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                report_path = ?
            WHERE id = ?
        """, (report_path, session_id))

        return True

    def delete_session(self, session_id: str) -> bool:
        """
        删除研究会话

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        # 删除发现
        self.execute_write(
            "DELETE FROM research_findings WHERE session_id = ?",
            (session_id,)
        )

        # 删除会话
        self.execute_write(
            "DELETE FROM research_sessions WHERE id = ?",
            (session_id,)
        )

        return True

    # ========== 研究发现 ==========

    def save_finding(self, session_id: str, dimension: str,
                     finding: str, confidence: float = None,
                     sources: List[str] = None) -> int:
        """
        保存研究发现

        Args:
            session_id: 会话 ID
            dimension: 维度名称
            finding: 发现内容
            confidence: 置信度（可选）
            sources: 来源列表（可选）

        Returns:
            finding ID
        """
        cursor = self.execute_write("""
            INSERT INTO research_findings
                (session_id, dimension, finding, sources)
            VALUES (?, ?, ?, ?)
        """, (
            session_id,
            dimension,
            finding,
            self._serialize_json(sources) if sources else None
        ))

        return cursor.lastrowid

    def get_findings(self, session_id: str) -> List[dict]:
        """
        获取研究会话的所有发现

        Args:
            session_id: 会话 ID

        Returns:
            发现列表
        """
        cursor = self.execute_read("""
            SELECT * FROM research_findings
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,))

        findings = []
        for row in cursor.fetchall():
            finding = dict(row)
            finding['sources'] = self._deserialize_json(finding.get('sources'), [])
            findings.append(finding)

        return findings

    def get_findings_by_dimension(self, session_id: str, dimension: str) -> List[dict]:
        """
        按维度获取发现

        Args:
            session_id: 会话 ID
            dimension: 维度名称

        Returns:
            发现列表
        """
        cursor = self.execute_read("""
            SELECT * FROM research_findings
            WHERE session_id = ? AND dimension = ?
            ORDER BY created_at ASC
        """, (session_id, dimension))

        findings = []
        for row in cursor.fetchall():
            finding = dict(row)
            finding['sources'] = self._deserialize_json(finding.get('sources'), [])
            findings.append(finding)

        return findings

    # ========== 报告保存 ==========

    def save_report(self, session_id: str, report: str) -> bool:
        """
        保存研究报告内容（更新 report_path）

        Args:
            session_id: 会话 ID
            report: 报告路径

        Returns:
            是否保存成功
        """
        self.execute_write("""
            UPDATE research_sessions
            SET report_path = ?, status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (report, session_id))

        return True

    # ========== S2 推荐 ==========

    def add_s2_recommendation(self, source_type: str, source_id: str,
                               paper_data: Dict) -> int:
        """
        添加 S2 推荐论文

        Args:
            source_type: 来源类型（paper/concept）
            source_id: 来源 ID
            paper_data: 推荐论文数据

        Returns:
            recommendation ID
        """
        cursor = self.execute_write("""
            INSERT INTO s2_recommendations
                (source_type, source_id, recommended_s2_id, recommended_title,
                 recommended_abstract, recommended_year, recommended_citation_count,
                 recommended_tldr, recommended_open_access_pdf, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_type,
            source_id,
            paper_data.get('s2_id'),
            paper_data.get('title'),
            paper_data.get('abstract'),
            paper_data.get('year'),
            paper_data.get('citation_count'),
            paper_data.get('tldr'),
            paper_data.get('open_access_pdf'),
            paper_data.get('score')
        ))

        return cursor.lastrowid

    def get_s2_recommendations(self, source_type: str, source_id: str) -> List[dict]:
        """
        获取 S2 推荐

        Args:
            source_type: 来源类型
            source_id: 来源 ID

        Returns:
            推荐列表
        """
        cursor = self.execute_read("""
            SELECT * FROM s2_recommendations
            WHERE source_type = ? AND source_id = ?
            ORDER BY score DESC, recommended_citation_count DESC
        """, (source_type, source_id))

        recommendations = []
        for row in cursor.fetchall():
            rec = dict(row)
            # 解析 JSON 字段
            rec['recommended_open_access_pdf'] = self._deserialize_json(
                rec.get('recommended_open_access_pdf')
            )
            recommendations.append(rec)

        return recommendations

    def clear_s2_recommendations(self, source_type: str = None,
                                  source_id: str = None) -> int:
        """
        清除 S2 推荐

        Args:
            source_type: 来源类型（可选）
            source_id: 来源 ID（可选）

        Returns:
            删除的数量
        """
        if source_type and source_id:
            cursor = self.execute_write("""
                DELETE FROM s2_recommendations
                WHERE source_type = ? AND source_id = ?
            """, (source_type, source_id))
        elif source_type:
            cursor = self.execute_write("""
                DELETE FROM s2_recommendations WHERE source_type = ?
            """, (source_type,))
        else:
            cursor = self.execute_write("DELETE FROM s2_recommendations")

        return cursor.rowcount