# mkg/agent/llm_config.py
"""
LLM 配置管理 - 使用现有的 LiteLLMClient，包装为 LangChain 兼容接口
"""

from typing import Optional, Dict, Any, List
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration

# 全局 LLM 实例
_llm: Optional['LiteLLMClientWrapper'] = None
_litellm_client = None


class LiteLLMClientWrapper(BaseChatModel):
    """
    将现有的 LiteLLMClient 包装为 LangChain 兼容的 Chat Model
    """

    def __init__(self, client, **kwargs):
        super().__init__(**kwargs)
        self._client = client

    @property
    def _llm_type(self) -> str:
        return "litellm-client-wrapper"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """生成响应"""
        # 将 LangChain 消息格式转换为单个 prompt 字符串
        prompt_parts = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                prompt_parts.append(f"<system>\n{msg.content}\n</system>")
            elif isinstance(msg, HumanMessage):
                prompt_parts.append(f"<user>\n{msg.content}\n</user>")
            elif isinstance(msg, AIMessage):
                prompt_parts.append(f"<assistant>\n{msg.content}\n</assistant>")
            else:
                prompt_parts.append(str(msg.content))

        prompt = "\n\n".join(prompt_parts)

        # 调用 LiteLLMClient
        try:
            content = self._client.generate(prompt)

            # 构建 ChatResult
            message = AIMessage(content=content)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])

        except Exception as e:
            error_msg = f"LLM 调用失败: {str(e)}"
            message = AIMessage(content=error_msg)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])

    def bind_tools(self, tools: List[Any], **kwargs: Any) -> "LiteLLMClientWrapper":
        """绑定工具（简化实现，返回 self）

        注意：当前实现不支持 function calling，
        工具调用由节点代码手动处理
        """
        return self


def init_llm(db=None, config: Dict[str, Any] = None):
    """
    初始化 LLM

    Args:
        db: Database 实例（用于读取配置）
        config: 直接传入的配置（优先于 db）
    """
    global _llm, _litellm_client

    from mkg.pdf_parser import LiteLLMClient

    # 从数据库读取配置
    if db:
        db_config = db.get_llm_config()
        if db_config and db_config.get('providers'):
            provider_config = db.get_active_llm_provider()
            if not provider_config:
                provider_config = db_config['providers'][0]

            provider = provider_config.get('provider', 'openai')
            api_key = provider_config.get('api_key')
            model = provider_config.get('model', 'gpt-4o-mini')
            base_url = provider_config.get('base_url')

            # 创建 LiteLLMClient
            _litellm_client = LiteLLMClient(
                provider=provider,
                api_key=api_key,
                model=model,
                base_url=base_url
            )

            # 包装为 LangChain 兼容
            _llm = LiteLLMClientWrapper(_litellm_client)
        else:
            _llm = None
            _litellm_client = None
    else:
        _llm = None
        _litellm_client = None


def get_llm() -> Optional[LiteLLMClientWrapper]:
    """获取 LLM 实例"""
    return _llm


def get_llm_or_raise() -> LiteLLMClientWrapper:
    """获取 LLM 实例，如果未配置则抛出异常"""
    if _llm is None:
        raise ValueError("LLM 未配置，请先在设置中配置 API Key")
    return _llm


def get_litellm_client():
    """获取原始 LiteLLMClient 实例"""
    return _litellm_client


def reset_llm():
    """重置 LLM 配置"""
    global _llm, _litellm_client
    _llm = None
    _litellm_client = None