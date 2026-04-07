# mkg/repositories/paper_repo.py
"""
PaperRepository - 论文相关数据库操作
"""

from typing import Optional, Dict, List, Any
from .base import BaseRepository


class PaperRepository(BaseRepository):
    """论文数据访问层"""

    # ========== CRUD 方法 ==========

    def add(self, paper_data: dict) -> str:
        """
        添加或更新论文

        Args:
            paper_data: 论文数据字典，包含 doi, title, abstract, authors 等

        Returns:
            论文的 DOI
        """
        # 检查是否已存在（通过 DOI）
        cursor = self.execute_read(
            "SELECT doi FROM papers WHERE doi = ?",
            (paper_data.get('doi'),)
        )
        existing = cursor.fetchone()

        if existing:
            # 更新
            self.execute_write("""
                UPDATE papers SET
                    title = ?, abstract = ?, authors = ?,
                    keywords = ?, contributions = ?,
                    pdf_path = ?, published_date = ?,
                    s2_paper_id = ?, venue = ?, year = ?,
                    citation_count = ?, reference_count = ?, influential_citation_count = ?,
                    open_access_pdf = ?, s2_doi = ?, s2_arxiv_id = ?, s2_external_ids = ?,
                    tldr = ?, s2_fields_of_study = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE doi = ?
            """, (
                paper_data.get('title'),
                paper_data.get('abstract'),
                self._serialize_json(paper_data.get('authors', [])),
                self._serialize_json(paper_data.get('keywords', [])),
                self._serialize_json(paper_data.get('contributions', [])),
                paper_data.get('pdf_path'),
                paper_data.get('published'),
                paper_data.get('s2_paper_id'),
                paper_data.get('venue'),
                paper_data.get('year'),
                paper_data.get('citation_count'),
                paper_data.get('reference_count'),
                paper_data.get('influential_citation_count'),
                paper_data.get('open_access_pdf'),
                paper_data.get('s2_doi'),
                paper_data.get('s2_arxiv_id'),
                paper_data.get('s2_external_ids'),
                paper_data.get('tldr'),
                paper_data.get('s2_fields_of_study'),
                paper_data.get('doi')
            ))
            doi = existing['doi']
        else:
            # 插入
            doi = paper_data.get('doi', paper_data.get('arxiv_id'))
            self.execute_write("""
                INSERT INTO papers (doi, arxiv_id, title, abstract, authors, keywords, contributions,
                    pdf_path, published_date, status, s2_paper_id, venue, year, citation_count,
                    reference_count, influential_citation_count, open_access_pdf, s2_doi, s2_arxiv_id,
                    s2_external_ids, tldr, s2_fields_of_study)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doi,
                paper_data.get('arxiv_id'),
                paper_data.get('title'),
                paper_data.get('abstract'),
                self._serialize_json(paper_data.get('authors', [])),
                self._serialize_json(paper_data.get('keywords', [])),
                self._serialize_json(paper_data.get('contributions', [])),
                paper_data.get('pdf_path'),
                paper_data.get('published'),
                paper_data.get('s2_paper_id'),
                paper_data.get('venue'),
                paper_data.get('year'),
                paper_data.get('citation_count'),
                paper_data.get('reference_count'),
                paper_data.get('influential_citation_count'),
                paper_data.get('open_access_pdf'),
                paper_data.get('s2_doi'),
                paper_data.get('s2_arxiv_id'),
                paper_data.get('s2_external_ids'),
                paper_data.get('tldr'),
                paper_data.get('s2_fields_of_study'),
            ))

        return doi

    def get(self, identifier: str) -> Optional[dict]:
        """
        获取论文（支持 DOI、arXiv ID 或 S2 Paper ID）

        Args:
            identifier: 论文标识符（DOI、arXiv ID 或 S2 Paper ID）

        Returns:
            论文字典，或 None
        """
        cursor = self.execute_read("""
            SELECT * FROM papers WHERE doi = ? OR arxiv_id = ? OR s2_paper_id = ?
        """, (identifier, identifier, identifier))
        row = cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        return None

    def get_all(self, folder_id: str = None, status: str = None) -> List[dict]:
        """
        获取所有论文，可选按文件夹或状态过滤

        Args:
            folder_id: 文件夹 ID（可选）
            status: 状态过滤（可选）

        Returns:
            论文列表
        """
        query = "SELECT * FROM papers"
        params = []
        conditions = []

        if folder_id:
            conditions.append("folder_id = ?")
            params.append(folder_id)
        if status:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        cursor = self.execute_read(query, tuple(params))
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_all_basic(self) -> List[Dict]:
        """
        获取所有论文的基本信息（用于引用图谱）

        Returns:
            论文基本信息列表（doi, title, s2_paper_id, citation_count, year, venue）
        """
        cursor = self.execute_read("""
            SELECT doi, title, s2_paper_id, citation_count, year, venue
            FROM papers
            ORDER BY citation_count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_by_status(self, status: str) -> List[dict]:
        """
        按状态获取论文列表

        Args:
            status: 论文状态（pending/downloaded/processed/failed）

        Returns:
            论文列表
        """
        cursor = self.execute_read(
            "SELECT * FROM papers WHERE status = ?",
            (status,)
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_by_folder(self, folder_id: str) -> List[dict]:
        """
        按文件夹获取论文

        Args:
            folder_id: 文件夹 ID

        Returns:
            论文列表
        """
        cursor = self.execute_read(
            "SELECT * FROM papers WHERE folder_id = ? ORDER BY created_at DESC",
            (folder_id,)
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_by_s2_id(self, s2_paper_id: str) -> Optional[dict]:
        """
        通过 S2 Paper ID 获取论文

        Args:
            s2_paper_id: Semantic Scholar Paper ID

        Returns:
            论文字典，或 None
        """
        cursor = self.execute_read(
            "SELECT * FROM papers WHERE s2_paper_id = ?",
            (s2_paper_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        return None

    def get_with_s2_id(self) -> List[Dict]:
        """
        获取所有有 S2 Paper ID 的论文

        Returns:
            论文列表（doi, title, s2_paper_id, citation_count, year, venue）
        """
        cursor = self.execute_read("""
            SELECT doi, title, s2_paper_id, citation_count, year, venue
            FROM papers
            WHERE s2_paper_id IS NOT NULL
            ORDER BY citation_count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def update_status(self, doi: str, status: str, error_message: str = None):
        """
        更新论文处理状态

        Args:
            doi: 论文 DOI
            status: 新状态
            error_message: 错误信息（可选）
        """
        self.execute_write("""
            UPDATE papers SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (status, error_message, doi))

    def update_metadata(self, doi: str, metadata: dict):
        """
        更新论文元数据（作者、摘要、关键词、创新点、S2元数据等）

        Args:
            doi: 论文 DOI
            metadata: 元数据字典
        """
        self.execute_write("""
            UPDATE papers SET
                title = COALESCE(?, title),
                abstract = COALESCE(?, abstract),
                authors = COALESCE(?, authors),
                keywords = COALESCE(?, keywords),
                contributions = COALESCE(?, contributions),
                s2_paper_id = COALESCE(?, s2_paper_id),
                s2_doi = COALESCE(?, s2_doi),
                citation_count = COALESCE(?, citation_count),
                reference_count = COALESCE(?, reference_count),
                influential_citation_count = COALESCE(?, influential_citation_count),
                venue = COALESCE(?, venue),
                year = COALESCE(?, year),
                tldr = COALESCE(?, tldr),
                s2_fields_of_study = COALESCE(?, s2_fields_of_study),
                open_access_pdf_url = COALESCE(?, open_access_pdf_url),
                s2_matched_at = COALESCE(?, s2_matched_at),
                updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (
            metadata.get('title'),
            metadata.get('abstract'),
            self._serialize_json(metadata.get('authors')) if metadata.get('authors') else None,
            self._serialize_json(metadata.get('keywords')) if metadata.get('keywords') else None,
            self._serialize_json(metadata.get('contributions')) if metadata.get('contributions') else None,
            metadata.get('s2_paper_id'),
            metadata.get('s2_doi'),
            metadata.get('citation_count'),
            metadata.get('reference_count'),
            metadata.get('influential_citation_count'),
            metadata.get('venue'),
            metadata.get('year'),
            metadata.get('tldr'),
            metadata.get('s2_fields_of_study'),
            metadata.get('open_access_pdf_url'),
            metadata.get('s2_matched_at'),
            doi
        ))

    def update_s2_metadata(self, doi: str, metadata: dict):
        """
        更新论文的 S2 元数据（Semantic Scholar 相关字段）

        Args:
            doi: 论文 DOI
            metadata: S2 元数据字典
        """
        self.execute_write("""
            UPDATE papers SET
                s2_paper_id = COALESCE(?, s2_paper_id),
                s2_doi = COALESCE(?, s2_doi),
                citation_count = COALESCE(?, citation_count),
                reference_count = COALESCE(?, reference_count),
                influential_citation_count = COALESCE(?, influential_citation_count),
                venue = COALESCE(?, venue),
                year = COALESCE(?, year),
                tldr = COALESCE(?, tldr),
                s2_fields_of_study = COALESCE(?, s2_fields_of_study),
                open_access_pdf_url = COALESCE(?, open_access_pdf_url),
                s2_matched_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (
            metadata.get('s2_paper_id'),
            metadata.get('s2_doi'),
            metadata.get('citation_count'),
            metadata.get('reference_count'),
            metadata.get('influential_citation_count'),
            metadata.get('venue'),
            metadata.get('year'),
            metadata.get('tldr'),
            metadata.get('s2_fields_of_study'),
            metadata.get('open_access_pdf_url'),
            doi
        ))

    def add_pdf_path(self, doi: str, pdf_path: str):
        """
        更新 PDF 路径并设置状态为 downloaded

        Args:
            doi: 论文 DOI
            pdf_path: PDF 文件路径
        """
        self.execute_write("""
            UPDATE papers SET pdf_path = ?, status = 'downloaded', updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (pdf_path, doi))

    def move_to_folder(self, doi: str, folder_id: str):
        """
        移动论文到指定文件夹

        Args:
            doi: 论文 DOI
            folder_id: 目标文件夹 ID
        """
        self.execute_write(
            "UPDATE papers SET folder_id = ? WHERE doi = ?",
            (folder_id, doi)
        )

    def delete(self, doi: str):
        """
        删除论文（仅删除论文记录，不删除关联的概念）

        Args:
            doi: 论文 DOI

        Note:
            如果需要删除关联概念，使用 delete_cascade 方法
        """
        self.execute_write("DELETE FROM papers WHERE doi = ?", (doi,))

    def delete_cascade(self, doi: str):
        """
        删除论文及其孤立的概念节点

        Args:
            doi: 论文 DOI

        工作流程:
            1. 获取该论文关联的所有概念
            2. 删除 paper_concepts 关联
            3. 对每个概念，检查是否有其他论文引用
            4. 如果没有，删除该概念并递归检查子概念
            5. 清理 concept_relations 记录
        """
        # 获取该论文关联的概念
        cursor = self.execute_read(
            "SELECT concept_id FROM paper_concepts WHERE paper_doi = ?",
            (doi,)
        )
        concepts = [row['concept_id'] for row in cursor.fetchall()]

        # 删除 paper_concepts 关联
        self.execute_write(
            "DELETE FROM paper_concepts WHERE paper_doi = ?",
            (doi,)
        )

        # 删除 concept_extractions
        self.execute_write(
            "DELETE FROM concept_extractions WHERE paper_doi = ?",
            (doi,)
        )

        # 删除 processing_log
        self.execute_write(
            "DELETE FROM processing_log WHERE paper_doi = ?",
            (doi,)
        )

        # 删除 paper_citations 相关记录
        self.execute_write(
            "DELETE FROM paper_citations WHERE citing_paper_id = ? OR cited_paper_id = ?",
            (doi, doi)
        )

        # 删除论文
        self.execute_write("DELETE FROM papers WHERE doi = ?", (doi,))

        # 检查并删除孤立概念
        for concept_id in concepts:
            cursor = self.execute_read(
                "SELECT COUNT(*) as count FROM paper_concepts WHERE concept_id = ?",
                (concept_id,)
            )
            count = cursor.fetchone()['count']

            if count == 0:
                # 没有其他论文引用，删除该概念
                self._delete_concept_cascade(concept_id)

    def _delete_concept_cascade(self, concept_id: str):
        """递归删除概念及其子概念（如果子概念也孤立）"""
        # 删除与该概念的关系
        self.execute_write(
            "DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?",
            (concept_id, concept_id)
        )

        # 删除概念
        self.execute_write("DELETE FROM concepts WHERE id = ?", (concept_id,))

    # ========== 概念关联 ==========

    def get_concepts(self, paper_doi: str) -> List[dict]:
        """
        获取论文关联的所有概念

        Args:
            paper_doi: 论文 DOI

        Returns:
            概念列表
        """
        cursor = self.execute_read("""
            SELECT c.* FROM concepts c
            JOIN paper_concepts pk ON c.id = pk.concept_id
            WHERE pk.paper_doi = ?
            ORDER BY pk.confidence DESC
        """, (paper_doi,))
        return [dict(row) for row in cursor.fetchall()]

    def get_contribution(self, doi: str) -> dict:
        """
        获取论文贡献的概念节点数和根概念

        Args:
            doi: 论文 DOI

        Returns:
            包含 node_count 和 root_concept 的字典
        """
        # 获取该论文关联的概念数
        cursor = self.execute_read(
            "SELECT COUNT(*) as count FROM paper_concepts WHERE paper_doi = ?",
            (doi,)
        )
        node_count = cursor.fetchone()['count']

        # 获取根概念（该论文的概念树的根）
        cursor = self.execute_read("""
            SELECT c.text FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            LEFT JOIN concept_relations cr ON c.id = cr.child_id
            WHERE pc.paper_doi = ? AND cr.parent_id IS NULL
            LIMIT 1
        """, (doi,))
        row = cursor.fetchone()
        root_concept = row['text'] if row else None

        return {
            'node_count': node_count,
            'root_concept': root_concept
        }

    def add_concept_link(self, paper_doi: str, concept_id: str,
                         confidence: float = 1.0, source: str = 'llm',
                         is_anchor: bool = False, contribution_role: str = None):
        """
        添加论文 - 概念关联

        Args:
            paper_doi: 论文 DOI
            concept_id: 概念 ID
            confidence: 置信度（默认 1.0）
            source: 来源（llm/author/extracted）
            is_anchor: 是否为锚点概念
            contribution_role: 贡献角色
        """
        self.execute_write("""
            INSERT OR IGNORE INTO paper_concepts
                (paper_doi, concept_id, confidence, source, is_anchor, contribution_role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (paper_doi, concept_id, confidence, source, 1 if is_anchor else 0, contribution_role))

        # 更新概念的 paper_count
        self.execute_write("""
            UPDATE concepts SET paper_count = (
                SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?
            ) WHERE id = ?
        """, (concept_id, concept_id))

    def remove_concept_link(self, paper_doi: str, concept_id: str):
        """
        移除论文 - 概念关联

        Args:
            paper_doi: 论文 DOI
            concept_id: 概念 ID
        """
        self.execute_write("""
            DELETE FROM paper_concepts WHERE paper_doi = ? AND concept_id = ?
        """, (paper_doi, concept_id))

        # 更新概念的 paper_count
        self.execute_write("""
            UPDATE concepts SET paper_count = (
                SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?
            ) WHERE id = ?
        """, (concept_id, concept_id))

    # ========== 处理日志 ==========

    def log_processing(self, paper_doi: str, action: str, status: str, message: str = None):
        """
        记录处理日志

        Args:
            paper_doi: 论文 DOI
            action: 操作类型（download/extract/build_graph）
            status: 状态（success/failed）
            message: 日志消息（可选）
        """
        self.execute_write("""
            INSERT INTO processing_log (paper_doi, action, status, message)
            VALUES (?, ?, ?, ?)
        """, (paper_doi, action, status, message))

    def get_processing_logs(self, paper_doi: str) -> List[dict]:
        """
        获取论文的处理日志

        Args:
            paper_doi: 论文 DOI

        Returns:
            日志列表
        """
        cursor = self.execute_read("""
            SELECT * FROM processing_log
            WHERE paper_doi = ?
            ORDER BY created_at DESC
        """, (paper_doi,))
        return [dict(row) for row in cursor.fetchall()]

    # ========== 统计 ==========

    def count(self, folder_id: str = None, status: str = None) -> int:
        """
        获取论文数量，可选按文件夹或状态过滤

        Args:
            folder_id: 文件夹 ID（可选）
            status: 状态过滤（可选）

        Returns:
            论文数量
        """
        query = "SELECT COUNT(*) as count FROM papers"
        params = []
        conditions = []

        if folder_id:
            conditions.append("folder_id = ?")
            params.append(folder_id)
        if status:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor = self.execute_read(query, tuple(params))
        return cursor.fetchone()['count']

    def count_by_status(self) -> Dict[str, int]:
        """
        按状态统计论文数量

        Returns:
            状态 -> 数量的字典
        """
        cursor = self.execute_read("""
            SELECT status, COUNT(*) as count FROM papers GROUP BY status
        """)
        return {row['status']: row['count'] for row in cursor.fetchall()}

    # ========== 私有方法 ==========

    def _row_to_dict(self, row: Any) -> dict:
        """
        转换数据库行到字典，处理 JSON 字段

        Args:
            row: sqlite3.Row 对象

        Returns:
            论文字典
        """
        paper = dict(row)

        # Deserialize JSON fields
        paper['authors'] = self._deserialize_json(paper.get('authors'), [])
        paper['keywords'] = self._deserialize_json(paper.get('keywords'), [])
        paper['contributions'] = self._deserialize_json(paper.get('contributions'), [])
        paper['s2_fields_of_study'] = self._deserialize_json(paper.get('s2_fields_of_study'), [])

        # Handle open_access_pdf (may be JSON string or None)
        if paper.get('open_access_pdf'):
            paper['open_access_pdf'] = self._deserialize_json(paper.get('open_access_pdf'))

        return paper