# backend/routes/papers_upload.py
"""
论文上传路由 - 上传和批处理相关端点
"""


from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..dependencies import get_upload_service
from ..services.upload_service import UploadService

router = APIRouter(prefix="/api/papers", tags=["papers-upload"])


@router.post("/upload")
async def upload_paper(
    file: UploadFile = File(...),
    folder: str = Form("default"),
    service: UploadService = Depends(get_upload_service)
):
    """上传单个论文 PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    result = await service.upload_single(file, folder)
    return {"success": True, **result}


@router.post("/batch-upload")
async def batch_upload_papers(
    files: list[UploadFile] = File(...),
    folder: str = Form("default"),
    service: UploadService = Depends(get_upload_service)
):
    """批量上传论文 PDF"""
    pdf_files = [f for f in files if f.filename.endswith('.pdf')]
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No PDF files found")

    result = await service.upload_batch(pdf_files, folder)
    return result


@router.get("/batch-status/{job_id}")
def get_batch_status(
    job_id: str,
    service: UploadService = Depends(get_upload_service)
):
    """获取批处理任务状态"""
    status = service.get_batch_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status
