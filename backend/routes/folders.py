"""
Folder API routes
"""

from fastapi import APIRouter, HTTPException

from backend.dependencies import get_db
from backend.schemas import FolderCreate, FolderResponse, FolderUpdate

router = APIRouter(prefix="/api/folders", tags=["folders"])


@router.get("/", response_model=list[FolderResponse])
def list_folders():
    """获取所有文件夹"""
    db = get_db()
    folders = db.get_all_folders()

    # 计算每个文件夹的论文数
    for folder in folders:
        papers = db.get_papers_by_folder(folder["id"])
        folder["paper_count"] = len(papers)

    return folders


@router.post("/", response_model=FolderResponse)
def create_folder(request: FolderCreate):
    """创建文件夹"""
    db = get_db()
    folder_id = db.create_folder(request.model_dump())
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=500, detail="Failed to create folder")
    folder["paper_count"] = 0
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
    folder["paper_count"] = len(papers)
    return folder


@router.delete("/{folder_id}")
def delete_folder(folder_id: str, delete_contents: bool = True):
    """删除文件夹

    Args:
        folder_id: 文件夹ID
        delete_contents: 如果为 True（默认），删除文件夹中的论文和图谱；
                        如果为 False，将论文移动到默认文件夹

    Returns:
        删除结果
    """
    db = get_db()

    if folder_id == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default folder")

    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    success = db.delete_folder(folder_id, delete_contents=delete_contents)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete folder")

    if delete_contents:
        return {"success": True, "message": "Folder and its contents deleted"}
    else:
        return {"success": True, "message": "Folder deleted, papers moved to default"}
