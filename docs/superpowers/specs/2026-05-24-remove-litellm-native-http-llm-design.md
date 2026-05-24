# LLM 调用层重构：删除 liteLLM，改为原生 HTTP

## 背景

当前 `mkg/llm.py` 通过 LangChain 的 `ChatOpenAI`/`ChatAnthropic` 包装 LLM 调用，并依赖 `litellm`（`pyproject.toml` 中声明但代码中已不直接使用）。目标是参照 `D:\miniharness` 中的 `LLMClient` 实现，将底层调用改为原生 HTTP（`httpx`），同时保留 LangGraph agent 层的兼容性。

## 目标

1. 删除 `litellm`、`langchain-openai`、`langchain-anthropic` 依赖
2. 新建原生 HTTP LLM client（类似 miniharness）
3. 用自定义 `BaseChatModel` 包装 client，agent 层 `llm.invoke()` 无感知
4. 保持 `mkg/llm.py` 对外接口不变

## 非目标

- 不修改 agent 层（`mkg/agent/`）任何代码
- 不修改路由层（`backend/routes/`）任何代码
- 不修改前端任何代码

## 架构

```
mkg/llm_client.py    [新增] 原生 HTTP client（httpx）
mkg/llm_adapter.py   [新增] MKGChatModel(BaseChatModel) 适配器
mkg/llm.py           [修改] 保持对外接口不变，内部用 adapter + client

pyproject.toml       [修改] 删除 litellm、langchain-openai、langchain-anthropic
requirements.txt     [修改] 同上
```

依赖保留 `langchain-core`（agent 层需要 `BaseMessage`、`AIMessage` 等），新增 `httpx`（若未安装）。

## 组件设计

### 1. LLMClient（`mkg/llm_client.py`）

与 miniharness 基本一致，增加同步版本：

```python
class LLMClient:
    def __init__(self, api_key: str, provider: str, base_url: str = "", model: str = "")

    async def complete(self, prompt: str) -> str
    async def complete_messages(self, messages: list[dict], system: str = "") -> str

    # 新增同步接口（mkg/llm.py 的 generate() 目前同步）
    def complete_sync(self, prompt: str) -> str
    def complete_messages_sync(self, messages: list[dict], system: str = "") -> str
```

内置重试：429 和 `ReadTimeout` 指数退避（1s, 2s），最多 3 次，与 miniharness 一致。

- **anthropic**：`POST /v1/messages`，headers 含 `anthropic-version: 2023-06-01`、`User-Agent: claude-code/0.1.0`
- **openai**：`POST /v1/chat/completions`，headers 含 `User-Agent: claude-code/0.1.0`
- 默认模型：`claude-3-5-sonnet-latest`（anthropic）、`gpt-4o`（openai）

### 2. MKGChatModel（`mkg/llm_adapter.py`）

```python
class MKGChatModel(BaseChatModel):
    client: LLMClient

    def _generate(self, messages, stop, run_manager, **kwargs) -> ChatResult
    async def _agenerate(self, messages, stop, run_manager, **kwargs) -> ChatResult
```

职责：
1. 把 LangChain `BaseMessage`（`HumanMessage`/`SystemMessage`/`ToolMessage`）转成 `list[dict]`
2. 提取 `SystemMessage` 作为 `system` 参数
3. 调用 `LLMClient.complete_messages_sync()` / `complete_messages()`
4. 把响应字符串包回 `ChatResult(generations=[ChatGeneration(message=AIMessage(content=...))])`

属性：
- `_llm_type` → `"mkg"`
- `_identifying_params` → `{"provider": ..., "model": ...}`

### 3. mkg/llm.py（修改）

保持对外接口不变：

- `init_llm()` 内部改为创建 `LLMClient`，包装成 `MKGChatModel`
- `generate()` 改为直接调用 `LLMClient.complete_messages_sync()`，不再绕 LangChain 消息构建 → invoke → 解析
- `extract_text_content()` 保留但标记为 deprecated（新 client 直接返回 str）
- 删除 `ChatOpenAI`、`ChatAnthropic` 导入
- 保留 `BaseChatModel`、`HumanMessage`、`SystemMessage` 导入（`generate()` 构建 messages 用）

