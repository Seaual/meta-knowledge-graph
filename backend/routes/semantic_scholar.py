"""
Semantic Scholar API routes
"""

import json
import os

from fastapi import APIRouter, HTTPException

from backend.dependencies import get_db
from backend.schemas import (
    S2Citation,
    S2CitationsResponse,
    S2ConfigRequest,
    S2ConfigResponse,
    S2Reference,
    S2ReferencesResponse,
    S2TestResponse,
)
from mkg.semantic_scholar import S2Client

router = APIRouter(prefix="/api/s2", tags=["semantic-scholar"])

# Semantic Scholar API Key（优先从环境变量读取）
S2_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")


@router.get("/config", response_model=S2ConfigResponse)
def get_config():
    """获取 Semantic Scholar 配置状态"""
    # 脱敏处理 API Key
    masked = S2_API_KEY[:4] + "****" + S2_API_KEY[-4:]
    return S2ConfigResponse(has_api_key=True, enabled=True, masked_key=masked)


@router.post("/config", response_model=S2ConfigResponse)
def save_config(request: S2ConfigRequest):
    """保存 Semantic Scholar API Key"""
    db = get_db()
    config = db.save_s2_config(request.api_key, request.enabled)

    key = request.api_key
    masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"

    return S2ConfigResponse(has_api_key=True, enabled=config["enabled"], masked_key=masked)


@router.post("/test", response_model=S2TestResponse)
def test_connection(request: S2ConfigRequest):
    """测试 API Key 是否有效"""
    result = S2Client.test_connection(S2_API_KEY)
    return S2TestResponse(success=result["success"], message=result["message"])


@router.post("/papers/{doi:path}/enhance")
def enhance_paper(doi: str):
    """手动重新增强指定论文的元数据"""
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.get("title"):
        raise HTTPException(status_code=400, detail="Paper has no title to search")

    client = S2Client(api_key=S2_API_KEY)
    enhanced = client.match_paper_by_title(paper["title"])

    if enhanced:
        # 提取 DOI from externalIds
        external_ids = enhanced.get("externalIds", {})
        s2_doi = external_ids.get("DOI")

        # 提取 authors
        authors = enhanced.get("authors", [])
        authors_json = json.dumps([a.get("name") for a in authors if a.get("name")])

        # 提取 fields of study
        fields_of_study = enhanced.get("s2FieldsOfStudy", [])
        fields_json = json.dumps(fields_of_study) if fields_of_study else None

        # 提取 open access PDF
        open_access_pdf_url = enhanced.get("openAccessPdf")

        # 更新数据库
        db.execute_write(
            """
            UPDATE papers SET
                s2_paper_id = ?,
                s2_doi = ?,
                s2_external_ids = ?,
                abstract = COALESCE(?, abstract),
                authors = CASE WHEN ? IS NOT NULL THEN ? ELSE authors END,
                venue = ?,
                year = ?,
                citation_count = ?,
                reference_count = ?,
                influential_citation_count = ?,
                open_access_pdf_url = ?,
                tldr = ?,
                s2_fields_of_study = ?,
                s2_matched_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """,
            (
                enhanced.get("paperId"),
                s2_doi,
                json.dumps(external_ids) if external_ids else None,
                enhanced.get("abstract"),
                authors_json,
                authors_json,
                enhanced.get("venue"),
                enhanced.get("year"),
                enhanced.get("citationCount", 0),
                enhanced.get("referenceCount", 0),
                enhanced.get("influentialCitationCount", 0),
                open_access_pdf_url,
                enhanced.get("tldr"),
                fields_json,
                doi,
            ),
        )

    return {"success": True, "enhanced": enhanced}


@router.get("/papers/{doi:path}/citations", response_model=S2CitationsResponse)
def get_paper_citations(doi: str, limit: int = 50):
    """获取论文的引用列表"""
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    s2_paper_id = paper.get("s2_paper_id")
    if not s2_paper_id:
        raise HTTPException(status_code=400, detail="Paper has no S2 paper ID")

    client = S2Client(api_key=S2_API_KEY)
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

    s2_paper_id = paper.get("s2_paper_id")
    if not s2_paper_id:
        raise HTTPException(status_code=400, detail="Paper has no S2 paper ID")

    client = S2Client(api_key=S2_API_KEY)
    references = client.get_paper_references(s2_paper_id, limit)

    if references is None:
        raise HTTPException(status_code=500, detail="Failed to fetch references from S2")

    reference_items = [S2Reference(**r) for r in references]
    return S2ReferencesResponse(references=reference_items, total=len(reference_items))
