# backend/routes/concepts_tree.py
"""
概念树路由 - 树操作相关端点
"""

from fastapi import APIRouter, Depends

from ..dependencies import get_concept_service, get_language
from ..services.concept_service import ConceptService
from ..services.localization import localize_concept, localize_concept_list

router = APIRouter(prefix="/api/concepts", tags=["concepts-tree"])


@router.get("/roots")
def get_root_concepts(service: ConceptService = Depends(get_concept_service)):
    """获取根概念"""
    lang = get_language()
    return localize_concept_list(service.get_roots(), lang)


@router.get("/tree")
def get_concept_tree(
    root_id: str = None,
    service: ConceptService = Depends(get_concept_service)
):
    """获取概念树"""
    lang = get_language()
    tree = service.get_tree(root_id)

    def localize_tree_nodes(node, language):
        """递归本地化概念树中的每个节点"""
        if not node:
            return node
        localized = localize_concept(node, language)
        if "children" in localized:
            localized["children"] = [localize_tree_nodes(c, language) for c in localized["children"]]
        return localized

    return localize_tree_nodes(tree, lang)


@router.get("/{concept_id}/children")
def get_concept_children(
    concept_id: str,
    service: ConceptService = Depends(get_concept_service)
):
    """获取子概念"""
    lang = get_language()
    return localize_concept_list(service.get_children(concept_id), lang)


@router.get("/{concept_id}/parents")
def get_concept_parents(
    concept_id: str,
    service: ConceptService = Depends(get_concept_service)
):
    """获取父概念"""
    lang = get_language()
    return localize_concept_list(service.get_parents(concept_id), lang)
