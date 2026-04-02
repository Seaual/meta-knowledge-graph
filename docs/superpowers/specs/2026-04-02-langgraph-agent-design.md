# LangGraph Agent 架构重构设计

> **日期**: 2026-04-02
> **目标**: 将现有手动 Agent 架构迁移到 LangGraph，实现统一的多 Agent 协作架构

## 背景

当前 Agent 架构存在的问题：
- 手动意图识别（LLM + JSON 解析），不可靠
- 手动管理对话历史（字符串拼接最近 6 条）
- 各 Agent 代码分散，缺乏统一协调
- 无持久化记忆

## 设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 架构模式 | 简单单图架构 | 结构清晰、易于调试、执行路径可预测 |
| 意图识别 | 规则路由 | 快速可靠，无需 LLM 调用 |
| 历史管理 | Lead Agent 管理，专业 Agent 只看当前任务 | 避免上下文污染，聚焦任务 |
| 输出处理 | 根据复杂度决定是否汇总 | 灵活高效 |
| 数据访问 | LangChain Tools | 统一接口，便于测试和复用 |

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
│                    /api/agent/chat                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Graph                     │
│                                                              │
│  ┌─────────┐                                                 │
│  │  Entry  │                                                 │
│  └────┬────┘                                                 │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────┐    route_by_intent()                            │
│  │  Lead   │────────────────────────────────┐                │
│  │  Node   │                                 │                │
│  └────┬────┘                                 │                │
│       │                                      │                │
│       │ intent=lead ──► END                  │                │
│       │                                      ▼                │
│       │         ┌─────────┬─────────┬─────────────┐          │
│       │         │         │         │             │          │
│       │         ▼         ▼         ▼             ▼          │
│       │    ┌────────┐┌────────┐┌────────┐  ┌──────────┐      │
│       │    │Citation││Research││PaperQA │  │DeepResearch│    │
│       │    │  Node  ││  Node  ││  Node  │  │   Node    │     │
│       │    └────┬───┘└────┬───┘└────┬───┘  └─────┬─────┘     │
│       │         │         │         │            │           │
│       │         │         │         │            ▼           │
│       │         │         │         │     ┌───────────┐      │
│       │         │         │         │     │Summarize  │      │
│       │         │         │         │     │   Node    │      │
│       │         │         │         │     └─────┬─────┘      │
│       │         │         │         │           │            │
│       │         ▼         ▼         ▼           ▼            │
│       │                    END                                 │
│       │                                                      │
└───────┴──────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      LangChain Tools                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │search_paper  │ │get_paper_doi │ │read_pdf      │          │
│  │get_citations │ │get_concept   │ │move_paper    │          │
│  │search_s2     │ │create_folder │ │...           │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                               │
│     SQLite Database  │  Semantic Scholar API  │  PDF Files   │
└─────────────────────────────────────────────────────────────┘
```

## 核心状态设计

```python
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage, add_messages

class AgentState(TypedDict):
    # 对话历史（自动累加）
    messages: Annotated[List[BaseMessage], add_messages]

    # 上下文（当前关注的目标）
    current_target: Optional[Dict[str, Any]]  # {type: "paper"|"concept", id: str, name: str}
    uploaded_papers: List[Dict[str, str]]     # [{doi: str, title: str}]

    # 路由决策
    intent: str      # lead | citation | research | deep_research | paper_qa | move_paper
    target_name: Optional[str]

    # 输出
    response: str
    agent_used: str
    needs_summary: bool  # 是否需要 Lead Agent 汇总
```

## 路由规则设计

基于关键词的规则路由，无需 LLM 调用：

```python
ROUTING_RULES = {
    "citation": [
        "引用", "被引", "citation", "谁引用了", "引用了谁",
        "引用关系", "引用分析"
    ],
    "research": [
        "研究点", "研究方向", "研究机会", "概念分析",
        "有什么研究", "可以研究什么"
    ],
    "deep_research": [
        "深入研究", "系统分析", "详细研究", "全面分析",
        "帮我研究", "完整研究"
    ],
    "paper_qa": [
        "这篇论文讲了什么", "论文内容", "论文创新点",
        "论文摘要", "这篇论文是什么", "论文讲了啥"
    ],
    "move_paper": [
        "移动到", "放到", "新建文件夹", "把论文放到",
        "移到", "转移到"
    ],
}

