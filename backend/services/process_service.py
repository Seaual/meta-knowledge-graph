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
        """处理单篇论文 - 提取概念 + DOI 匹配 + 元数据增强"""
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

            # ===== DOI 匹配与 S2 元数据增强 =====
            self._enhance_with_s2_metadata(doi, paper_content)

            extracted = extractor.extract(paper_content)

            # 将 ConceptTree 转换为 dict 供后续方法使用
            hierarchy = extracted.concept_tree.to_dict() if extracted.concept_tree else None

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

    def _enhance_with_s2_metadata(self, doi: str, paper_content) -> dict:
        """使用 S2 API 增强论文元数据（DOI/arXiv 精确匹配 + 标题回退）"""
        import logging
        from datetime import datetime

        from mkg.semantic_scholar import S2Client

        logger = logging.getLogger(__name__)

        # 获取 S2 API Key（数据库 → 硬编码 fallback → 环境变量）
        api_key = None
        s2_config = self.db.get_s2_config()
        if s2_config and s2_config.get("api_key"):
            api_key = s2_config["api_key"]

        if not api_key:
            try:
                import os
                api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
            except Exception:
                pass

        if not api_key:
            # 使用默认硬编码 Key（与 semantic_scholar.py 路由一致）
            api_key = "HdvhTeK6be5JUDCMKhwXa66QibQ2Qn171FL0Kkns"

        print(f"[S2增强] PDF解析DOI: '{paper_content.doi}'")
        print(f"[S2增强] PDF解析arXivID: '{paper_content.arxiv_id}'")
        print(f"[S2增强] PDF解析标题: '{paper_content.title}'")

        try:
            client = S2Client(api_key=api_key)

            # 使用 S2Client.match_paper，优先级：DOI > arXiv ID > 标题
            s2_result = client.match_paper(
                doi=paper_content.doi or None,
                arxiv_id=paper_content.arxiv_id or None,
                title=paper_content.title or None,
            )

            print(f"[S2增强] S2匹配结果: {s2_result}")

            if not s2_result:
                logger.info(f"S2 match failed for DOI={paper_content.doi}, title={paper_content.title}")
                return {"success": False, "reason": "s2_match_failed"}

            # 提取 externalIds 中的 DOI
            external_ids = s2_result.get("externalIds", {})
            matched_doi = external_ids.get("DOI", paper_content.doi)

            # 更新数据库
            self.db.papers.update_metadata(doi, {
                "title": s2_result.get("title") or paper_content.title,
                "abstract": s2_result.get("abstract") or paper_content.abstract,
                "authors": [a.get("name", "") for a in s2_result.get("authors", [])] or paper_content.authors,
                "s2_paper_id": s2_result.get("paperId"),
                "s2_doi": matched_doi,
                "citation_count": s2_result.get("citationCount", 0),
                "reference_count": s2_result.get("referenceCount", 0),
                "influential_citation_count": s2_result.get("influentialCitationCount", 0),
                "venue": s2_result.get("venue"),
                "year": s2_result.get("year"),
                "tldr": (s2_result.get("tldr") or {}).get("text"),
                "s2_fields_of_study": str(s2_result.get("s2FieldsOfStudy", [])),
                "open_access_pdf_url": (s2_result.get("openAccessPdf") or {}).get("url"),
                "s2_matched_at": datetime.now().isoformat(),
            })

            logger.info(f"S2 metadata enhanced: paperId={s2_result.get('paperId')}, doi={matched_doi}")
            print(f"[S2增强] 元数据更新成功: paperId={s2_result.get('paperId')}, doi={matched_doi}")
            return {"success": True, "s2_paper_id": s2_result.get("paperId"), "doi": matched_doi}

        except Exception as e:
            import traceback
            print(f"[S2增强] 异常: {e}")
            print(traceback.format_exc())
            logger.error(f"S2 metadata enhancement failed: {e}")
            return {"success": False, "reason": str(e)}

    def _save_concepts(self, doi: str, hierarchy: dict):
        """保存提取的概念到数据库"""
        def save_node(node, parent_id=None):
            # 添加概念（to_dict 返回 "concept" 字段）
            concept_id = self.db.concepts.add({
                "text": node.get("concept", ""),
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
