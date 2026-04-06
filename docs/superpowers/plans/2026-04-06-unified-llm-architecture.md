# 统一 LLM 架构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将所有 LLM 调用统一为 LangChain Chat 模型，移除 LiteLLM 依赖。

**Architecture:** 创建统一 LLM 客户端 mkg/llm.py，根据 base_url 自动选择 ChatOpenAI 或 ChatAnthropic。所有模块（PDF 解析、Agent、CLI）统一使用此客户端。

**Tech Stack:** LangChain, langchain-openai, langchain-anthropic, langgraph

---

## 文件结构

### 新增文件
- `mkg/llm.py` - 统一 LLM 客户端（单例）
- `mkg/agent/research_graph.py` - Deep Research 多智能体

### 修改文件
- `mkg/pdf_parser.py` - 移除 LiteLLMClient，改用 mkg.llm
- `mkg/agent/graph.py` - 改用 mkg.llm 初始化
- `mkg/agent/tools.py` - 改用 mkg.llm，新增 deep_research tool
- `mkg/agent/nodes/lead.py` - 改用 mkg.llm
- `mkg/cli.py` - 改用 mkg.llm
- `backend/routes/agent.py` - 移除 LiteLLM 相关代码
- `backend/routes/llm.py` - 配置更新时重置 LLM
- `backend/routes/papers.py` - 处理论文时初始化 LLM

### 删除文件
- `mkg/agent/llm_config.py`
- `mkg/agent/lead_agent.py`
- `mkg/agent/citation_agent.py`
- `mkg/agent/research_agent.py`
- `mkg/agent/paper_qa_agent.py`
- `mkg/agent/deep_research_agent.py`
- `mkg/agent/prompts.py`

---

## Task 1: 创建统一 LLM 客户端

**Files:**
- Create: `mkg/llm.py`

- [ ] **Step 1: 创建 mkg/llm.py 文件**

```python
# mkg/llm.py
"""
统一 LLM 客户端 - 所有 LLM 调用通过 LangChain Chat 模型

支持：
- OpenAI 兼容 API（ChatOpenAI + base_url）
- Anthropic 兼容 API（ChatAnthropic + 环境变量）
"""

from typing import Optional, Dict, Any
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# 全局 LLM 实例
_llm_instance: Optional[BaseChatModel] = None
_current_config: Dict[str, Any] = {}


def init_llm(
    provider: str,
    api_key: str,
    model: str,
    base_url: Optional[str] = None
) -> BaseChatModel:
    """
    初始化 LLM 客户端

    根据 base_url 内容判断 API 格式：
    - 含 'anthropic' → ChatAnthropic
    - 其他 → ChatOpenAI

    Args:
        provider: 服务商名称（用于日志）
        api_key: API 密钥
        model: 模型名称
        base_url: API 地址（可选）

    Returns:
        初始化好的 LLM 实例
    """
    global _llm_instance, _current_config
    import os

    # 判断 API 格式
    use_anthropic = base_url and 'anthropic' in base_url.lower()

    if use_anthropic:
        # Anthropic 兼容 API
        # ChatAnthropic 通过环境变量设置 base_url
        if base_url:
            os.environ["ANTHROPIC_BASE_URL"] = base_url

        _llm_instance = ChatAnthropic(
            model=model,
            api_key=api_key,
        )
    else:
        # OpenAI 兼容 API
        _llm_instance = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

    _current_config = {
        'provider': provider,
        'model': model,
        'base_url': base_url,
    }

    return _llm_instance


def init_llm_from_db(db) -> Optional[BaseChatModel]:
    """
    从数据库配置初始化 LLM

    Args:
        db: Database 实例

    Returns:
        初始化好的 LLM 实例，如果配置不存在返回 None
    """
    config = db.get_llm_config()
    if not config or not config.get('providers'):
        return None

    provider_config = db.get_active_llm_provider()
    if not provider_config:
        provider_config = config['providers'][0]

    return init_llm(
        provider=provider_config.get('provider', 'openai'),
        api_key=provider_config.get('api_key'),
        model=provider_config.get('model', 'gpt-4o-mini'),
        base_url=provider_config.get('base_url'),
    )


def get_llm() -> Optional[BaseChatModel]:
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


def get_current_config() -> Dict[str, Any]:
    """
    获取当前 LLM 配置

    Returns:
        当前配置字典
    """
    return _current_config.copy()


def generate(prompt: str, system_prompt: Optional[str] = None) -> str:
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

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = llm.invoke(messages)
    return response.content
```

