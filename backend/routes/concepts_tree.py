# backend/routes/concepts_tree.py
"""
概念树路由 - 树操作相关端点
"""

from fastapi import APIRouter, Depends

from ..dependencies import get_concept_service
from ..services.concept_service import ConceptService

router = APIRouter(prefix="/api/concepts", tags=["concepts-tree"])


@router.get("/roots")
def get_root_concepts(service: ConceptService = Depends(get_concept_service)):
    """获取根概念"""
    return service.get_roots()


@router.get("/tree")
def get_concept_tree(
    root_id: str = None,
    service: ConceptService = Depends(get_concept_service)
):
    """获取概念树"""
    return service.get_tree(root_id)


@router.get("/{concept_id}/children")
def get_concept_children(
    concept_id: str,
    service: ConceptService = Depends(get_concept_service)
):
    """获取子概念"""
    return service.get_children(concept_id)


@router.get("/{concept_id}/parents")
def get_concept_parents(
    concept_id: str,
    service: ConceptService = Depends(get_concept_service)
):
    """获取父概念"""
    return service.get_parents(concept_id)
