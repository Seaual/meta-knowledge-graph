"""
Folder API routes
"""

from fastapi import APIRouter, HTTPException
from typing import List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database
from backend.schemas import FolderResponse, FolderCreate, FolderUpdate

router = APIRouter(prefix="/api/folders", tags=["folders"])

_db = None


def get_db():
    global _db
    if _db is None:
        _db = Database("openclaw.db")
        _db.connect()
    return _db


@router.get("/", response_model=List[FolderResponse])
def list_folders():
    """获取所有文件夹"""
    db = get_db()
    folders = db.get_all_folders()

    # 计算每个文件夹的论文数
    for folder in folders:
        papers = db.get_papers_by_folder(folder['id'])
        folder['paper_count'] = len(papers)

    return folders


@router.post("/", response_model=FolderResponse)
def create_folder(request: FolderCreate):
    """创建文件夹"""
    db = get_db()
    folder_id = db.create_folder(request.model_dump())
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=500, detail="Failed to create folder")
    folder['paper_count'] = 0
    return folder


@router.patch("/{folder_id}", response_model=FolderResponse)
def update_folder(folder_id: str, request: FolderUpdate):
    """更新文件夹"""
    db = get_db()
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    db.update_folder(folder_id, request.model_dump(exclude_none=True))
    folder = db.get_folder(folder_id)
    papers = db.get_papers_by_folder(folder_id)
    folder['paper_count'] = len(papers)
    return folder


@router.delete("/{folder_id}")
def delete_folder(folder_id: str):
    """删除文件夹（论文移到 default）"""
    db = get_db()

    if folder_id == 'default':
        raise HTTPException(status_code=400, detail="Cannot delete default folder")

    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    success = db.delete_folder(folder_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete folder")

    return {"success": True, "message": "Folder deleted, papers moved to default"}