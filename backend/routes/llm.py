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
from mkg.pdf_parser import AnthropicClient, GoogleClient, OpenAICompatibleClient, ClaudeCLIClient
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


# Available providers with configuration hints
PROVIDERS = [
    {
        "value": "claude_cli",
        "label": "Claude Code CLI（Docker不可用）",
        "requires_api_key": False,
        "default_base_url": None,
        "models": []
    },
    {
        "value": "openai",
        "label": "OpenAI",
        "requires_api_key": True,
        "default_base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    },
    {
        "value": "anthropic",
        "label": "Anthropic Claude",
        "requires_api_key": True,
        "default_base_url": "https://api.anthropic.com",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]
    },
    {
        "value": "google",
        "label": "Google Gemini",
        "requires_api_key": True,
        "default_base_url": None,
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
    },
    {
        "value": "deepseek",
        "label": "DeepSeek",
        "requires_api_key": True,
        "default_base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]
    },
    {
        "value": "dashscope",
        "label": "阿里云 DashScope（通义千问）",
        "requires_api_key": True,
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"]
    },
    {
        "value": "minimax",
        "label": "MiniMax",
        "requires_api_key": True,
        "default_base_url": "https://api.minimax.chat/v1",
        "models": ["abab6.5s-chat", "abab6.5g-chat", "abab5.5-chat"]
    },
    {
        "value": "openrouter",
        "label": "OpenRouter",
        "requires_api_key": True,
        "default_base_url": "https://openrouter.ai/api/v1",
        "models": ["anthropic/claude-sonnet-4", "openai/gpt-4o", "google/gemini-2.0-flash-exp"]
    },
    {
        "value": "moonshot",
        "label": "Moonshot（Kimi）",
        "requires_api_key": True,
        "default_base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]
    },
    {
        "value": "zhipu",
        "label": "智谱 AI（GLM）",
        "requires_api_key": True,
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4", "glm-4-flash", "glm-4-plus"]
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

        elif request.provider in ("dashscope", "openrouter", "minimax", "deepseek", "moonshot", "zhipu"):
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key 是必需的")
            base_urls = {
                "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "openrouter": "https://openrouter.ai/api/v1",
                "minimax": "https://api.minimax.chat/v1",
                "deepseek": "https://api.deepseek.com/v1",
                "moonshot": "https://api.moonshot.cn/v1",
                "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            }
            default_models = {
                "dashscope": "qwen-plus",
                "openrouter": "openai/gpt-4o-mini",
                "minimax": "abab6.5s-chat",
                "deepseek": "deepseek-chat",
                "moonshot": "moonshot-v1-8k",
                "zhipu": "glm-4-flash",
            }
            client = OpenAICompatibleClient(
                request.api_key,
                base_url=request.base_url or base_urls.get(request.provider),
                model=request.model or default_models.get(request.provider)
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