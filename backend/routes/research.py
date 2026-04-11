# backend/routes/research.py
"""
自演化研究 API 路由

提供从知识图谱发现到论文生成的完整研究流水线
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mkg.agent.evolution_graph import (
    get_evolution_progress,
    run_evolution_research,
    start_evolution_research_sync,
)

router = APIRouter(prefix="/api/research", tags=["research"])


# ============================================================
# 请求/响应模型
# ============================================================

class StartResearchRequest(BaseModel):
    concept_id: str
    mode: str = "auto"  # auto | co-pilot


class ResearchResponse(BaseModel):
    run_id: str
    status: str
    message: str


class ProgressResponse(BaseModel):
    run_id: str
    status: str
    current_stage: str
    progress: int
    stages_completed: list[str]
    data: dict


class PaperResponse(BaseModel):
    run_id: str
    status: str
    paper: str
    hypothesis: dict | None
    review: dict | None


# ============================================================
# API 端点
# ============================================================

@router.post("/start", response_model=ResearchResponse)
async def start_research(request: StartResearchRequest):
    """
    启动自演化研究流程
    
    从知识图谱中的概念出发，自动生成研究假设，完成文献调研、
    实验设计、论文撰写和评审验证。
    """
    # 依赖注入通过 Depends 获取（由 main.py 配置）
    from backend.dependencies import get_db
    db = get_db()
    
    if not db:
        raise HTTPException(status_code=500, detail="数据库未初始化")
    
    # 验证概念存在
    concept = db.get_concept_by_id(request.concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail=f"概念不存在: {request.concept_id}")
    
    try:
        run_id = start_evolution_research_sync(
            db=db,
            concept_id=request.concept_id,
            mode=request.mode,
        )
        
        return ResearchResponse(
            run_id=run_id,
            status="running",
            message="研究已启动，可通过 /api/research/{run_id}/status 查看进度",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}/status", response_model=ProgressResponse)
async def get_research_status(run_id: str):
    """查询研究进度"""
    progress = get_evolution_progress(run_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail=f"未找到运行记录: {run_id}")
    
    return ProgressResponse(
        run_id=run_id,
        status=progress["status"],
        current_stage=progress.get("current_stage", ""),
        progress=progress.get("progress", 0),
        stages_completed=progress.get("stages_completed", []),
        data=progress.get("data", {}),
    )


@router.get("/{run_id}/paper", response_model=PaperResponse)
async def get_paper(run_id: str):
    """获取生成的论文"""
    progress = get_evolution_progress(run_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail=f"未找到运行记录: {run_id}")
    
    data = progress.get("data", {})
    
    return PaperResponse(
        run_id=run_id,
        status=progress["status"],
        paper=data.get("paper", ""),
        hypothesis=data.get("best_hypothesis"),
        review=data.get("review"),
    )


@router.get("/list")
async def list_research_runs():
    """列出所有研究运行"""
    runs = []
    for run_id, progress in get_evolution_progress("").items() if False else {}.items():
        pass
    
    # 从内存中获取所有 run
    from mkg.agent.evolution_graph import _evolution_progress
    for run_id, progress in _evolution_progress.items():
        runs.append({
            "run_id": run_id,
            "status": progress["status"],
            "progress": progress["progress"],
            "current_stage": progress.get("current_stage", ""),
        })
    
    return {"runs": runs}
