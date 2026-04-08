# backend/services/upload_service.py
"""
上传服务 - 论文上传处理
"""

import uuid
import shutil
from typing import List, Dict, Optional
from pathlib import Path
from fastapi import UploadFile

from mkg.database import Database


class UploadService:
    """论文上传服务"""

    def __init__(self, db: Database):
        self.db = db
        self.upload_dir = Path(__file__).parent.parent.parent / "papers"
        self.upload_dir.mkdir(exist_ok=True)

    async def upload_single(self, file: UploadFile, folder: str = "default") -> Dict:
        """上传单个论文 PDF"""
        # 生成唯一文件名
        file_id = str(uuid.uuid4())[:8]
        safe_filename = file.filename.replace("/", "_").replace("\\", "_")
        file_path = self.upload_dir / f"{file_id}_{safe_filename}"

        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 使用文件名作为临时 DOI
        doi = f"upload:{file_id}"

        # 添加到数据库
        self.db.papers.add({
            "doi": doi,
            "title": Path(file.filename).stem,
            "pdf_path": str(file_path),
            "status": "uploaded"
        })

        # 移动到指定文件夹
        if folder and folder != "default":
            self.db.papers.move_to_folder(doi, folder)

        return {
            "doi": doi,
            "title": Path(file.filename).stem,
            "filename": file.filename,
            "success": True
        }

    async def upload_batch(self, files: List[UploadFile], folder: str = "default") -> Dict:
        """批量上传论文"""
        job_id = str(uuid.uuid4())
        results = []

        for file in files:
            try:
                if file.filename.endswith('.pdf'):
                    result = await self.upload_single(file, folder)
                    results.append(result)
                else:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": "Not a PDF file"
                    })
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })

        return {
            "job_id": job_id,
            "uploaded": results,
            "total": len(results)
        }

    def get_batch_status(self, job_id: str) -> Optional[Dict]:
        """获取批处理状态"""
        cursor = self.db.execute_read(
            "SELECT * FROM batch_jobs WHERE id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None