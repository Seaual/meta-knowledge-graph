# backend/routes/concepts_research.py
"""
研究路由 - 研究点发现和论文推荐相关端点
"""


from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_research_service
from ..services.research_service import ResearchService

router = APIRouter(prefix="/api/concepts", tags=["concepts-research"])


@router.get("/{concept_id}/search-papers")
def search_papers_by_concept(
    concept_id: str,
    year: str | None = None,
    min_citations: int | None = None,
    limit: int = 10,
    service: ResearchService = Depends(get_research_service)
):
    """搜索概念相关论文"""
    result = service.search_papers_by_concept(concept_id, year, min_citations, limit)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{concept_id}/research-points")
def discover_research_points(
    concept_id: str,
    service: ResearchService = Depends(get_research_service)
):
    """发现概念的研究点"""
    result = service.discover_research_points(concept_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
