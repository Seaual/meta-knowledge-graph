# LLM Refactor — Remove liteLLM, Switch to Native HTTP

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace LangChain `ChatOpenAI`/`ChatAnthropic` wrappers with a native `httpx`-based `LLMClient`, wrap it in a custom `BaseChatModel` adapter (`MKGChatModel`), and remove `litellm`, `langchain-openai`, `langchain-anthropic` dependencies while keeping the `mkg/llm.py` public API unchanged.

**Architecture:** New `LLMClient` handles raw HTTP to OpenAI/Anthropic APIs. New `MKGChatModel` inherits `BaseChatModel` from `langchain-core`, translates LangChain messages to dicts, delegates to `LLMClient`, and wraps responses back into `ChatResult`. Existing agent nodes call `llm.invoke()` exactly as before.

**Tech Stack:** Python 3.10+, `httpx`, `langchain-core`, `pytest`, `pytest-asyncio`

---

### Task 1: LLMClient Core Implementation

**Files:**
- Create: `mkg/llm_client.py`
- Test: `tests/test_llm_client.py`

**Context:** The project currently has no direct usage of `litellm`, but `pyproject.toml` still declares it. We will replace the entire LLM calling layer with native HTTP.

- [ ] **Step 1: Write the failing test for LLMClient (OpenAI success path)**

```python
# tests/test_llm_client.py
import pytest
from unittest.mock import patch, MagicMock

from mkg.llm_client import LLMClient


def test_llm_client_openai_success():
    client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "hello from openai"}}]
    }

    with patch("mkg.llm_client.httpx.Client.post", return_value=mock_response):
        result = client.complete_sync("say hi")
        assert result == "hello from openai"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_client.py::test_llm_client_openai_success -v`

Expected: `FAILED` — `ModuleNotFoundError: No module named 'mkg.llm_client'`

- [ ] **Step 3: Write minimal LLMClient with sync OpenAI support**

```python
# mkg/llm_client.py
import httpx

DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-latest"
DEFAULT_OPENAI_MODEL = "gpt-4o"


class LLMClient:
    def __init__(self, api_key: str, provider: str, base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.provider = provider.lower()
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.model = model

    def complete_sync(self, prompt: str) -> str:
        return self.complete_messages_sync(
            [{"role": "user", "content": prompt}],
            system="",
        )

    def complete_messages_sync(self, messages: list[dict], system: str = "") -> str:
        if self.provider == "anthropic":
            return self._call_anthropic_sync(messages, system)
        if self.provider == "openai":
            return self._call_openai_sync(messages, system)
        raise ValueError(f"Unknown provider: {self.provider}")

    def _call_openai_sync(self, messages: list[dict], system: str = "") -> str:
        url = f"{self.base_url}/v1/chat/completions" if self.base_url else "https://api.openai.com/v1/chat/completions"
        model = self.model or DEFAULT_OPENAI_MODEL
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": msgs,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _call_anthropic_sync(self, messages: list[dict], system: str = "") -> str:
        url = f"{self.base_url}/v1/messages" if self.base_url else "https://api.anthropic.com/v1/messages"
        model = self.model or DEFAULT_ANTHROPIC_MODEL
        payload: dict = {
            "model": model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system:
            payload["system"] = system

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_client.py::test_llm_client_openai_success -v`

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tests/test_llm_client.py mkg/llm_client.py
git commit -m "feat: add native HTTP LLMClient with sync support

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Async LLMClient + Retry Logic + Full Test Coverage

**Files:**
- Modify: `mkg/llm_client.py`
- Test: `tests/test_llm_client.py`

- [ ] **Step 1: Write failing tests for async and retry**

```python
# Append to tests/test_llm_client.py

import asyncio


@pytest.mark.asyncio
async def test_llm_client_openai_async():
    client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "async hello"}}]
    }

    with patch("mkg.llm_client.httpx.AsyncClient.post", return_value=mock_response):
        result = await client.complete("say hi")
        assert result == "async hello"


@pytest.mark.asyncio
async def test_llm_client_retry_on_429():
    client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")

    error_response = MagicMock()
    error_response.status_code = 429
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429", request=MagicMock(), response=error_response
    )

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "choices": [{"message": {"content": "retry success"}}]
    }

    with patch(
        "mkg.llm_client.httpx.AsyncClient.post",
        side_effect=[error_response, success_response],
    ) as mock_post:
        with patch("asyncio.sleep", return_value=None):
            result = await client.complete("say hi")
            assert result == "retry success"
            assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_llm_client_timeout_eventually_fails():
    client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")

    with patch(
        "mkg.llm_client.httpx.AsyncClient.post",
        side_effect=httpx.ReadTimeout("timeout"),
    ):
        with patch("asyncio.sleep", return_value=None):
            with pytest.raises(RuntimeError, match="LLM API timeout"):
                await client.complete("say hi")


def test_llm_client_unknown_provider():
    client = LLMClient(api_key="sk-test", provider="unknown")
    with pytest.raises(ValueError, match="Unknown provider"):
        client.complete_sync("say hi")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_llm_client.py -v`

