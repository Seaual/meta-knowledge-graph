# backend/dependencies.py
"""
依赖注入配置 - 提供服务和资源实例
"""

from pathlib import Path
from typing import Optional

# 延迟导入避免循环依赖
_db_instance = None
_s2_client = None
_pdf_parser = None


def get_db():
    """获取数据库实例（单例）"""
    global _db_instance
    if _db_instance is None:
        from mkg.database import Database
        db_path = Path(__file__).parent.parent / "mkg.db"
        _db_instance = Database(str(db_path))
        _db_instance.connect()
    return _db_instance


def get_s2_client():
    """获取 Semantic Scholar 客户端（单例）"""
    global _s2_client
    if _s2_client is None:
        from mkg.semantic_scholar import S2Client
        # 从数据库获取 API Key
        db = get_db()
        s2_config = db.config.get_s2_config()
        api_key = s2_config.get('api_key') if s2_config else None
        _s2_client = S2Client(api_key=api_key)
    return _s2_client


def get_pdf_parser():
    """获取 PDF 解析器（单例）"""
    global _pdf_parser
    if _pdf_parser is None:
        from mkg.pdf_parser import PDFParser
        _pdf_parser = PDFParser()
    return _pdf_parser


# ========== Service Factories ==========

def get_paper_service():
    """获取 PaperService 实例"""
    from .services.paper_service import PaperService
    return PaperService(get_db())


def get_upload_service():
    """获取 UploadService 实例"""
    from .services.upload_service import UploadService
    return UploadService(get_db())


def get_process_service():
    """获取 ProcessService 实例"""
    from .services.process_service import ProcessService
    return ProcessService(get_db(), get_pdf_parser())


def get_concept_service():
    """获取 ConceptService 实例"""
    from .services.concept_service import ConceptService
    return ConceptService(get_db())


def get_dedup_service():
    """获取 DedupService 实例"""
    from .services.dedup_service import DedupService
    return DedupService(get_db())


def get_research_service():
    """获取 ResearchService 实例"""
    from .services.research_service import ResearchService
    return ResearchService(get_db(), get_s2_client())