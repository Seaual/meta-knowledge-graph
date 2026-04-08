# backend/routes/papers_process.py
"""
论文处理路由 - PDF 解析和概念提取相关端点
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import httpx
from pathlib import Path

from ..dependencies import get_process_service, get_db
from ..services.process_service import ProcessService

router = APIRouter(prefix="/api/papers", tags=["papers-process"])


class ProcessRequest(BaseModel):
    """处理论文请求"""
    doi: str


class ProcessResponse(BaseModel):
    """处理论文响应"""
    success: bool
    message: str
    concept_tree: Optional[dict] = None
    duration: float = 0


class AddFromS2Request(BaseModel):
    """从 S2 添加论文请求"""
    s2_paper_id: str
    title: str
    year: Optional[int] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    tldr: Optional[str] = None
    open_access_pdf_url: Optional[str] = None


class DownloadAndProcessRequest(BaseModel):
    """下载并处理论文请求"""
    s2_paper_id: str
    title: str
    year: Optional[int] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    tldr: Optional[str] = None
    open_access_pdf_url: str


@router.post("/process", response_model=ProcessResponse)
def process_paper(
    request: ProcessRequest,
    service: ProcessService = Depends(get_process_service)
):
    """处理论文 - 提取概念"""
    result = service.process_paper(request.doi)
    return ProcessResponse(
        success=result.get("success", False),
        message=result.get("message", result.get("error", "")),
        concept_tree=None,
        duration=0
    )


@router.post("/process-batch")
def process_batch_papers(
    dois: List[str],
    service: ProcessService = Depends(get_process_service)
):
    """批量处理论文"""
    result = service.process_batch(dois)
    return result


@router.post("/add-from-s2")
def add_paper_from_s2(request: AddFromS2Request):
    """从 Semantic Scholar 添加论文（仅元数据）"""
    db = get_db()

    # 使用 S2 Paper ID 作为 DOI
    doi = f"s2:{request.s2_paper_id}"

    db.papers.add({
        "doi": doi,
        "title": request.title,
        "abstract": request.abstract,
        "authors": request.authors or [],
        "year": request.year,
        "venue": request.venue,
        "citation_count": request.citation_count,
        "tldr": request.tldr,
        "s2_paper_id": request.s2_paper_id,
        "status": "metadata_only"
    })

    return {
        "success": True,
        "message": "Paper metadata added",
        "doi": doi,
        "title": request.title
    }


@router.post("/download-and-process")
async def download_and_process_paper(request: DownloadAndProcessRequest):
    """下载 PDF 并处理"""
    pdf_dir = Path("papers")
    pdf_dir.mkdir(exist_ok=True)

    pdf_path = pdf_dir / f"{request.s2_paper_id}.pdf"

    # 下载 PDF
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(request.open_access_pdf_url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download PDF")

        with open(pdf_path, "wb") as f:
            f.write(response.content)

    # 添加到数据库
    db = get_db()
    doi = f"s2:{request.s2_paper_id}"

    db.papers.add({
        "doi": doi,
        "title": request.title,
        "abstract": request.abstract,
        "authors": request.authors or [],
        "year": request.year,
        "venue": request.venue,
        "citation_count": request.citation_count,
        "tldr": request.tldr,
        "s2_paper_id": request.s2_paper_id,
        "pdf_path": str(pdf_path),
        "status": "downloaded"
    })

    # 处理
    process_service = get_process_service()
    result = process_service.process_paper(doi)

    return {
        "success": result.get("success", False),
        "doi": doi,
        "title": request.title,
        "message": result.get("message", result.get("error", ""))
    }