Expected: `FAILED` — `AttributeError: 'LLMClient' object has no attribute 'complete'`

- [ ] **Step 3: Add async methods and retry to LLMClient**

Replace the entire `mkg/llm_client.py` with this expanded version:

```python
# mkg/llm_client.py
import asyncio
import httpx

DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-latest"
DEFAULT_OPENAI_MODEL = "gpt-4o"


class LLMClient:
    def __init__(self, api_key: str, provider: str, base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.provider = provider.lower()
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.model = model

    async def complete(self, prompt: str) -> str:
        return await self.complete_messages(
            [{"role": "user", "content": prompt}],
            system="",
        )

    async def complete_messages(self, messages: list[dict], system: str = "") -> str:
        if self.provider == "anthropic":
            return await self._call_anthropic(messages, system)
        if self.provider == "openai":
            return await self._call_openai(messages, system)
        raise ValueError(f"Unknown provider: {self.provider}")

    def complete_sync(self, prompt: str) -> str:
        return self.complete_messages_sync(
            [{"role": "user", "content": prompt}],
            system="",
        )

    def complete_messages_sync(self, messages: list[dict], system: str = "") -> str:
        if self.provider == "anthropic":
            return self._call_anthropic_sync(messages, system)
        if self.provider == "openai":
            return self._call_openai_sync(messages, system)
        raise ValueError(f"Unknown provider: {self.provider}")

    async def _call_openai(self, messages: list[dict], system: str = "") -> str:
        url = f"{self.base_url}/v1/chat/completions" if self.base_url else "https://api.openai.com/v1/chat/completions"
        model = self.model or DEFAULT_OPENAI_MODEL
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        last_err = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    resp = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": msgs,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except httpx.ReadTimeout as e:
                last_err = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"LLM API timeout after {attempt + 1} attempts") from e
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code == 429 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        raise last_err

    async def _call_anthropic(self, messages: list[dict], system: str = "") -> str:
        url = f"{self.base_url}/v1/messages" if self.base_url else "https://api.anthropic.com/v1/messages"
        model = self.model or DEFAULT_ANTHROPIC_MODEL
        payload: dict = {
            "model": model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system:
            payload["system"] = system

        last_err = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    resp = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "anthropic-version": "2023-06-01",
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data["content"][0]["text"]
            except httpx.ReadTimeout as e:
                last_err = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"LLM API timeout after {attempt + 1} attempts") from e
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code == 429 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        raise last_err

    def _call_openai_sync(self, messages: list[dict], system: str = "") -> str:
        url = f"{self.base_url}/v1/chat/completions" if self.base_url else "https://api.openai.com/v1/chat/completions"
        model = self.model or DEFAULT_OPENAI_MODEL
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": msgs,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _call_anthropic_sync(self, messages: list[dict], system: str = "") -> str:
        url = f"{self.base_url}/v1/messages" if self.base_url else "https://api.anthropic.com/v1/messages"
        model = self.model or DEFAULT_ANTHROPIC_MODEL
        payload: dict = {
            "model": model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system:
            payload["system"] = system

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_llm_client.py -v`

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tests/test_llm_client.py mkg/llm_client.py
git commit -m "feat: add async LLMClient with retry logic

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: MKGChatModel Adapter

**Files:**
- Create: `mkg/llm_adapter.py`
- Test: `tests/test_llm_adapter.py`

- [ ] **Step 1: Write failing test for MKGChatModel**

```python
# tests/test_llm_adapter.py
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from mkg.llm_adapter import MKGChatModel


def test_generate_with_human_and_system():
    mock_client = MagicMock()
    mock_client.provider = "openai"
    mock_client.model = "gpt-4o"
    mock_client.complete_messages_sync.return_value = "generated text"

    model = MKGChatModel(client=mock_client)
    result = model.invoke([SystemMessage(content="sys"), HumanMessage(content="hi")])

    assert result.content == "generated text"
    mock_client.complete_messages_sync.assert_called_once()
    call_args = mock_client.complete_messages_sync.call_args
    assert call_args.kwargs["system"] == "sys"
    assert call_args.args[0] == [{"role": "user", "content": "hi"}]


def test_generate_with_tool_message():
    from langchain_core.messages import ToolMessage

    mock_client = MagicMock()
    mock_client.provider = "openai"
    mock_client.model = "gpt-4o"
    mock_client.complete_messages_sync.return_value = "tool response"

    model = MKGChatModel(client=mock_client)
    result = model.invoke([
        HumanMessage(content="question"),
        ToolMessage(content="tool result", tool_call_id="tc1"),
    ])

    assert result.content == "tool response"
    call_args = mock_client.complete_messages_sync.call_args
    assert call_args.args[0] == [
        {"role": "user", "content": "question"},
        {"role": "tool", "content": "tool result", "tool_call_id": "tc1"},
    ]


@pytest.mark.asyncio
async def test_agenerate_async():
    mock_client = MagicMock()
    mock_client.provider = "anthropic"
    mock_client.model = "claude-3-5-sonnet-latest"
    mock_client.complete_messages = MagicMock(return_value="async result")

    model = MKGChatModel(client=mock_client)
    result = await model.ainvoke([HumanMessage(content="hi")])

    assert result.content == "async result"


def test_llm_type_and_params():
    mock_client = MagicMock()
    mock_client.provider = "openai"
    mock_client.model = "gpt-4o"

    model = MKGChatModel(client=mock_client)
    assert model._llm_type == "mkg"
    assert model._identifying_params == {"provider": "openai", "model": "gpt-4o"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_llm_adapter.py -v`

