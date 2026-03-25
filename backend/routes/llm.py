"""
LLM Configuration API routes
"""

from fastapi import APIRouter, HTTPException
from typing import List
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openclaw.database import Database
from openclaw.pdf_parser import AnthropicClient, GoogleClient, OpenAICompatibleClient, ClaudeCLIClient
from backend.schemas import (
    LLMConfigResponse, LLMConfigRequest, LLMTestRequest, LLMTestResponse, LLMProviderConfig
)

router = APIRouter(prefix="/api/llm", tags=["llm"])

_db = None


def get_db():
    global _db
    if _db is None:
        _db = Database("openclaw.db")
        _db.connect()
    return _db


# Available providers
PROVIDERS = [
    {"value": "claude_cli", "label": "Claude Code CLI", "requires_api_key": False},
    {"value": "openai", "label": "OpenAI 兼容接口", "requires_api_key": True, "default_base_url": "https://api.openai.com/v1"},
    {"value": "anthropic", "label": "Anthropic Claude", "requires_api_key": True},
    {"value": "google", "label": "Google Gemini", "requires_api_key": True},
    {"value": "dashscope", "label": "阿里云 DashScope", "requires_api_key": True},
    {"value": "openrouter", "label": "OpenRouter", "requires_api_key": True, "default_base_url": "https://openrouter.ai/api/v1"},
    {"value": "minimax", "label": "MiniMax", "requires_api_key": True},
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

    return LLMConfigResponse(
        mode=config['mode'],
        providers=[LLMProviderConfig(**p) for p in config.get('providers', [])]
    )


@router.post("/test", response_model=LLMTestResponse)
def test_connection(request: LLMTestRequest):
    """Test LLM connection"""
    try:
        if request.provider == "claude_cli":
            client = ClaudeCLIClient()
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message="Claude CLI 连接成功", model="claude-code")

        elif request.provider == "openai":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key 是必需的")
            client = OpenAICompatibleClient(
                request.api_key,
                base_url=request.base_url or "https://api.openai.com/v1",
                model=request.model or "gpt-3.5-turbo"
            )
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message="OpenAI 连接成功", model=request.model)

        elif request.provider == "anthropic":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key 是必需的")
            client = AnthropicClient(
                request.api_key,
                model=request.model or "claude-sonnet-4-20250514",
                base_url=request.base_url
            )
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message="Anthropic 连接成功", model=request.model)

        elif request.provider == "google":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key 是必需的")
            client = GoogleClient(request.api_key)
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message="Google Gemini 连接成功", model="gemini")

        elif request.provider in ("dashscope", "openrouter", "minimax"):
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key 是必需的")
            base_urls = {
                "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "openrouter": "https://openrouter.ai/api/v1",
                "minimax": request.base_url
            }
            client = OpenAICompatibleClient(
                request.api_key,
                base_url=base_urls.get(request.provider, request.base_url),
                model=request.model or "qwen-plus"
            )
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message=f"{request.provider} 连接成功", model=request.model)

        else:
            raise HTTPException(status_code=400, detail=f"未知的服务商: {request.provider}")

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
            raise HTTPException(status_code=401, detail="API Key 无效，请检查后重试")
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            raise HTTPException(status_code=503, detail="网络连接失败，请检查 Base URL")
        elif "model" in error_msg.lower() or "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="模型不存在，请确认模型名称")
        else:
            raise HTTPException(status_code=500, detail=f"测试失败: {error_msg}")