- [ ] **Step 2: 验证文件创建成功**

Run: `ls -la mkg/llm.py`
Expected: 文件存在

- [ ] **Step 3: 提交**

```bash
git add mkg/llm.py
git commit -m "feat: add unified LLM client mkg/llm.py"
```

---

## Task 2: 重构 mkg/agent/graph.py

**Files:**
- Modify: `mkg/agent/graph.py`

- [ ] **Step 1: 读取当前文件内容**

Run: `cat mkg/agent/graph.py`

- [ ] **Step 2: 修改导入和初始化逻辑**

将文件修改为：

```python
# mkg/agent/graph.py
"""
LangGraph Agent 图定义 - 简化版

所有功能通过 lead node 的 tool 调用实现
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .tools import init_tools
from .nodes import lead_node
from mkg.llm import init_llm_from_db


def build_agent_graph(db=None, s2_client=None, pdf_parser=None):
    """
    构建 LangGraph Agent 图

    简化架构：只有一个 lead node，通过 tool 调用实现所有功能
    """
    # 初始化 LLM
    init_llm_from_db(db)

    # 初始化 Tools 依赖
    init_tools(db=db, s2_client=s2_client, pdf_parser=pdf_parser)

    # 创建图
    graph = StateGraph(AgentState)

    # 只添加一个节点
    graph.add_node("lead", lead_node)

    # 设置入口
    graph.set_entry_point("lead")

    # lead 直接结束
    graph.add_edge("lead", END)

    # 添加记忆持久化
    memory = MemorySaver()

    return graph.compile(checkpointer=memory)


# 单例
_compiled_graph = None


def get_agent_graph(db=None, s2_client=None, pdf_parser=None):
    """获取编译后的 Agent 图（单例）"""
    global _compiled_graph

    # 初始化 LLM
    init_llm_from_db(db)

    if _compiled_graph is None:
        _compiled_graph = build_agent_graph(db, s2_client, pdf_parser)

    return _compiled_graph


def reset_graph():
    """重置图"""
    global _compiled_graph
    _compiled_graph = None
    from mkg.llm import reset_llm
    reset_llm()
```

- [ ] **Step 3: 提交**

```bash
git add mkg/agent/graph.py
git commit -m "refactor: use mkg.llm in agent graph"
```

---

## Task 3: 重构 mkg/agent/nodes/lead.py

**Files:**
- Modify: `mkg/agent/nodes/lead.py`

- [ ] **Step 1: 读取当前文件**

Run: `cat mkg/agent/nodes/lead.py`

- [ ] **Step 2: 修改导入**

修改文件开头的导入部分：

```python
# mkg/agent/nodes/lead.py
"""
Lead Node - 统一对话节点

所有功能都通过 tool 调用实现
"""

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import Dict, Any

from ..state import AgentState
from .. import tools
from mkg.llm import get_llm_or_raise
```

删除这一行：
```python
from ..llm_config import get_llm_or_raise
```

- [ ] **Step 3: 提交**

```bash
git add mkg/agent/nodes/lead.py
git commit -m "refactor: use mkg.llm in lead node"
```

---

## Task 4: 重构 mkg/agent/tools.py

**Files:**
- Modify: `mkg/agent/tools.py`

- [ ] **Step 1: 读取当前文件**

Run: `cat mkg/agent/tools.py`

- [ ] **Step 2: 修改导入部分**

在文件开头，将：
```python
from ..llm_config import get_llm_or_raise
```

改为：
```python
from mkg.llm import get_llm_or_raise, generate
```

- [ ] **Step 3: 在文件末尾添加 deep_research tool**

在 `ALL_TOOLS` 列表之前添加：

