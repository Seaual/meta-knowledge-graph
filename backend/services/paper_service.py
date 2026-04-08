# backend/services/paper_service.py
"""
论文服务 - 论文 CRUD 操作
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from mkg.database import Database


class PaperService:
    """论文数据访问服务"""

    def __init__(self, db: Database):
        self.db = db

    def list(self, status: str = None, folder: str = None) -> List[Dict]:
        """获取论文列表"""
        return self.db.papers.get_all(folder_id=folder, status=status)

    def get(self, doi: str) -> Optional[Dict]:
        """获取单个论文"""
        return self.db.papers.get(doi)

    def get_by_folder(self, folder_id: str) -> List[Dict]:
        """获取文件夹中的论文"""
        return self.db.papers.get_by_folder(folder_id)

    def delete(self, doi: str) -> bool:
        """删除论文及其关联数据"""
        paper = self.db.papers.get(doi)
        if not paper:
            return False

        # 获取关联的概念
        concepts = self.db.papers.get_concepts(doi)

        # 删除论文（级联删除 paper_concepts）
        self.db.papers.delete_cascade(doi)

        # 清理孤立概念
        for concept in concepts:
            self.db.concepts._delete_orphaned(concept['id'])

        return True

    def update_metadata(self, doi: str, metadata: dict) -> bool:
        """更新论文元数据"""
        paper = self.db.papers.get(doi)
        if not paper:
            return False
        self.db.papers.update_metadata(doi, metadata)
        return True

    def move_to_folder(self, doi: str, folder_id: str) -> bool:
        """移动论文到文件夹"""
        paper = self.db.papers.get(doi)
        if not paper:
            return False
        self.db.papers.move_to_folder(doi, folder_id)
        return True

    def get_text(self, doi: str) -> Optional[str]:
        """获取论文文本"""
        paper = self.db.papers.get(doi)
        if not paper or not paper.get('pdf_path'):
            return None

        # 检查文件是否存在
        pdf_path = Path(paper['pdf_path'])
        if not pdf_path.exists():
            return None

        # 读取 PDF 文本
        from mkg.pdf_parser import PDFParser
        parser = PDFParser()
        try:
            return parser.extract_text(str(pdf_path))
        except Exception:
            return None

    def get_contribution(self, doi: str) -> Dict:
        """获取论文贡献统计"""
        return self.db.papers.get_contribution(doi)

    def get_concepts(self, doi: str) -> List[Dict]:
        """获取论文关联的概念"""
        return self.db.papers.get_concepts(doi)