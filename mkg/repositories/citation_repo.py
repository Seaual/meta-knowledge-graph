# mkg/repositories/citation_repo.py
"""
CitationRepository - 引用相关数据库操作
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class CitationRepository(BaseRepository):
    """引用数据访问层"""

    def add(self, paper_doi: str, citation_data: Dict) -> int:
        """
        添加引用关系

        Args:
            paper_doi: 引用论文的 DOI（citing paper）
            citation_data: 引用数据，包含：
                - cited_paper_id: 被引用论文 DOI
                - citing_s2_id: 引用论文的 S2 ID
                - cited_s2_id: 被引用论文的 S2 ID
                - citing_title: 引用论文标题
                - citing_year: 引用论文年份
                - cited_title: 被引用论文标题
                - cited_year: 被引用论文年份
                - cited_citation_count: 被引用论文的引用数
                - is_internal: 是否为内部引用（两篇论文都在库中）

        Returns:
            citation ID
        """
        cursor = self.execute_write("""
            INSERT OR REPLACE INTO paper_citations
                (citing_paper_id, cited_paper_id, citing_s2_id, cited_s2_id,
                 citing_title, citing_year, cited_title, cited_year,
                 cited_citation_count, is_internal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paper_doi,
            citation_data.get('cited_paper_id'),
            citation_data.get('citing_s2_id'),
            citation_data.get('cited_s2_id'),
            citation_data.get('citing_title'),
            citation_data.get('citing_year'),
            citation_data.get('cited_title'),
            citation_data.get('cited_year'),
            citation_data.get('cited_citation_count'),
            citation_data.get('is_internal', 0)
        ))

        return cursor.lastrowid

    def get_all(self) -> List[dict]:
        """
        获取所有引用关系

        Returns:
            引用列表
        """
        cursor = self.execute_read(
            "SELECT * FROM paper_citations ORDER BY created_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_by_s2_id(self, s2_id: str) -> List[dict]:
        """
        通过 S2 ID 获取引用关系

        Args:
            s2_id: Semantic Scholar Paper ID

        Returns:
            引用列表
        """
        cursor = self.execute_read("""
            SELECT * FROM paper_citations
            WHERE citing_s2_id = ? OR cited_s2_id = ?
            ORDER BY created_at DESC
        """, (s2_id, s2_id))

        return [dict(row) for row in cursor.fetchall()]

    def get_paper_citations(self, paper_doi: str) -> List[dict]:
        """
        获取论文引用的论文（该论文引用了哪些论文）

        Args:
            paper_doi: 论文 DOI

        Returns:
            被引用的论文列表
        """
        cursor = self.execute_read("""
            SELECT * FROM paper_citations
            WHERE citing_paper_id = ?
            ORDER BY cited_citation_count DESC
        """, (paper_doi,))

        return [dict(row) for row in cursor.fetchall()]

    def get_paper_cited_by(self, paper_doi: str) -> List[dict]:
        """
        获取引用该论文的论文（哪些论文引用了该论文）

        Args:
            paper_doi: 论文 DOI

        Returns:
            引用该论文的论文列表
        """
        cursor = self.execute_read("""
            SELECT * FROM paper_citations
            WHERE cited_paper_id = ?
            ORDER BY citing_year DESC
        """, (paper_doi,))

        return [dict(row) for row in cursor.fetchall()]

    def get_internal_edges(self) -> List[dict]:
        """
        获取内部引用边（两篇论文都在库中的引用关系）

        Returns:
            内部引用关系列表
        """
        cursor = self.execute_read("""
            SELECT * FROM paper_citations
            WHERE is_internal = 1
            ORDER BY cited_citation_count DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_all_edges(self) -> List[dict]:
        """
        获取所有引用边（用于可视化）

        Returns:
            所有引用关系列表，每条包含 source 和 target
        """
        cursor = self.execute_read("""
            SELECT
                citing_paper_id as source,
                cited_paper_id as target,
                citing_title,
                cited_title,
                is_internal
            FROM paper_citations
        """)

        return [dict(row) for row in cursor.fetchall()]

    def clear_paper_citations(self, paper_doi: str = None) -> int:
        """
        清除论文引用数据

        Args:
            paper_doi: 论文 DOI（可选，如果指定则只清除该论文的引用）

        Returns:
            删除的数量
        """
        if paper_doi:
            cursor = self.execute_write("""
                DELETE FROM paper_citations
                WHERE citing_paper_id = ? OR cited_paper_id = ?
            """, (paper_doi, paper_doi))
        else:
            cursor = self.execute_write("DELETE FROM paper_citations")

        return cursor.rowcount

    def count(self, paper_doi: str = None, is_internal: bool = None) -> int:
        """
        统计引用数量

        Args:
            paper_doi: 论文 DOI（可选）
            is_internal: 是否内部引用（可选）

        Returns:
            引用数量
        """
        query = "SELECT COUNT(*) as count FROM paper_citations"
        params = []
        conditions = []

        if paper_doi:
            conditions.append("(citing_paper_id = ? OR cited_paper_id = ?)")
            params.extend([paper_doi, paper_doi])
        if is_internal is not None:
            conditions.append("is_internal = ?")
            params.append(1 if is_internal else 0)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor = self.execute_read(query, tuple(params))
        return cursor.fetchone()['count']

    def get_citation_stats(self, paper_doi: str) -> dict:
        """
        获取论文的引用统计

        Args:
            paper_doi: 论文 DOI

        Returns:
            统计字典，包含 outgoing（引用数）、incoming（被引用数）、internal（内部引用数）
        """
        # 引用数（该论文引用了多少论文）
        cursor = self.execute_read(
            "SELECT COUNT(*) as count FROM paper_citations WHERE citing_paper_id = ?",
            (paper_doi,)
        )
        outgoing = cursor.fetchone()['count']

        # 被引用数（有多少论文引用该论文）
        cursor = self.execute_read(
            "SELECT COUNT(*) as count FROM paper_citations WHERE cited_paper_id = ?",
            (paper_doi,)
        )
        incoming = cursor.fetchone()['count']

        # 内部引用数
        cursor = self.execute_read("""
            SELECT COUNT(*) as count FROM paper_citations
            WHERE (citing_paper_id = ? OR cited_paper_id = ?) AND is_internal = 1
        """, (paper_doi, paper_doi))
        internal = cursor.fetchone()['count']

        return {
            'outgoing': outgoing,
            'incoming': incoming,
            'internal': internal
        }