def route_intent(message: str, context: dict) -> tuple[str, Optional[str]]:
    """
    规则路由函数

    Returns:
        (intent, target_name)
    """
    message_lower = message.lower()

    # 按优先级匹配关键词
    for intent, keywords in ROUTING_RULES.items():
        if any(kw in message_lower for kw in keywords):
            target_name = extract_target(message, context)
            return intent, target_name

    return "lead", None

def extract_target(message: str, context: dict) -> Optional[str]:
    """从消息或上下文提取目标名称"""
    # 代词处理
    pronouns = ["这篇论文", "这篇文章", "这个论文", "这个概念", "刚才上传的"]
    if any(p in message for p in pronouns):
        current = context.get("currentTarget")
        if current:
            return current.get("name")

    # TODO: 可后续用 NER 或正则提取论文/概念名称
    return None
```

## Tools 设计

### 数据访问 Tools

```python
from langchain_core.tools import tool
from mkg.database import Database
from mkg.semantic_scholar import S2Client
from mkg.pdf_parser import PDFParser

# 初始化依赖
_db = Database("mkg.db")
_s2_client = S2Client()
_pdf_parser = PDFParser()

@tool
def search_paper(query: str) -> dict:
    """在本地数据库搜索论文，返回匹配的论文列表"""
    papers = _db.search_papers(query)
    return {"papers": papers, "count": len(papers)}

@tool
def get_paper_by_doi(doi: str) -> dict:
    """根据 DOI 获取论文详情（元数据 + 本地路径）"""
    paper = _db.get_paper(doi)
    return paper or {"error": f"未找到论文: {doi}"}

@tool
def get_paper_citations(doi: str, include_s2: bool = True) -> dict:
    """
    获取论文的引用关系

    Args:
        doi: 论文 DOI
        include_s2: 是否从 Semantic Scholar 补充数据
    """
    paper = _db.get_paper(doi)
    if not paper:
        return {"error": "论文不存在"}

    citations = _db.get_citations(doi)

    if include_s2 and paper.get("s2_paper_id"):
        s2_citations = _s2_client.get_citations(paper["s2_paper_id"])
        citations.extend(s2_citations)

    return {"paper": paper, "citations": citations}

@tool
def get_concept_papers(concept_id: str, limit: int = 10) -> list:
    """获取概念关联的论文列表"""
    papers = _db.get_concept_papers(concept_id, limit=limit)
    return papers

@tool
def search_s2_papers(query: str, limit: int = 10) -> list:
    """在 Semantic Scholar 搜索论文（外部数据源）"""
    results = _s2_client.search_paper(query, limit=limit)
    return results

@tool
def read_pdf_content(doi: str, max_chars: int = 10000) -> str:
    """
    读取论文 PDF 全文

    Args:
        doi: 论文 DOI
        max_chars: 最大字符数，超出则截断
    """
    paper = _db.get_paper(doi)
    if not paper or not paper.get("pdf_path"):
        return "错误：论文 PDF 不存在"

    text = _pdf_parser.extract_text(paper["pdf_path"])
    if len(text) > max_chars:
        text = text[:max_chars] + "...(内容过长，已截断)"

    return text

@tool
def move_paper_to_folder(doi: str, folder_name: str, create_if_not_exist: bool = False) -> str:
    """
    移动论文到指定文件夹

    Args:
        doi: 论文 DOI
        folder_name: 目标文件夹名称
        create_if_not_exist: 文件夹不存在时是否创建
    """
    # 查找文件夹
    folders = _db.get_all_folders()
    target = next((f for f in folders if f["name"] == folder_name), None)

    if not target and create_if_not_exist:
        folder_id = _db.create_folder({"name": folder_name})
        target = {"id": folder_id, "name": folder_name}
    elif not target:
        return f"错误：文件夹「{folder_name}」不存在"

    _db.move_paper_to_folder(doi, target["id"])
    return f"已移动到「{folder_name}」"

@tool
def create_folder(name: str, description: str = "") -> str:
    """创建新文件夹"""
    folder_id = _db.create_folder({"name": name, "description": description})
    return f"已创建文件夹「{name}」(ID: {folder_id})"
