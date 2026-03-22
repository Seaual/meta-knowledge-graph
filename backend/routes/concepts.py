"""
Concept API routes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from meta_knowledge_graph.database import Database
from meta_knowledge_graph.graph import KnowledgeGraph
from .schemas import ConceptResponse, ConceptTreeNode, ConceptDetail

router = APIRouter(prefix="/api/concepts", tags=["concepts"])

_db = None
_graph = None


def get_db():
    global _db
    if _db is None:
        _db = Database("openclaw.db")
        _db.connect()
    return _db


def get_graph():
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph(get_db())
    return _graph


@router.get("/", response_model=List[ConceptResponse])
def list_concepts():
    """Get all concepts"""
    db = get_db()
    return db.get_all_concepts()


@router.get("/roots", response_model=List[ConceptResponse])
def get_root_concepts():
    """Get root concepts (no parents)"""
    db = get_db()
    return db.get_root_concepts()


@router.get("/tree")
def get_concept_tree(root_id: Optional[str] = None):
    """Get concept tree structure"""
    db = get_db()
    tree = db.get_concept_tree(root_id)
    return tree


@router.get("/search")
def search_concepts(q: str = Query(..., min_length=1)):
    """Search concepts by query"""
    graph = get_graph()
    return graph.search_concepts(q)


@router.get("/{concept_id}", response_model=ConceptDetail)
def get_concept(concept_id: str):
    """Get concept details with parents, children, and papers"""
    db = get_db()
    concept = db.get_concept(concept_id)

    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    parents = db.get_concept_parents(concept_id)
    children = db.get_concept_children(concept_id)
    papers = db.get_papers_by_concept(concept_id)

    return ConceptDetail(
        id=concept['id'],
        text=concept['text'],
        category=concept.get('category'),
        paper_count=concept.get('paper_count', 0),
        depth_cache=concept.get('depth_cache', -1),
        parents=parents,
        children=children,
        papers=[{"doi": p['doi'], "title": p['title']} for p in papers]
    )


@router.get("/{concept_id}/papers")
def get_concept_papers(concept_id: str, limit: int = 20):
    """Get papers associated with a concept"""
    db = get_db()
    papers = db.get_papers_by_concept(concept_id)
    return papers[:limit]


@router.get("/{concept_id}/children")
def get_concept_children(concept_id: str):
    """Get child concepts"""
    db = get_db()
    return db.get_concept_children(concept_id)


@router.get("/{concept_id}/parents")
def get_concept_parents(concept_id: str):
    """Get parent concepts"""
    db = get_db()
    return db.get_concept_parents(concept_id)