Expected: `FAILED` — `ModuleNotFoundError: No module named 'mkg.llm_adapter'`

- [ ] **Step 3: Implement MKGChatModel**

```python
# mkg/llm_adapter.py
from typing import Any

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

from mkg.llm_client import LLMClient


class MKGChatModel(BaseChatModel):
    client: LLMClient = Field(exclude=True)

    @property
    def _llm_type(self) -> str:
        return "mkg"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"provider": self.client.provider, "model": self.client.model}

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        system_prompt = ""
        dict_messages: list[dict] = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = str(msg.content)
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
        system_prompt = ""
        dict_messages: list[dict] = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = str(msg.content)
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

        text = await self.client.complete_messages(dict_messages, system=system_prompt)

        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content=text))
            ],
            llm_output={"provider": self.client.provider, "model": self.client.model},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_llm_adapter.py -v`

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tests/test_llm_adapter.py mkg/llm_adapter.py
git commit -m "feat: add MKGChatModel BaseChatModel adapter

Wraps LLMClient so LangGraph agents can call llm.invoke() unchanged.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Refactor mkg/llm.py to Use Adapter

**Files:**
- Modify: `mkg/llm.py`

- [ ] **Step 1: Run existing tests to establish baseline**

Run: `pytest tests/ -k llm -v`

Expected: Current tests pass (or skip if none directly test `mkg/llm.py`)

- [ ] **Step 2: Replace mkg/llm.py internals**

Replace the entire file with:

```python
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
            system=system_prompt or "",
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
```

- [ ] **Step 3: Run agent tests to verify no regression**

Run: `pytest tests/ -v`

Expected: All existing tests pass (agent tests, concept extraction tests, etc.)

If failures occur, check that `MKGChatModel` correctly handles all message types the agents use.

- [ ] **Step 4: Commit**

```bash
git add mkg/llm.py
git commit -m "refactor: switch mkg/llm.py to native HTTP via LLMClient + MKGChatModel

Remove ChatOpenAI/ChatAnthropic imports. generate() bypasses
LangChain wrapper when possible for lower latency.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Remove Obsolete Dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Remove litellm, langchain-openai, langchain-anthropic from pyproject.toml**

In `pyproject.toml`, delete these lines from `[project] dependencies`:
```
    "litellm>=1.50.0",
    "anthropic>=0.18.0",
    "openai>=1.0.0",
    "langchain-openai>=0.2.0",
    "langchain-anthropic>=0.2.0",
```

Add `httpx` if not already present:
```
    "httpx>=0.26.0",
```

- [ ] **Step 2: Sync requirements.txt**

In `requirements.txt`, remove:
```
litellm>=1.50.0
anthropic>=0.18.0
openai>=1.0.0
langchain-openai>=0.2.0
langchain-anthropic>=0.2.0
```

Add if not present:
```
httpx>=0.26.0
```

- [ ] **Step 3: Regenerate lock file**

Run: `uv lock`

Expected: `uv.lock` updates without errors

- [ ] **Step 4: Verify imports still work**

Run: `python -c "from mkg.llm import init_llm, generate, get_llm_or_raise; from mkg.llm_client import LLMClient; from mkg.llm_adapter import MKGChatModel; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`

Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml requirements.txt uv.lock
git commit -m "build: remove litellm, langchain-openai, langchain-anthropic deps

Switch to native httpx-based LLMClient. Keep langchain-core for agent layer.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage:**
- LLMClient sync + async: ✅ Task 1 + Task 2
- Retry logic (429, timeout): ✅ Task 2
- MKGChatModel adapter: ✅ Task 3
- mkg/llm.py refactor (API unchanged): ✅ Task 4
- Dependency cleanup: ✅ Task 5
- Agent layer zero改动: ✅ (no tasks touch mkg/agent/)

**2. Placeholder scan:**
- No "TBD", "TODO", "implement later", "fill in details"
- No vague "add appropriate error handling"
- No "similar to Task N" shortcuts
- All code blocks contain complete implementations

**3. Type consistency:**
- `LLMClient.complete_messages_sync(messages: list[dict], system: str)` — consistent across all tasks
- `MKGChatModel(client=mock_client)` — constructor pattern consistent in tests and implementation
- `generate(prompt: str, system_prompt: str | None = None) -> str` — unchanged from original signature

No issues found.
