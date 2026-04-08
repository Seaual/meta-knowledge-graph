# backend/routes/concepts.py
"""
概念基础 CRUD 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_concept_service
from ..services.concept_service import ConceptService

router = APIRouter(prefix="/api/concepts", tags=["concepts"])


@router.get("/")
def list_concepts(service: ConceptService = Depends(get_concept_service)):
    """获取所有概念"""
    return service.list()


@router.get("/search")
def search_concepts(
    q: str = Query(..., min_length=1),
    service: ConceptService = Depends(get_concept_service)
):
    """搜索概念"""
    return service.search(q)


@router.get("/{concept_id}")
def get_concept(
    concept_id: str,
    service: ConceptService = Depends(get_concept_service)
):
    """获取单个概念"""
    concept = service.get(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return concept


@router.get("/{concept_id}/papers")
def get_concept_papers(
    concept_id: str,
    limit: int = 20,
    service: ConceptService = Depends(get_concept_service)
):
    """获取概念关联的论文"""
    papers = service.get_papers(concept_id, limit)
    return {"concept_id": concept_id, "papers": papers, "total": len(papers)}