## 数据流

### Agent 层调用路径（零改动）

```
agent node:
  llm.invoke([HumanMessage(content=...), SystemMessage(content=...)])

    ↓

MKGChatModel._generate():
  1. 遍历 messages，按 role 分类：
     - SystemMessage → system_prompt
     - HumanMessage → {"role": "user", "content": ...}
     - ToolMessage → {"role": "tool", "content": ...}
  2. 调用 client.complete_messages_sync(msgs, system=system_prompt)

    ↓

LLMClient.complete_messages_sync():
  1. provider == "anthropic"：
     POST {base_url}/v1/messages
     headers: Authorization, anthropic-version, User-Agent: claude-code/...
     body: {model, max_tokens, messages, system?}
  2. provider == "openai"：
     POST {base_url}/v1/chat/completions
     headers: Authorization, User-Agent: claude-code/...
     body: {model, messages}（system 已插入 messages 头部）
  3. 解析 JSON，提取文本

    ↓

返回 str → 包装成：
  ChatResult(
    generations=[ChatGeneration(message=AIMessage(content=str))],
    llm_output={"provider": ..., "model": ...},
  )

    ↓

agent node 收到 AIMessage，继续执行
```

### generate() 直接调用路径（绕开 LangChain 包装）

```
mkg/llm.py generate(prompt, system_prompt):
  client.complete_messages_sync(
    [{"role": "user", "content": prompt}],
    system=system_prompt,
  )
  直接返回 str
```

## 错误处理

### LLMClient 内部

- `httpx.ReadTimeout` → 指数退避重试（1s, 2s），最多 3 次，仍失败抛出 `RuntimeError("LLM API timeout")`
- `httpx.HTTPStatusError` 429 → 指数退避重试，仍失败抛出
- 其他 `httpx.HTTPStatusError` → 直接抛出，携带 status code 和 response body
- `KeyError`（JSON 解析失败）→ `RuntimeError("Unexpected LLM response format")`

### MKGChatModel 层

- 捕获 LLMClient 抛出的异常，原样向上传递
- 不吞掉异常，让 agent 层的 LangGraph error handler 或路由层的 try/except 自行处理

### mkg/llm.py generate()

- 与现在行为一致：`get_llm_or_raise()` 未配置时抛 `ValueError`
- LLMClient 异常原样向上

## 测试策略

1. **`tests/test_llm_client.py`** — 测试 LLMClient（mock `httpx.AsyncClient` / `httpx.Client`）
   - `test_call_anthropic_success`
   - `test_call_openai_success`
   - `test_anthropic_retry_on_429`
   - `test_timeout_retry_and_fail`
   - `test_unknown_provider`

2. **`tests/test_llm_adapter.py`** — 测试 MKGChatModel（mock LLMClient）
   - `test_generate_with_human_and_system`
   - `test_generate_with_tool_message`
   - `test_agenerate_async`
   - `test_llm_type_and_params`

3. **现有 agent 测试** — 无需修改，作为回归测试，验证 `llm.invoke()` 行为不变

## 依赖变更

### 删除

- `litellm>=1.50.0`
- `langchain-openai>=0.2.0`
- `langchain-anthropic>=0.2.0`

### 保留

- `langchain>=0.3.0`（LangGraph 需要）
- `langgraph>=0.2.0`

### 新增

- `httpx>=0.26.0`（若 pyproject.toml 中未声明）

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| `BaseChatModel` 接口在后续 langchain-core 版本中变化 | 锁定 `langchain-core` 兼容版本；接口变化时 `MKGChatModel` 跟随调整 |
| 某些 agent 节点使用 `llm.bind_tools()` 或 `with_structured_output` | 当前代码 grep 未使用这些高级特性；如未来需要，再扩展 `MKGChatModel` |
| 同步 `complete_messages_sync` 在已有事件循环中调用会报错 | 使用 `httpx.Client` 做同步请求，不通过 `asyncio.run()` |
