# backend/routes/dedup.py
"""
去重路由 - 概念去重相关端点
"""


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import get_dedup_service
from ..services.dedup_service import DedupService

router = APIRouter(prefix="/api/concepts", tags=["dedup"])


class DedupScanRequest(BaseModel):
    """去重扫描请求"""
    folder_id: str | None = None


class DedupExecuteRequest(BaseModel):
    """去重执行请求"""
    scan_id: str
    merge_ids: list[str]


@router.post("/dedup/scan")
async def start_dedup_scan(
    request: DedupScanRequest,
    service: DedupService = Depends(get_dedup_service)
):
    """开始去重扫描"""
    result = service.start_scan(request.folder_id)
    return result


@router.get("/dedup/scan-status/{scan_id}")
def get_dedup_scan_status(
    scan_id: str,
    service: DedupService = Depends(get_dedup_service)
):
    """获取扫描状态"""
    status = service.get_scan_status(scan_id)
    if not status:
        raise HTTPException(status_code=404, detail="Scan not found")
    return status


@router.post("/dedup/execute")
def dedup_execute(
    request: DedupExecuteRequest,
    service: DedupService = Depends(get_dedup_service)
):
    """执行概念合并"""
    result = service.execute_merge(request.scan_id, request.merge_ids)
    return result