```python
# ============================================================
# Deep Research Tool
# ============================================================

@tool
def deep_research(target_name: str, target_type: str, query: str,
                  dimensions: Optional[List[str]] = None) -> Dict[str, Any]:
    """深入研究 - 多智能体协作分析。

    启动多个维度的研究 agent，并行分析后综合报告。
    当用户说"深入研究"、"全面分析"时调用。

    Args:
        target_name: 研究目标名称（概念或论文标题）
        target_type: 目标类型 ('concept' | 'paper')
        query: 研究问题
        dimensions: 研究维度（可选，默认自动生成）

    Returns:
        研究报告，包含各维度分析和综合结论
    """
    from mkg.agent.research_graph import run_deep_research

    try:
        result = run_deep_research(
            target_name=target_name,
            target_type=target_type,
            query=query,
            dimensions=dimensions
        )
        return result
    except Exception as e:
        return {"error": f"深入研究失败: {str(e)}"}
```

- [ ] **Step 4: 更新 ALL_TOOLS 列表**

在 `ALL_TOOLS` 列表中添加 `deep_research`：

```python
ALL_TOOLS = [
    # 论文相关
    search_paper,
    get_paper_by_title,
    read_paper_content,
    # 引用分析
    analyze_citations,
    # 概念相关
    get_concept_graph,
    analyze_research_points,
    # 深入研究
    deep_research,
    # 文件夹管理
    list_folders,
    move_paper_to_folder,
    create_folder,
]
```

- [ ] **Step 5: 提交**

```bash
git add mkg/agent/tools.py
git commit -m "refactor: use mkg.llm in tools, add deep_research tool"
```

---

## Task 5: 创建 Deep Research 多智能体

**Files:**
- Create: `mkg/agent/research_graph.py`

- [ ] **Step 1: 创建文件**

```python
# mkg/agent/research_graph.py
"""
Deep Research 多智能体架构

使用 LangGraph 实现多维度并行研究
"""

import json
import asyncio
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from mkg.llm import get_llm_or_raise, generate


class ResearchState(TypedDict):
    """研究状态"""
    target_name: str
    target_type: str
    query: str
    dimensions: List[str]
    dimension_findings: Dict[str, str]
    final_report: str


def coordinator_node(state: ResearchState) -> Dict[str, Any]:
    """
    协调者节点 - 规划研究维度

    分析研究目标，生成 3-5 个研究维度
    """
    llm = get_llm_or_raise()

    prompt = f"""分析以下研究目标，规划 3-5 个研究维度。

目标：{state['target_name']} ({state['target_type']})
研究问题：{state['query']}

要求：
- 维度应该覆盖不同角度（如技术、应用、趋势、挑战等）
- 每个维度用一个简短的词组描述

返回 JSON 数组格式：["维度1", "维度2", "维度3", ...]
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        # 处理可能的 markdown 代码块
        if content.startswith('```'):
            lines = content.split('\n')
            start_idx = 1
            end_idx = len(lines)
            if lines[-1].strip() == '```':
                end_idx = len(lines) - 1
            content = '\n'.join(lines[start_idx:end_idx])

        dimensions = json.loads(content)

        if not isinstance(dimensions, list):
            dimensions = ["技术分析", "应用场景", "发展趋势"]

        return {"dimensions": dimensions[:5]}

    except Exception as e:
        # 默认维度
        return {"dimensions": ["技术分析", "应用场景", "发展趋势", "挑战与机遇"]}


async def dimension_agent_async(dimension: str, target_name: str, target_type: str, query: str) -> tuple:
    """
    单维度异步研究
    """
    llm = get_llm_or_raise()

    prompt = f"""从「{dimension}」维度进行深入研究。

研究目标：{target_name} ({target_type})
核心问题：{query}

要求：
- 基于该维度提供深入的分析
- 包含具体的事实或数据支撑
- 给出有价值的见解

输出该维度的研究发现（200字以内）。
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return (dimension, response.content)
    except Exception as e:
        return (dimension, f"分析失败: {str(e)}")


def research_node(state: ResearchState) -> Dict[str, Any]:
    """
    研究节点 - 并行执行各维度研究
    """
    async def run_all_dimensions():
        tasks = [
            dimension_agent_async(
                dimension=dim,
                target_name=state['target_name'],
                target_type=state['target_type'],
                query=state['query']
            )
            for dim in state['dimensions']
        ]
        results = await asyncio.gather(*tasks)
        return dict(results)

    # 运行异步任务
    findings = asyncio.run(run_all_dimensions())

    return {"dimension_findings": findings}


def synthesizer_node(state: ResearchState) -> Dict[str, Any]:
    """
    综合者节点 - 汇总各维度发现，生成报告
    """
    llm = get_llm_or_raise()

    # 格式化各维度发现
    findings_text = "\n\n".join([
        f"### {dim}\n{finding}"
        for dim, finding in state['dimension_findings'].items()
    ])

    prompt = f"""综合以下各维度的研究发现，生成完整的研究报告。

