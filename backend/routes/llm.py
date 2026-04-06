"""
LLM Configuration API routes
"""

from fastapi import APIRouter, HTTPException
from typing import List
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database
from mkg.pdf_parser import LiteLLMClient, ClaudeCLIClient
from mkg.llm import reset_llm
from backend.schemas import (
    LLMConfigResponse, LLMConfigRequest, LLMTestRequest, LLMTestResponse, LLMProviderConfig
)

router = APIRouter(prefix="/api/llm", tags=["llm"])

_db = None


def get_db():
    global _db
    if _db is None:
        _db = Database("mkg.db")
        _db.connect()
    return _db


# Available providers - 极简配置
PROVIDERS = [
    {
        "value": "claude_cli",
        "label": "Claude Code CLI（本地开发）",
        "requires_api_key": False,
        "models": []
    },
    {
        "value": "custom",
        "label": "自定义配置",
        "requires_api_key": True,
        "requires_base_url": True,
        "models": []
    },
]

FUNCTION_GROUPS = [
    {"value": "paper_parsing", "label": "论文解析"},
    {"value": "concept_extraction", "label": "概念提取"},
    {"value": "research_analysis", "label": "研究分析"},
]


@router.get("/providers")
def list_providers():
    """List available LLM providers"""
    return {"providers": PROVIDERS, "function_groups": FUNCTION_GROUPS}


@router.get("/config", response_model=LLMConfigResponse)
def get_config():
    """Get current LLM configuration"""
    db = get_db()
    config = db.get_llm_config()

    if not config:
        return LLMConfigResponse(mode="single", providers=[])

    return LLMConfigResponse(
        mode=config['mode'],
        providers=[LLMProviderConfig(**p) for p in config.get('providers', [])]
    )


@router.post("/config", response_model=LLMConfigResponse)
def save_config(request: LLMConfigRequest):
    """Save LLM configuration"""
    db = get_db()

    providers_data = [p.model_dump() for p in request.providers]
    config = db.save_llm_config(request.mode, providers_data)

    # 重置 LLM 实例，下次调用时会重新初始化
    reset_llm()

    return LLMConfigResponse(
        mode=config['mode'],
        providers=[LLMProviderConfig(**p) for p in config.get('providers', [])]
    )


@router.post("/test", response_model=LLMTestResponse)
def test_connection(request: LLMTestRequest):
    """Test LLM connection using LiteLLM"""
    try:
        if request.provider == "claude_cli":
            # Claude CLI 特殊处理
            client = ClaudeCLIClient()
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message="Claude CLI 连接成功", model="claude-code")

        # 所有其他服务商通过 LiteLLM 统一处理
        client = LiteLLMClient(
            provider=request.provider,
            api_key=request.api_key,
            model=request.model,
            base_url=request.base_url  # 可选，用于代理或私有部署
        )
        result = client.extract_concepts("Say 'OK' if you can read this.")

        provider_label = next((p["label"] for p in PROVIDERS if p["value"] == request.provider), request.provider)
        return LLMTestResponse(
            success=True,
            message=f"{provider_label} 连接成功",
            model=request.model or "default"
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()

        # 友好的错误提示
        if "api_key" in error_msg or "unauthorized" in error_msg or "invalid" in error_msg:
            raise HTTPException(status_code=401, detail="API Key 无效，请检查后重试")
        elif "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
            raise HTTPException(status_code=503, detail="网络连接失败，请检查网络或代理设置")
        elif "model" in error_msg or "not found" in error_msg:
            raise HTTPException(status_code=404, detail=f"模型 '{request.model}' 不存在，请确认模型名称")
        elif "rate" in error_msg or "limit" in error_msg:
            raise HTTPException(status_code=429, detail="请求频率超限，请稍后重试")
        else:
            raise HTTPException(status_code=500, detail=f"连接失败: {str(e)}")