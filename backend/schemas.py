"""
Pydantic schemas for API
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# Paper schemas
class PaperBase(BaseModel):
    doi: str
    title: str
    abstract: Optional[str] = None
    authors: List[str] = []
    keywords: List[str] = []
    contributions: List[str] = []
    published_date: Optional[str] = None
    pdf_path: Optional[str] = None
    status: str = "pending"


class PaperCreate(BaseModel):
    title: str
    abstract: Optional[str] = None
    authors: List[str] = []
    keywords: List[str] = []
    contributions: List[str] = []


class PaperResponse(PaperBase):
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# Concept schemas
class ConceptBase(BaseModel):
    id: str
    text: str
    category: Optional[str] = None
    paper_count: int = 0


class ConceptResponse(ConceptBase):
    depth_cache: int = -1

    class Config:
        from_attributes = True


class ConceptTreeNode(ConceptBase):
    children: List['ConceptTreeNode'] = []
    papers: List[dict] = []


class ConceptDetail(ConceptResponse):
    parents: List[ConceptResponse] = []
    children: List[ConceptResponse] = []
    papers: List[dict] = []


# Graph schemas
class GraphStats(BaseModel):
    papers: dict
    concepts: dict
    relations: int
    root_concepts: int


class GraphNode(BaseModel):
    id: str
    label: str
    category: str
    paper_count: int


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str = "parent-child"


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# Process schemas
class ProcessRequest(BaseModel):
    doi: str


class ProcessResponse(BaseModel):
    success: bool
    message: str
    concept_tree: Optional[dict] = None


# Skill submission schema
class SkillConceptSubmission(BaseModel):
    """Skill 提交的概念提取结果"""
    concept_tree: dict
    raw_response: Optional[str] = None