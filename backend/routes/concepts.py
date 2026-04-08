# backend/routes/concepts.py
"""
概念基础 CRUD 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..dependencies import get_concept_service
from ..services.concept_service import ConceptService
from mkg.database import Database

router = APIRouter(prefix="/api/concepts", tags=["concepts"])


def get_db():
    db = Database("mkg.db")
    db.connect()
    return db


@router.get("/")
def list_concepts(service: ConceptService = Depends(get_concept_service)):
    """获取所有概念"""
    return service.list()


@router.get("/roots")
def get_root_concepts():
    """获取根概念列表"""
    db = get_db()
    roots = db.get_root_concepts()
    return roots


@router.get("/tree")
def get_concept_tree(root_id: Optional[str] = None):
    """获取概念树结构"""
    db = get_db()

    def build_tree(concept_id: str, depth: int = 0) -> dict:
        if depth > 10:
            return None

        concept = db.get_concept(concept_id)
        if not concept:
            return None

        node = {
            "id": concept['id'],
            "text": concept['text'],
            "category": concept.get('category'),
            "paper_count": concept.get('paper_count', 0),
            "children": []
        }

        children = db.get_concept_children(concept_id)
        for child in children:
            child_node = build_tree(child['id'], depth + 1)
            if child_node:
                node['children'].append(child_node)

        return node

    if root_id:
        tree = build_tree(root_id)
        return {"tree": tree}
    else:
        roots = db.get_root_concepts()
        trees = []
        for root in roots[:10]:  # Limit to 10 roots
            tree = build_tree(root['id'])
            if tree:
                trees.append(tree)
        return {"trees": trees}


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


@router.get("/{concept_id}/research-points")
def get_concept_research_points(concept_id: str):
    """获取概念的研究点"""
    db = get_db()

    concept = db.get_concept(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # 获取相关上下文
    children = db.get_concept_children(concept_id)
    papers = db.get_concept_papers(concept_id)

    # 简单返回结构化数据，实际研究点发现需要 LLM
    return {
        "concept_id": concept_id,
        "concept_text": concept['text'],
        "context": {
            "children_count": len(children),
            "papers_count": len(papers),
            "children": [{"id": c['id'], "text": c['text']} for c in children[:5]],
        },
        "research_points": []  # 需要通过 Agent 或 LLM 生成
    }