"""
自演化研究 API 路由

提供从"研究点发现"到"论文生成"的完整流水线接口
"""

import asyncio
import sys
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.dependencies import get_db
from mkg.agent.evolution_graph import (
    get_evolution_progress,
    run_evolution_research,
)

router = APIRouter(prefix="/api/research", tags=["research"])

# 存储所有运行记录（内存）
_run_registry: dict[str, dict] = {}


class ResearchStartRequest(BaseModel):
    conceptId: str
    mode: str = "auto"  # auto | co-pilot


class ResearchStartResponse(BaseModel):
    runId: str
    status: str
    conceptId: str


class ResearchStatusResponse(BaseModel):
    runId: str
    status: str
    progress: int
    currentStage: int | None = None
    stageName: str | None = None
    details: dict | None = None
    error: str | None = None


class ResearchPaperResponse(BaseModel):
    runId: str
    status: str
    finalPaper: str | None = None
    reviewReport: dict | None = None
    selectedHypothesis: dict | None = None
    keyReferencesCount: int | None = None


@router.post("/start")
def start_research(request: ResearchStartRequest):
    """启动自演化研究任务（异步，后台运行）"""
    db = get_db()

    # 验证概念存在
    concept = db.get_concept(request.conceptId)
    if not concept:
        raise HTTPException(status_code=404, detail=f"概念不存在: {request.conceptId}")

    # 初始化 LLM
    from mkg.llm import init_llm_from_db
    init_llm_from_db(db)

    # 检查 LLM 配置
    llm_config = db.get_llm_config()
    if not llm_config or not llm_config.get("providers"):
        raise HTTPException(status_code=500, detail="LLM 未配置，请先在设置中配置 API Key")

    run_id = None  # 让系统自动生成

    # 注册运行记录
    _run_registry.setdefault(run_id or "pending", {
        "concept_id": request.conceptId,
        "mode": request.mode,
    })

    # 在后台线程运行
    def _run_evolution():
        nonlocal run_id
        try:
            result = asyncio.run(run_evolution_research(db, request.conceptId, run_id, request.mode))
            run_id = result.get("run_id", run_id)
            # 更新注册表
            if run_id:
                _run_registry[run_id] = {
                    "concept_id": request.conceptId,
                    "mode": request.mode,
                    "status": result.get("status", "unknown"),
                    "result": result,
                }
        except Exception as e:
            # 更新错误状态
            progress = get_evolution_progress(run_id) if run_id else None
            if progress:
                progress["status"] = "error"
                progress["error"] = str(e)
            if run_id:
                _run_registry[run_id] = {
                    "concept_id": request.conceptId,
                    "mode": request.mode,
                    "status": "error",
                    "error": str(e),
                }

    thread = threading.Thread(target=_run_evolution, daemon=True)
    thread.start()

    return ResearchStartResponse(
        runId=run_id or "pending",
        status="running",
        conceptId=request.conceptId,
    )


@router.get("/{run_id}/status")
def get_research_status(run_id: str):
    """获取研究任务进度"""
    progress = get_evolution_progress(run_id)

    if not progress:
        # 检查是否在注册表中
        registry_entry = _run_registry.get(run_id)
        if not registry_entry:
            raise HTTPException(status_code=404, detail="任务不存在")
        # 如果还在 pending 状态
        return {
            "runId": run_id,
            "status": "pending",
            "progress": 0,
        }

    return {
        "runId": progress.get("run_id", run_id),
        "status": progress.get("status", "unknown"),
        "progress": progress.get("progress", 0),
        "currentStage": progress.get("current_stage"),
        "stageName": progress.get("stage_name"),
        "details": progress.get("details"),
        "error": progress.get("error"),
    }


@router.get("/{run_id}/paper")
def get_research_paper(run_id: str):
    """获取研究论文"""
    progress = get_evolution_progress(run_id)

    if not progress:
        raise HTTPException(status_code=404, detail="任务不存在")

    if progress.get("status") == "error":
        raise HTTPException(status_code=500, detail=f"研究失败: {progress.get('error')}")

    if progress.get("status") != "completed":
        raise HTTPException(status_code=400, detail="研究尚未完成")

    # 从注册表获取完整结果
    registry_entry = _run_registry.get(run_id, {})
    result = registry_entry.get("result", {})

    return {
        "runId": run_id,
        "status": progress.get("status"),
        "finalPaper": result.get("final_paper", ""),
        "reviewReport": result.get("review_report"),
        "selectedHypothesis": result.get("selected_hypothesis"),
        "keyReferencesCount": result.get("key_references_count", 0),
        "paperSections": result.get("paper_sections", {}),
    }


@router.get("/list")
def list_research_runs():
    """列出所有研究运行"""
    runs = []
    for run_id, entry in _run_registry.items():
        progress = get_evolution_progress(run_id) or {}
        runs.append({
            "runId": run_id,
            "conceptId": entry.get("concept_id", ""),
            "mode": entry.get("mode", "auto"),
            "status": progress.get("status", entry.get("status", "unknown")),
            "progress": progress.get("progress", 0),
            "stageName": progress.get("stage_name"),
            "createdAt": progress.get("created_at"),
            "updatedAt": progress.get("updated_at"),
        })

    # 按更新时间倒序
    runs.sort(key=lambda r: r.get("updatedAt") or "", reverse=True)

    return {"runs": runs, "total": len(runs)}
