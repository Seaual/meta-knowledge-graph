"""
Semantic Scholar API routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database
from mkg.semantic_scholar import SemanticScholarClient
from backend.schemas import (
    S2ConfigResponse, S2ConfigRequest, S2TestResponse,
    S2CitationsResponse, S2Citation, S2ReferencesResponse, S2Reference
)

router = APIRouter(prefix="/api/s2", tags=["semantic-scholar"])

# Semantic Scholar API Key（硬编码）
S2_API_KEY = "HdvhTeK6be5JUDCMKhwXa66QibQ2Qn171FL0Kkns"

_db = None


def get_db():
    global _db
    if _db is None:
        _db = Database("mkg.db")
        _db.connect()
    return _db


@router.get("/config", response_model=S2ConfigResponse)
def get_config():
    """获取 Semantic Scholar 配置状态"""
    # 脱敏处理 API Key
    masked = S2_API_KEY[:4] + "****" + S2_API_KEY[-4:]
    return S2ConfigResponse(
        has_api_key=True,
        enabled=True,
        masked_key=masked
    )


@router.post("/config", response_model=S2ConfigResponse)
def save_config(request: S2ConfigRequest):
    """保存 Semantic Scholar API Key"""
    db = get_db()
    config = db.save_s2_config(request.api_key, request.enabled)

    key = request.api_key
    masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"

    return S2ConfigResponse(
        has_api_key=True,
        enabled=config['enabled'],
        masked_key=masked
    )


@router.post("/test", response_model=S2TestResponse)
def test_connection(request: S2ConfigRequest):
    """测试 API Key 是否有效"""
    result = SemanticScholarClient.test_connection(S2_API_KEY)
    return S2TestResponse(success=result['success'], message=result['message'])


@router.post("/papers/{doi:path}/enhance")
def enhance_paper(doi: str):
    """手动重新增强指定论文的元数据"""
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.get('title'):
        raise HTTPException(status_code=400, detail="Paper has no title to search")

    client = SemanticScholarClient(S2_API_KEY)
    enhanced = client.enhance_paper_data(paper['title'], {})

    if enhanced:
        # 更新数据库
        update_fields = []
        update_values = []
        for field in ['s2_paper_id', 's2_doi', 's2_arxiv_id', 's2_external_ids',
                       'abstract', 'authors', 'venue', 'year',
                       'citation_count', 'reference_count', 'influential_citation_count', 'open_access_pdf',
                       'tldr', 's2_fields_of_study']:
            if field in enhanced:
                update_fields.append(f"{field} = ?")
                value = enhanced[field]
                # JSON 序列化 list/dict 字段
                if field in ('authors', 's2_fields_of_study') and isinstance(value, list):
                    value = json.dumps(value)
                update_values.append(value)

        if update_fields:
            update_values.append(doi)
            db.execute_write(
                f"UPDATE papers SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE doi = ?",
                tuple(update_values)
            )

    return {"success": True, "enhanced": enhanced}


@router.get("/papers/{doi:path}/citations", response_model=S2CitationsResponse)
def get_paper_citations(doi: str, limit: int = 50):
    """获取论文的引用列表"""
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    s2_paper_id = paper.get('s2_paper_id')
    if not s2_paper_id:
        raise HTTPException(status_code=400, detail="Paper has no S2 paper ID")

    client = SemanticScholarClient(S2_API_KEY)
    citations = client.get_paper_citations(s2_paper_id, limit)

    if citations is None:
        raise HTTPException(status_code=500, detail="Failed to fetch citations from S2")

    citation_items = [S2Citation(**c) for c in citations]
    return S2CitationsResponse(citations=citation_items, total=len(citation_items))


@router.get("/papers/{doi:path}/references", response_model=S2ReferencesResponse)
def get_paper_references(doi: str, limit: int = 50):
    """获取论文的参考文献列表"""
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    s2_paper_id = paper.get('s2_paper_id')
    if not s2_paper_id:
        raise HTTPException(status_code=400, detail="Paper has no S2 paper ID")

    client = SemanticScholarClient(S2_API_KEY)
    references = client.get_paper_references(s2_paper_id, limit)

    if references is None:
        raise HTTPException(status_code=500, detail="Failed to fetch references from S2")

    reference_items = [S2Reference(**r) for r in references]
    return S2ReferencesResponse(references=reference_items, total=len(reference_items))