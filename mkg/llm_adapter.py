from typing import Any, Protocol

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class _LLMClientProtocol(Protocol):
    provider: str
    model: str

    def complete_messages_sync(self, messages: list[dict], system: str | None = None) -> str: ...
    async def complete_messages(self, messages: list[dict], system: str | None = None) -> str: ...


class MKGChatModel(BaseChatModel):
    client: Any = Field(exclude=True)

    @property
    def _llm_type(self) -> str:
        return "mkg"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"provider": self.client.provider, "model": self.client.model}

    def _convert_messages(self, messages: list[BaseMessage]) -> tuple[str | None, list[dict]]:
        system_parts: list[str] = []
        dict_messages: list[dict] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_parts.append(str(msg.content))
            elif isinstance(msg, HumanMessage):
                dict_messages.append({"role": "user", "content": str(msg.content)})
            elif isinstance(msg, ToolMessage):
                dict_messages.append({
                    "role": "tool",
                    "content": str(msg.content),
                    "tool_call_id": msg.tool_call_id,
                })
            elif isinstance(msg, AIMessage):
                dict_messages.append({"role": "assistant", "content": str(msg.content)})
            else:
                dict_messages.append({"role": "user", "content": str(msg.content)})
        system_prompt = "\n\n".join(system_parts) if system_parts else None
        return system_prompt, dict_messages

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # NOTE: stop sequences are not supported by LLMClient; ignored for now
        system_prompt, dict_messages = self._convert_messages(messages)

        text = self.client.complete_messages_sync(dict_messages, system=system_prompt)

        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content=text))
            ],
            llm_output={"provider": self.client.provider, "model": self.client.model},
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # NOTE: stop sequences are not supported by LLMClient; ignored for now
        system_prompt, dict_messages = self._convert_messages(messages)

        text = await self.client.complete_messages(dict_messages, system=system_prompt)

        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content=text))
            ],
            llm_output={"provider": self.client.provider, "model": self.client.model},
        )