```

### 各节点绑定的 Tools

| 节点 | 绑定的 Tools |
|------|-------------|
| LeadNode | `search_paper`, `move_paper_to_folder`, `create_folder` |
| CitationNode | `get_paper_by_doi`, `get_paper_citations`, `search_s2_papers` |
| ResearchNode | `get_concept_papers`, `search_s2_papers` |
| PaperQANode | `get_paper_by_doi`, `read_pdf_content` |
| DeepResearchNode | 所有 Tools |

## 节点设计

### Lead Node

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

LEAD_SYSTEM_PROMPT = """你是 Meta Knowledge Graph 的研究助手。
你可以帮助用户：
- 分析论文引用关系
- 发现概念的研究机会
- 深入研究主题
- 回答论文内容问题

请友好、简洁地回复用户。"""

def lead_node(state: AgentState) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    messages = [
        SystemMessage(content=LEAD_SYSTEM_PROMPT),
        *state["messages"]
    ]

    response = llm.invoke(messages)

    return {
        "response": response.content,
        "agent_used": "lead",
        "messages": [response],
    }
```

### Citation Node

```python
CITATION_PROMPT = """分析论文「{target_name}」的引用关系。

请使用以下工具获取数据：
1. get_paper_by_doi 或 search_paper 获取论文信息
2. get_paper_citations 获取引用数据

然后生成分析报告，包括：
- 被引统计（总数、年均、近年趋势）
- 高影响力引用者
- 引用领域分布
- 关键洞察
"""

def citation_node(state: AgentState) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    tools = [get_paper_by_doi, get_paper_citations, search_paper, search_s2_papers]
    llm_with_tools = llm.bind_tools(tools)

    target_name = state["target_name"]
    prompt = CITATION_PROMPT.format(target_name=target_name)

    # 调用 LLM（可能多次 tool call）
    response = llm_with_tools.invoke([
        HumanMessage(content=prompt)
    ])

    # 处理 tool calls（如果有的话）
    while response.tool_calls:
        # 执行工具调用
        for tool_call in response.tool_calls:
            # ... 执行并收集结果
            pass
        # 继续调用 LLM
        response = llm_with_tools.invoke(messages_with_tool_results)

    return {
        "response": response.content,
        "agent_used": "citation",
        "needs_summary": False,
        "messages": [response],
    }
```

### Paper QA Node

```python
PAPER_QA_PROMPT = """回答关于论文「{target_name}」的问题：{question}

请按以下步骤：
1. 使用 get_paper_by_doi 获取论文元数据
2. 如果问题简单（摘要、作者、关键词等），直接基于元数据回答
3. 如果问题复杂（方法、实验、结论等），使用 read_pdf_content 读取全文后回答
"""

def paper_qa_node(state: AgentState) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    tools = [get_paper_by_doi, read_pdf_content]
    llm_with_tools = llm.bind_tools(tools)

    question = state["messages"][-1].content
    target_name = state["target_name"]
    prompt = PAPER_QA_PROMPT.format(target_name=target_name, question=question)

    response = llm_with_tools.invoke([HumanMessage(content=prompt)])

    # 处理 tool calls...

    return {
        "response": response.content,
        "agent_used": "paper_qa",
        "needs_summary": False,
        "messages": [response],
    }
```

### Summarize Node

```python
SUMMARIZE_PROMPT = """以下是专业 Agent 生成的分析报告，请用简洁友好的方式总结要点：

{report}

请用中文总结（100字以内）。"""

def summarize_node(state: AgentState) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)

    prompt = SUMMARIZE_PROMPT.format(report=state["response"])
    summary = llm.invoke([HumanMessage(content=prompt)])

    return {
        "response": summary.content,
        "agent_used": state["agent_used"],  # 保持原 agent 标记
        "messages": [summary],
    }
```

## 图结构

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

