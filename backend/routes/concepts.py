# backend/routes/concepts.py
"""
概念基础 CRUD 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_concept_service, get_language
from ..services.concept_service import ConceptService
from ..services.concept_translation import translate_concept_if_needed
from ..services.localization import localize_concept, localize_concept_list

router = APIRouter(prefix="/api/concepts", tags=["concepts"])


@router.get("/")
def list_concepts(service: ConceptService = Depends(get_concept_service)):
    """获取所有概念"""
    lang = get_language()
    return localize_concept_list(service.list(), lang)


@router.get("/search")
def search_concepts(
    q: str = Query(..., min_length=1),
    service: ConceptService = Depends(get_concept_service)
):
    """搜索概念"""
    lang = get_language()
    return localize_concept_list(service.search(q), lang)


@router.get("/{concept_id}")
def get_concept(
    concept_id: str,
    service: ConceptService = Depends(get_concept_service)
):
    """获取单个概念"""
    concept = service.get(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # English user requesting concept missing English name -> auto-translate
    lang = get_language()
    if lang == "en" and not concept.get("text_en"):
        translate_concept_if_needed(concept, service.db)
        concept = service.get(concept_id)  # Re-fetch updated concept

    return localize_concept(concept, lang)


@router.get("/{concept_id}/papers")
def get_concept_papers(
    concept_id: str,
    limit: int = 20,
    service: ConceptService = Depends(get_concept_service)
):
    """获取概念关联的论文"""
    papers = service.get_papers(concept_id, limit)
    return {"concept_id": concept_id, "papers": papers, "total": len(papers)}
