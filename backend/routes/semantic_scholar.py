"""
Semantic Scholar API routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database
from mkg.semantic_scholar import SemanticScholarClient
from backend.schemas import S2ConfigResponse, S2ConfigRequest, S2TestResponse

router = APIRouter(prefix="/api/s2", tags=["semantic-scholar"])

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
    db = get_db()
    config = db.get_s2_config()

    if not config or not config.get('api_key'):
        return S2ConfigResponse(has_api_key=False, enabled=True)

    # 脱敏处理 API Key
    key = config['api_key']
    masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"

    return S2ConfigResponse(
        has_api_key=True,
        enabled=config.get('enabled', True),
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
    result = SemanticScholarClient.test_connection(request.api_key)
    return S2TestResponse(success=result['success'], message=result['message'])


@router.post("/papers/{doi:path}/enhance")
def enhance_paper(doi: str):
    """手动重新增强指定论文的元数据"""
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    config = db.get_s2_config()
    if not config or not config.get('api_key'):
        raise HTTPException(status_code=400, detail="Semantic Scholar API Key not configured")

    if not paper.get('title'):
        raise HTTPException(status_code=400, detail="Paper has no title to search")

    client = SemanticScholarClient(config['api_key'])
    enhanced = client.enhance_paper_data(paper['title'], {})

    if enhanced:
        # 更新数据库
        update_fields = []
        update_values = []
        for field in ['s2_paper_id', 'abstract', 'authors', 'venue', 'year',
                       'citation_count', 'reference_count', 'influential_citation_count', 'open_access_pdf']:
            if field in enhanced:
                update_fields.append(f"{field} = ?")
                update_values.append(enhanced[field])

        if update_fields:
            update_values.append(doi)
            db.execute_write(
                f"UPDATE papers SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE doi = ?",
                tuple(update_values)
            )

    return {"success": True, "enhanced": enhanced}