def build_agent_graph():
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("lead", lead_node)
    graph.add_node("citation", citation_node)
    graph.add_node("research", research_node)
    graph.add_node("deep_research", deep_research_node)
    graph.add_node("paper_qa", paper_qa_node)
    graph.add_node("move_paper", move_paper_node)
    graph.add_node("summarize", summarize_node)

    # 入口：先到 lead，由 lead 决定路由
    graph.set_entry_point("lead")

    # 条件路由
    graph.add_conditional_edges(
        "lead",
        route_by_intent,
        {
            "citation": "citation",
            "research": "research",
            "deep_research": "deep_research",
            "paper_qa": "paper_qa",
            "move_paper": "move_paper",
            "end": END,
        }
    )

    # 简单节点直接结束
    for node in ["citation", "research", "paper_qa", "move_paper"]:
        graph.add_conditional_edges(
            node,
            lambda s: "summarize" if s.get("needs_summary") else END,
            {"summarize": "summarize", END: END}
        )

    # deep_research 固定走汇总
    graph.add_edge("deep_research", "summarize")
    graph.add_edge("summarize", END)

    # 记忆持久化
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "lead")
    if intent == "lead":
        return "end"
    return intent
```

## API 集成

```python
# backend/routes/agent.py

from langchain_core.messages import HumanMessage, AIMessage
from mkg.agent.graph import build_agent_graph, AgentState, route_intent

_agent_graph = None

def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph

@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest):
    graph = get_agent_graph()

    # 构建消息历史
    messages = []
    for m in request.history:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        else:
            messages.append(AIMessage(content=m.content))
    messages.append(HumanMessage(content=request.message))

    # 构建初始状态
    context = request.context.model_dump()
    intent, target_name = route_intent(request.message, context)

    initial_state: AgentState = {
        "messages": messages,
        "current_target": context.get("currentTarget"),
        "uploaded_papers": context.get("uploadedPapers", []),
        "intent": intent,
        "target_name": target_name,
        "response": "",
        "agent_used": "lead",
        "needs_summary": False,
    }

    # 执行图
    config = {"configurable": {"thread_id": "default"}}
    result = graph.invoke(initial_state, config)

    return AgentChatResponse(
        message=result["response"],
        agent=result["agent_used"],
        contextUpdate={"currentTarget": result.get("current_target")},
    )
```

## 依赖变更

### 新增依赖

```txt
langchain>=0.3.0
langchain-openai>=0.2.0
langgraph>=0.2.0
```

### 可移除代码

- `mkg/agent/lead_agent.py` 中的意图识别逻辑
- `mkg/agent/prompts.py` 中的 `LEAD_AGENT_SYSTEM_PROMPT`（迁移到节点）
- `backend/routes/agent.py` 中的手动路由分发逻辑

### 保留代码

- `mkg/database.py` - 数据库操作
- `mkg/semantic_scholar.py` - S2 API 客户端
- `mkg/pdf_parser.py` - PDF 解析（保留 LiteLLMClient 用于论文解析）
- 各专业 Agent 的核心分析逻辑（迁移到节点）

## 文件结构

```
mkg/agent/
├── __init__.py
├── graph.py              # NEW - LangGraph 图定义
├── state.py              # NEW - AgentState 定义
├── tools.py              # NEW - LangChain Tools
├── nodes/
│   ├── __init__.py
│   ├── lead.py           # NEW - Lead Node
│   ├── citation.py       # NEW - Citation Node
│   ├── research.py       # NEW - Research Node
│   ├── deep_research.py  # NEW - Deep Research Node
│   ├── paper_qa.py       # NEW - Paper QA Node
│   └── summarize.py      # NEW - Summarize Node
├── prompts.py            # MODIFY - 简化为节点提示词
└── routing.py            # NEW - 路由规则

backend/routes/
└── agent.py              # MODIFY - 接入 LangGraph
```

## 测试计划

1. **单元测试**：各 Tool 函数正确性
2. **节点测试**：各节点独立执行正确
3. **路由测试**：各种消息正确路由到目标节点
4. **集成测试**：完整对话流程
5. **性能测试**：响应时间对比（预期：路由阶段减少 ~500ms LLM 调用）

## 迁移步骤

1. 安装依赖：`langchain`, `langchain-openai`, `langgraph`
2. 创建 `mkg/agent/state.py` 定义 AgentState
3. 创建 `mkg/agent/tools.py` 封装 Tools
4. 创建 `mkg/agent/routing.py` 实现规则路由
5. 创建 `mkg/agent/nodes/` 各节点实现
6. 创建 `mkg/agent/graph.py` 组装图
7. 修改 `backend/routes/agent.py` 接入新架构
8. 测试并移除旧代码