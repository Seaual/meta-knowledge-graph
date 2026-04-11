# backend/services/process_service.py
"""
处理服务 - PDF 解析和概念提取
"""

from mkg.database import Database
from mkg.pdf_parser import PDFParser


class ProcessService:
    """论文处理服务 - PDF 解析和概念提取"""

    def __init__(self, db: Database, pdf_parser: PDFParser):
        self.db = db
        self.pdf_parser = pdf_parser

    def process_paper(self, doi: str) -> dict:
        """处理单篇论文 - 提取概念"""
        paper = self.db.papers.get(doi)
        if not paper:
            return {"success": False, "error": "Paper not found", "doi": doi}

        if not paper.get('pdf_path'):
            return {"success": False, "error": "No PDF path", "doi": doi}

        try:
            # 更新状态
            self.db.papers.update_status(doi, "processing")

            # 初始化 LLM
            from mkg.llm import init_llm_from_db
            init_llm_from_db(self.db)

            # 提取概念
            from mkg.pdf_parser import LLMConceptExtractor
            extractor = LLMConceptExtractor()

            # 从 PDF 解析器获取完整论文内容（包含 title, authors, abstract, sections 等）
            paper_content = self.pdf_parser.parse(paper['pdf_path'])
            if not paper_content:
                raise Exception("Failed to parse PDF")

            hierarchy = extractor.extract(paper_content)

            # 保存概念
            self._save_concepts(doi, hierarchy)

            # 更新状态
            self.db.papers.update_status(doi, "processed")

            return {
                "success": True,
                "doi": doi,
                "message": "Paper processed successfully",
                "concepts_count": self._count_concepts(hierarchy)
            }

        except Exception as e:
            self.db.papers.update_status(doi, "failed", str(e))
            return {"success": False, "error": str(e), "doi": doi}

    def _save_concepts(self, doi: str, hierarchy: dict):
        """保存提取的概念到数据库"""
        def save_node(node, parent_id=None):
            # 添加概念
            concept_id = self.db.concepts.add({
                "text": node.get("name", node.get("text", "")),
                "category": node.get("category")
            })

            # 添加关系
            if parent_id:
                self.db.concepts.add_relation(parent_id, concept_id)

            # 添加论文关联
            self.db.concepts.add_paper_concept(doi, concept_id)

            # 递归处理子节点
            for child in node.get("children", []):
                save_node(child, concept_id)

        if hierarchy:
            save_node(hierarchy)

    def _count_concepts(self, hierarchy: dict) -> int:
        """统计概念数量"""
        if not hierarchy:
            return 0
        count = 1
        for child in hierarchy.get("children", []):
            count += self._count_concepts(child)
        return count

    def process_batch(self, dois: list[str]) -> dict:
        """批量处理论文"""
        results = []
        successful = 0
        failed = 0

        for doi in dois:
            result = self.process_paper(doi)
            results.append(result)
            if result.get("success"):
                successful += 1
            else:
                failed += 1

        return {
            "total": len(dois),
            "successful": successful,
            "failed": failed,
            "results": results
        }
