# mkg/llm.py
"""
统一 LLM 客户端 - 所有 LLM 调用通过原生 HTTP client

支持：
- OpenAI 兼容 API
- Anthropic 兼容 API
"""

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from mkg.llm_adapter import MKGChatModel
from mkg.llm_client import LLMClient

# 全局 LLM 实例
_llm_instance: BaseChatModel | None = None
_current_config: dict[str, Any] = {}


def init_llm(
    provider: str,
    api_key: str,
    model: str,
    base_url: str | None = None
) -> BaseChatModel:
    """
    初始化 LLM 客户端

    Args:
        provider: 服务商名称（openai / anthropic）
        api_key: API 密钥
        model: 模型名称
        base_url: API 地址（可选）

    Returns:
        初始化好的 LLM 实例（MKGChatModel）
    """
    global _llm_instance, _current_config

    client = LLMClient(
        api_key=api_key,
        provider=provider,
        model=model,
        base_url=base_url or "",
    )
    _llm_instance = MKGChatModel(client=client)

    _current_config = {
        "provider": provider,
        "model": model,
        "base_url": base_url,
    }

    return _llm_instance


def init_llm_from_db(db) -> BaseChatModel | None:
    """
    从数据库配置初始化 LLM

    Args:
        db: Database 实例

    Returns:
        初始化好的 LLM 实例，如果配置不存在返回 None
    """
    config = db.get_llm_config()
    if not config or not config.get("providers"):
        return None

    provider_config = db.get_active_llm_provider()
    if not provider_config:
        provider_config = config["providers"][0]

    return init_llm(
        provider=provider_config.get("provider", "openai"),
        api_key=provider_config.get("api_key"),
        model=provider_config.get("model", "gpt-4o-mini"),
        base_url=provider_config.get("base_url"),
    )


def get_llm() -> BaseChatModel | None:
    """
    获取 LLM 实例

    Returns:
        LLM 实例，如果未初始化返回 None
    """
    return _llm_instance


def get_llm_or_raise() -> BaseChatModel:
    """
    获取 LLM 实例，如果未配置则抛出异常

    Returns:
        LLM 实例

    Raises:
        ValueError: 如果 LLM 未配置
    """
    if _llm_instance is None:
        raise ValueError("LLM 未配置，请先在设置中配置 API Key")
    return _llm_instance


def reset_llm():
    """
    重置 LLM 实例

    在配置更新后调用，下次调用时会重新初始化
    """
    global _llm_instance, _current_config
    _llm_instance = None
    _current_config = {}


def get_current_config() -> dict[str, Any]:
    """
    获取当前 LLM 配置

    Returns:
        当前配置字典
    """
    return _current_config.copy()


def extract_text_content(content) -> str:
    """
    从 LLM 响应内容中提取文本

    处理不同的响应格式：
    - 字符串：直接返回
    - 列表：提取文本块并合并

    Args:
        content: LLM 响应内容

    Returns:
        文本字符串
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return "".join(text_parts)
    return str(content)


def generate(prompt: str, system_prompt: str | None = None) -> str:
    """
    简化的单次生成接口

    用于 PDF 解析等场景，无需手动构建 messages

    Args:
        prompt: 用户输入
        system_prompt: 系统提示（可选）

    Returns:
        生成的文本内容
    """
    llm = get_llm_or_raise()
    # 直接通过底层 client 调用，避免绕 LangChain
    if isinstance(llm, MKGChatModel):
        return llm.client.complete_messages_sync(
            [{"role": "user", "content": prompt}],
            system=system_prompt,
        )

    # Fallback: 使用 LangChain 路径（理论上不会走到这里）
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = llm.invoke(messages)
    content = response.content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return "".join(text_parts)
    return str(content)
