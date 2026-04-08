# backend/routes/papers.py
"""
论文基础 CRUD 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from ..dependencies import get_paper_service
from ..services.paper_service import PaperService

router = APIRouter(prefix="/api/papers", tags=["papers"])


class PaperMetadataUpdate(BaseModel):
    """论文元数据更新"""
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[list] = None
    keywords: Optional[list] = None


class MovePaperRequest(BaseModel):
    """移动论文请求"""
    folder_id: str = "default"


@router.get("/")
def list_papers(
    status: Optional[str] = None,
    folder: Optional[str] = None,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文列表"""
    return service.list(status=status, folder=folder)


@router.get("/{doi:path}")
def get_paper(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取单个论文"""
    paper = service.get(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.delete("/{doi:path}")
def delete_paper(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """删除论文"""
    if not service.delete(doi):
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"status": "deleted", "doi": doi}


@router.patch("/{doi:path}/metadata")
def update_metadata(
    doi: str,
    update: PaperMetadataUpdate,
    service: PaperService = Depends(get_paper_service)
):
    """更新论文元数据"""
    if not service.update_metadata(doi, update.dict(exclude_unset=True)):
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"status": "updated", "doi": doi}


@router.get("/{doi:path}/text")
def get_paper_text(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文文本"""
    text = service.get_text(doi)
    if text is None:
        raise HTTPException(status_code=404, detail="Text not available")
    return {"text": text, "doi": doi}


@router.get("/{doi:path}/contribution")
def get_contribution(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文贡献统计"""
    return service.get_contribution(doi)


@router.patch("/{doi:path}/move")
def move_paper(
    doi: str,
    request: MovePaperRequest,
    service: PaperService = Depends(get_paper_service)
):
    """移动论文到文件夹"""
    if not service.move_to_folder(doi, request.folder_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"status": "moved", "doi": doi, "folder_id": request.folder_id}


@router.get("/{doi:path}/concepts")
def get_paper_concepts(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文关联的概念"""
    concepts = service.get_concepts(doi)
    return {"doi": doi, "concepts": concepts}