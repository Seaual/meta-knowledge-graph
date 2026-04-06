# 统一 LLM 架构设计

## 概述

将 Meta Knowledge Graph 中所有 LLM 调用统一为 LangChain Chat 模型，支持 OpenAI 和 Anthropic 两种 API 格式。

## 目标

- 统一所有 LLM 调用，移除 LiteLLM 依赖
- 支持 OpenAI 兼容 API 和 Anthropic 兼容 API
- 根据 base_url 自动判断 API 格式
- 简化 agent 架构，所有功能作为 tools

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      mkg/llm.py                              │
│              统一 LLM 客户端（单例）                          │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  ChatOpenAI     │    │ ChatAnthropic   │                 │
│  │  + base_url     │    │ + base_url      │                 │
│  └─────────────────┘    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
           ▲                ▲                ▲
           │                │                │
    ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
    │ pdf_parser  │  │ agent/tools │  │    CLI      │
    │             │  │             │  │             │
    │ generate()  │  │ bind_tools()│  │ generate()  │
    └─────────────┘  └─────────────┘  └─────────────┘
```

## API 格式判断逻辑

沿用现有 LiteLLMClient 的判断方式：

```python
if base_url and 'anthropic' in base_url.lower():
    # Anthropic 兼容 API
    return ChatAnthropic(model=model, api_key=api_key, anthropic_api_url=base_url)
else:
    # OpenAI 兼容 API
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url)
```

## 统一调用方式

所有地方都使用 LangChain messages 格式：

```python
from langchain_core.messages import SystemMessage, HumanMessage

# 对话场景（支持 function calling）
llm = get_llm_or_raise()
llm_with_tools = llm.bind_tools(tools)
response = llm_with_tools.invoke([
    SystemMessage(content="You are..."),
    HumanMessage(content="用户输入")
])

# 单次生成场景（PDF 解析等）
from mkg.llm import generate
response = generate(prompt, system_prompt="...")
```

## 文件变更

### 新增文件

| 文件 | 说明 |
|------|------|
| `mkg/llm.py` | 统一 LLM 客户端 |
| `mkg/agent/research_graph.py` | Deep Research 多智能体实现 |

### 重构文件

| 文件 | 变更说明 |
|------|----------|
| `mkg/pdf_parser.py` | 移除 LiteLLMClient，改用 mkg.llm |
| `mkg/agent/graph.py` | 改用 mkg.llm 初始化 |
| `mkg/agent/tools.py` | 改用 mkg.llm，新增 deep_research tool |
| `mkg/agent/nodes/lead.py` | 改用 mkg.llm |
| `mkg/cli.py` | 改用 mkg.llm |
| `backend/routes/agent.py` | 移除 LiteLLM 相关代码 |
| `backend/routes/llm.py` | 配置更新时重置 LLM |
| `backend/routes/papers.py` | 处理论文时初始化 LLM |

### 删除文件

| 文件 | 原因 |
|------|------|
| `mkg/agent/llm_config.py` | 合并到 mkg/llm.py |
| `mkg/agent/lead_agent.py` | 功能已迁移到 LangGraph |
| `mkg/agent/citation_agent.py` | 功能已迁移到 tools |
| `mkg/agent/research_agent.py` | 功能已迁移到 tools |
| `mkg/agent/paper_qa_agent.py` | 功能已迁移到 tools |
| `mkg/agent/deep_research_agent.py` | 功能已迁移到 tools |
| `mkg/agent/prompts.py` | prompts 分散到各处 |

## 详细设计

### 1. 统一 LLM 客户端 (mkg/llm.py)

```python
"""
统一 LLM 客户端 - 所有 LLM 调用通过 LangChain Chat 模型
"""

from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

_llm_instance: Optional[BaseChatModel] = None

def init_llm(provider: str, api_key: str, model: str, base_url: Optional[str] = None) -> BaseChatModel:
    """初始化 LLM 客户端，根据 base_url 判断 API 格式"""
    global _llm_instance

    if base_url and 'anthropic' in base_url.lower():
        _llm_instance = ChatAnthropic(
            model=model,
            api_key=api_key,
            anthropic_api_url=base_url,
        )
    else:
        _llm_instance = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

    return _llm_instance

def init_llm_from_db(db) -> Optional[BaseChatModel]:
    """从数据库配置初始化 LLM"""
    config = db.get_llm_config()
    if not config or not config.get('providers'):
        return None

    provider_config = db.get_active_llm_provider() or config['providers'][0]
    return init_llm(
        provider=provider_config.get('provider', 'openai'),
        api_key=provider_config.get('api_key'),
        model=provider_config.get('model', 'gpt-4o-mini'),
        base_url=provider_config.get('base_url'),
    )

def get_llm() -> Optional[BaseChatModel]:
    """获取 LLM 实例"""
    return _llm_instance

def get_llm_or_raise() -> BaseChatModel:
    """获取 LLM 实例，未配置则抛异常"""
    if _llm_instance is None:
        raise ValueError("LLM 未配置，请先在设置中配置 API Key")
    return _llm_instance

def reset_llm():
    """重置 LLM（配置更新时调用）"""
    global _llm_instance
    _llm_instance = None

def generate(prompt: str, system_prompt: str = None) -> str:
    """简化的单次生成接口"""
    llm = get_llm_or_raise()

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = llm.invoke(messages)
    return response.content
```

### 2. PDF 解析器重构 (mkg/pdf_parser.py)

移除 LiteLLMClient、ClaudeCLIClient、LLMClient 类。

```python
from mkg.llm import generate

class PDFParser:
    def extract_concepts(self, text: str, title: str = None) -> dict:
        prompt = STAGE1_SUMMARY_PROMPT.format(...)
        response = generate(
            prompt=prompt,
            system_prompt="You are an academic knowledge graph builder."
        )
        return self._parse_response(response)
```

### 3. Agent 架构

最终文件结构：

```
mkg/agent/
├── __init__.py
├── graph.py           # 主对话 LangGraph
├── research_graph.py  # Deep Research 多智能体
├── routing.py         # 路由（简化版）
├── state.py           # 状态定义
├── tools.py           # 所有 tools
└── nodes/
    ├── __init__.py
    └── lead.py        # 主节点
```

### 4. Deep Research Tool

作为 tool 实现，内部使用 LangGraph 多智能体架构：

```
deep_research_tool
    │
    ├── coordinator_node（规划维度）
    │
    ├── research_node（并行研究）
    │       └── dimension_agent × N
    │
    └── synthesizer_node（综合报告）
```

## 实施步骤

1. 创建 `mkg/llm.py` 统一 LLM 客户端
2. 创建 `mkg/agent/research_graph.py` 多智能体实现
3. 重构 `mkg/pdf_parser.py`
4. 重构 `mkg/agent/` 下相关文件
5. 重构 `backend/routes/` 下相关文件
6. 重构 `mkg/cli.py`
7. 删除旧文件
8. 测试验证

## 依赖更新

`requirements.txt` 已包含所需依赖：
- langchain
- langchain-openai
- langchain-anthropic
- langgraph

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| Anthropic base_url 兼容性 | 测试验证 ChatAnthropic 的 base_url 参数 |
| function calling 在非原生 API 上的兼容性 | 测试阿里云等代理 API 的 function calling 支持 |
| PDF 解析大文本处理 | 保持截断逻辑，确保不超过模型上下文限制 |