## 研究目标
{state['target_name']} ({state['target_type']})
核心问题：{state['query']}

## 各维度发现
{findings_text}

## 要求
生成结构化报告，包含：
1. **摘要**（50字以内概括主要发现）
2. **各维度分析**（整合上述发现，避免重复）
3. **结论与建议**（基于分析给出可操作的建议）

使用 Markdown 格式输出。
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"final_report": response.content}
    except Exception as e:
        return {"final_report": f"报告生成失败: {str(e)}"}


def build_research_graph():
    """
    构建研究多智能体图
    """
    graph = StateGraph(ResearchState)

    # 添加节点
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("research", research_node)
    graph.add_node("synthesizer", synthesizer_node)

    # 设置流程
    graph.set_entry_point("coordinator")
    graph.add_edge("coordinator", "research")
    graph.add_edge("research", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


def run_deep_research(
    target_name: str,
    target_type: str,
    query: str,
    dimensions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    执行深入研究

    Args:
        target_name: 研究目标名称
        target_type: 目标类型 ('concept' | 'paper')
        query: 研究问题
        dimensions: 预设维度（可选）

    Returns:
        研究报告和中间结果
    """
    graph = build_research_graph()

    initial_state: ResearchState = {
        "target_name": target_name,
        "target_type": target_type,
        "query": query,
        "dimensions": dimensions or [],
        "dimension_findings": {},
        "final_report": "",
    }

    result = graph.invoke(initial_state)

    return {
        "report": result["final_report"],
        "dimensions": result["dimensions"],
        "findings": result["dimension_findings"],
    }
```

- [ ] **Step 2: 验证文件创建**

Run: `ls -la mkg/agent/research_graph.py`
Expected: 文件存在

- [ ] **Step 3: 提交**

```bash
git add mkg/agent/research_graph.py
git commit -m "feat: add deep research multi-agent graph"
```

---

## Task 6: 重构 mkg/pdf_parser.py

**Files:**
- Modify: `mkg/pdf_parser.py`

- [ ] **Step 1: 读取文件，找到 LiteLLMClient 类的位置**

Run: `grep -n "class LiteLLMClient" mkg/pdf_parser.py`

- [ ] **Step 2: 删除 LiteLLMClient、ClaudeCLIClient、LLMClient 类**

删除从 `class LLMClient:` 开始到文件末尾的所有内容（约 1450 行之后的内容）。

保留文件开头的导入和 PDFParser 类（1-1449 行左右）。

- [ ] **Step 3: 修改 PDFParser 类**

在 PDFParser 类中，找到所有 `self.llm_client` 的使用，改为使用 `mkg.llm.generate()`。

主要修改 `__init__` 方法和 `extract_concepts` 方法：

```python
class PDFParser:
    """PDF 解析器"""

    def __init__(self):
        """初始化 PDF 解析器"""
        pass  # 不再需要 llm_client

    def extract_concepts(self, pdf_path: str, title: str = None) -> dict:
        """
        提取概念树

        Args:
            pdf_path: PDF 文件路径
            title: 论文标题（可选）

        Returns:
            概念树字典
        """
        from mkg.llm import generate

        # 提取文本
        text = self.extract_text(pdf_path)

        # 截断过长的文本
        if len(text) > 30000:
            text = text[:30000]

        # 构建 prompt
        prompt = STAGE1_SUMMARY_PROMPT.format(
            title=title or '',
            authors='',
            abstract='',
            body=text
        )

        # 调用 LLM
        response = generate(
            prompt=prompt,
            system_prompt="You are an academic knowledge graph builder. Extract concepts and their hierarchical relationships from research papers."
        )

        # 解析响应
        return self._parse_response(response)
```

- [ ] **Step 4: 移除不再需要的导入**

删除文件顶部与 LiteLLM 相关的导入（如果有的话）。

- [ ] **Step 5: 提交**

```bash
git add mkg/pdf_parser.py
git commit -m "refactor: remove LiteLLMClient, use mkg.llm in PDFParser"
```

---

## Task 7: 重构 backend/routes/agent.py

**Files:**
- Modify: `backend/routes/agent.py`

- [ ] **Step 1: 读取当前文件**

Run: `cat backend/routes/agent.py`

- [ ] **Step 2: 修改导入**

将：
```python
from mkg.agent.graph import get_agent_graph, reset_graph
from mkg.agent.routing import route_intent
from mkg.agent.state import AgentState
```

改为：
```python
from mkg.agent.graph import get_agent_graph, reset_graph
from mkg.agent.state import AgentState
from mkg.llm import init_llm_from_db, reset_llm
```

- [ ] **Step 3: 删除 get_deep_research_agent 函数**

删除 `get_deep_research_agent()` 函数（约 73-100 行）。

- [ ] **Step 4: 修改 chat 函数**

确保 chat 函数使用 `init_llm_from_db`：

```python
@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest):
    """处理用户对话"""
    db = get_db()

    # 初始化 LLM
    init_llm_from_db(db)

    config = db.get_llm_config()
    if not config or not config.get('providers'):
        raise HTTPException(
            status_code=500,
            detail="LLM 未配置，请先在设置中配置 API Key"
        )

    # 获取 LangGraph Agent
    graph = get_agent_graph(
        db=db,
        s2_client=get_s2_client(),
        pdf_parser=get_pdf_parser()
    )

    # ... 其余逻辑不变
```

- [ ] **Step 5: 修改 deep-research 端点**

将 deep-research 相关端点改为使用 tools：

```python
@router.post("/deep-research/start")
def start_deep_research(request: DeepResearchStartRequest):
    """启动深入研究任务"""
    from mkg.agent.tools import deep_research

    init_llm_from_db(get_db())

    try:
        result = deep_research.invoke({
            "target_name": request.targetName,
            "target_type": request.targetType,
            "query": request.query,
            "dimensions": request.dimensions
        })

        return {
            "sessionId": "sync",
            "status": "completed",
            "report": result.get("report", ""),
            "dimensions": result.get("dimensions", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deep-research/{session_id}/status")
def get_research_status(session_id: str):
    """获取研究进度（已改为同步，保留兼容）"""
    return {
        "status": "completed",
        "progress": 100,
        "dimensions": [],
        "completedDimensions": []
    }


@router.get("/deep-research/{session_id}/report")
def get_research_report(session_id: str):
    """获取研究报告（已改为同步，保留兼容）"""
    return {"report": "请直接调用 deep-research/start 获取报告", "format": "markdown"}
```

- [ ] **Step 6: 修改 reset 端点**

```python
@router.post("/reset")
def reset_agent():
    """重置 Agent 图"""
    reset_graph()
    return {"status": "ok"}
```

- [ ] **Step 7: 提交**

```bash
git add backend/routes/agent.py
git commit -m "refactor: use mkg.llm in agent routes, simplify deep-research"
```

---

## Task 8: 重构 backend/routes/llm.py

**Files:**
- Modify: `backend/routes/llm.py`

- [ ] **Step 1: 找到保存配置的端点**

Run: `grep -n "def save_config\|def save" backend/routes/llm.py`

- [ ] **Step 2: 添加 reset_llm 调用**

在保存配置的端点中，添加重置 LLM 的逻辑：

```python
from mkg.llm import reset_llm

@router.post("/config")
def save_config(config: LLMConfigRequest):
    """保存 LLM 配置"""
    # ... 保存到数据库的逻辑 ...

    # 重置 LLM 实例，下次调用时重新初始化
    reset_llm()

    return {"status": "ok"}
```

- [ ] **Step 3: 提交**

```bash
git add backend/routes/llm.py
git commit -m "refactor: reset LLM instance on config update"
```

---

## Task 9: 重构 backend/routes/papers.py

**Files:**
- Modify: `backend/routes/papers.py`

- [ ] **Step 1: 找到 process 端点**

Run: `grep -n "def process" backend/routes/papers.py`

- [ ] **Step 2: 添加 LLM 初始化**

在处理论文的端点中添加 LLM 初始化：

```python
from mkg.llm import init_llm_from_db

@router.post("/process")
def process_paper(request: ProcessRequest):
    """处理论文"""
    db = get_db()

    # 初始化 LLM
    init_llm_from_db(db)

    # ... 其余逻辑 ...
```

- [ ] **Step 3: 提交**

```bash
git add backend/routes/papers.py
git commit -m "refactor: init LLM before paper processing"
```

---

## Task 10: 重构 mkg/cli.py

**Files:**
- Modify: `mkg/cli.py`

- [ ] **Step 1: 找到 LiteLLMClient 的使用**

Run: `grep -n "LiteLLMClient" mkg/cli.py`

- [ ] **Step 2: 替换为 mkg.llm**

将所有 `LiteLLMClient` 的使用替换为 `mkg.llm`：

```python
from mkg.llm import init_llm_from_db, generate

# 在需要使用 LLM 的地方：
init_llm_from_db(db)
response = generate(prompt, system_prompt="...")
```

- [ ] **Step 3: 提交**

```bash
git add mkg/cli.py
git commit -m "refactor: use mkg.llm in CLI"
```

---

## Task 11: 删除旧文件

**Files:**
- Delete: `mkg/agent/llm_config.py`
- Delete: `mkg/agent/lead_agent.py`
- Delete: `mkg/agent/citation_agent.py`
- Delete: `mkg/agent/research_agent.py`
- Delete: `mkg/agent/paper_qa_agent.py`
- Delete: `mkg/agent/deep_research_agent.py`
- Delete: `mkg/agent/prompts.py`

- [ ] **Step 1: 删除文件**

```bash
rm mkg/agent/llm_config.py
rm mkg/agent/lead_agent.py
rm mkg/agent/citation_agent.py
rm mkg/agent/research_agent.py
rm mkg/agent/paper_qa_agent.py
rm mkg/agent/deep_research_agent.py
rm mkg/agent/prompts.py
```

- [ ] **Step 2: 提交**

```bash
git add -A
git commit -m "refactor: remove old agent files, unified to tools"
```

---

## Task 12: 更新 mkg/agent/__init__.py

**Files:**
- Modify: `mkg/agent/__init__.py`

- [ ] **Step 1: 更新导出**

```python
# mkg/agent/__init__.py
"""
LangGraph Agent 模块
"""

from .graph import get_agent_graph, reset_graph
from .tools import ALL_TOOLS

__all__ = ["get_agent_graph", "reset_graph", "ALL_TOOLS"]
```

- [ ] **Step 2: 提交**

```bash
git add mkg/agent/__init__.py
git commit -m "refactor: update agent __init__.py exports"
```

---

## Task 13: 测试验证

- [ ] **Step 1: 启动后端服务**

```bash
cd D:/meta-knowledge-graph-main
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Expected: 服务正常启动，无导入错误

- [ ] **Step 2: 测试 LLM 配置 API**

```bash
curl http://localhost:8000/api/llm/config
```

Expected: 返回当前 LLM 配置

- [ ] **Step 3: 测试 Chat API**

在前端发送消息测试：
- "查看图谱"
- "分析引用"
- "深入研究多智能体系统的应用"

Expected: 正常返回响应，工具调用正常

- [ ] **Step 4: 测试 PDF 上传和处理**

上传一个 PDF 论文，测试概念提取是否正常。

Expected: 论文正常处理，概念树正常提取

---

## Task 14: 最终提交

- [ ] **Step 1: 检查所有更改**

```bash
git status
git log --oneline -10
```

- [ ] **Step 2: 推送到远程（如需要）**

```bash
git push origin main
```

---

## 自检清单

完成所有任务后，确认：

- [ ] `mkg/llm.py` 已创建并可用
- [ ] 所有 LiteLLM 引用已移除
- [ ] 所有 agent 文件使用 `mkg.llm`
- [ ] 旧 agent 文件已删除
- [ ] Deep Research 作为 tool 可用
- [ ] 后端服务正常启动
- [ ] Chat API 测试通过
- [ ] PDF 处理测试通过