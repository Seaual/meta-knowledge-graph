"""
Semantic Scholar API 路由
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import sys
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database
from mkg.semantic_scholar import S2Client
from mkg.citation_graph import build_citation_graph, get_citation_context, get_citation_graph_data

router = APIRouter(prefix="/api", tags=["s2"])

# Semantic Scholar API Key（硬编码）
S2_API_KEY = "HdvhTeK6be5JUDCMKhwXa66QibQ2Qn171FL0Kkns"


def get_db():
    db = Database("mkg.db")
    db.connect()
    return db


def get_s2_client():
    return S2Client(api_key=S2_API_KEY)


# ============================================================
# 引用图谱
# ============================================================

class CitationBuildResponse(BaseModel):
    total_papers: int
    processed: int
    total_citations: int
    internal_edges: int
    errors: List[str]


@router.get("/citations/graph")
def get_citations_graph():
    """
    获取引用图谱数据

    返回所有内部引用边 + 论文节点，供前端渲染引用图谱
    """
    db = get_db()
    data = get_citation_graph_data(db)
    return data


@router.get("/papers/{paper_id}/citations")
def get_paper_citations(paper_id: str):
    """
    获取论文引用上下文

    返回某篇论文引用了谁 + 谁引用了它
    """
    db = get_db()
    context = get_citation_context(db, paper_id)
    if not context:
        raise HTTPException(status_code=404, detail="Paper not found")
    return context


@router.post("/citations/build", response_model=CitationBuildResponse)
def build_citations():
    """
    触发引用网络构建

    遍历所有论文，拉取引用关系
    """
    db = get_db()
    s2_client = get_s2_client()

    result = build_citation_graph(db, s2_client)

    return CitationBuildResponse(
        total_papers=result['total_papers'],
        processed=result['processed'],
        total_citations=result['total_citations'],
        internal_edges=result['internal_edges'],
        errors=result['errors']
    )


@router.get("/papers/{paper_id}/s2-info")
def get_paper_s2_info(paper_id: str):
    """
    获取论文的 S2 元数据

    包括引用数、venue、TLDR 等
    """
    db = get_db()
    paper = db.get_paper(paper_id)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # 提取 S2 相关字段
    return {
        'paper_id': paper_id,
        'title': paper.get('title'),
        's2_paper_id': paper.get('s2_paper_id'),
        's2_doi': paper.get('s2_doi'),
        'venue': paper.get('venue'),
        'year': paper.get('year'),
        'citation_count': paper.get('citation_count', 0),
        'reference_count': paper.get('reference_count', 0),
        'influential_citation_count': paper.get('influential_citation_count', 0),
        'tldr': paper.get('tldr'),
        's2_fields_of_study': json.loads(paper.get('s2_fields_of_study', '[]')) if paper.get('s2_fields_of_study') else [],
        'open_access_pdf_url': paper.get('open_access_pdf_url'),
        's2_matched_at': paper.get('s2_matched_at')
    }


# ============================================================
# 论文推荐
# ============================================================

class RecommendationResponse(BaseModel):
    recommendations: List[dict]
    based_on: List[str]


@router.get("/recommendations")
def get_recommendations():
    """
    基于图谱中的论文推荐新论文

    1. 获取所有有 s2_paper_id 的论文
    2. 按 citation_count 排序，取前 5 篇
    3. 调用 S2 推荐接口
    4. 过滤已在图谱中的论文
    """
    db = get_db()
    s2_client = get_s2_client()

    # 获取图谱中的论文
    papers = db.get_papers_with_s2_id()

    if not papers:
        return {"recommendations": [], "based_on": []}

    # 按引用数排序，取前 5 篇
    top_papers = sorted(papers, key=lambda p: p.get('citation_count', 0), reverse=True)[:5]
    top_s2_ids = [p['s2_paper_id'] for p in top_papers if p.get('s2_paper_id')]

    if not top_s2_ids:
        return {"recommendations": [], "based_on": []}

    # 获取推荐
    recommendations = s2_client.get_recommendations(top_s2_ids, limit=20)

    # 过滤已在图谱中的论文
    existing_s2_ids = {p['s2_paper_id'] for p in papers if p.get('s2_paper_id')}
    filtered = [r for r in recommendations if r.get('paperId') not in existing_s2_ids]

    return {
        "recommendations": filtered[:10],
        "based_on": [p['title'] for p in top_papers]
    }


@router.get("/concepts/{concept_id}/search-papers")
def search_papers_by_concept(
    concept_id: str,
    year: str = "2023-2026",
    min_citations: int = 0,
    limit: int = 20
):
    """
    基于概念搜索 S2 论文

    用概念名称作为搜索关键词
    """
    db = get_db()
    s2_client = get_s2_client()

    # 获取概念名称
    concept = db.get_concept(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    concept_text = concept['text']

    # 搜索论文
    results = s2_client.search_papers(
        query=concept_text,
        year=year,
        limit=limit,
        min_citation_count=min_citations
    )

    # 过滤已在图谱中的论文
    papers = db.get_papers_with_s2_id()
    existing_s2_ids = {p['s2_paper_id'] for p in papers if p.get('s2_paper_id')}
    filtered = [r for r in results if r.get('paperId') not in existing_s2_ids]

    return {
        "concept_id": concept_id,
        "concept_text": concept_text,
        "papers": filtered,
        "total": len(filtered)
    }