# Chat 附件系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Chat 页面建立统一附件系统，让 LLM Agent 以对话驱动方式覆盖概念页面的所有功能，返回"文字分析 + 结构化可交互卡片"。

**Architecture:** 后端 Agent 每个 tool 执行后，将结构化结果收集到 `attachments` 列表中，同时 LLM 生成文字总结。前端根据 attachment type 分发渲染对应卡片组件，卡片内操作按钮发送消息回 Chat 实现对话闭环。

**Tech Stack:** Python/FastAPI/LangGraph (后端), React/TypeScript/Zustand (前端), force-graph (图谱渲染)

**Spec:** `docs/superpowers/specs/2026-04-06-chat-attachment-system-design.md`

---

## File Structure

### Backend files to modify
- `mkg/agent/state.py` — 增加 `attachments` 字段
- `backend/schemas.py` — `AgentChatResponse` 增加 `attachments`
- `backend/routes/agent.py` — 传递 `attachments` 到响应
- `mkg/agent/nodes/lead.py` — 附件收集逻辑、tool-attachment 映射、摘要生成
- `mkg/agent/tools.py` — 新增 `recommend_papers` tool，改造 `analyze_research_points`

### Frontend files to modify
- `frontend/src/stores/agentStore.ts` — `Message` 增加 `attachments` 类型
- `frontend/src/lib/api.ts` — `AgentChatResponse` 增加 `attachments`
- `frontend/src/pages/Chat.tsx` — 接入 ChatAttachments 分发组件

### Frontend files to create
- `frontend/src/components/ChatAttachments.tsx` — 附件分发组件
- `frontend/src/components/cards/ResearchPointsCard.tsx`
- `frontend/src/components/cards/PaperDetailCard.tsx`
- `frontend/src/components/cards/PaperListCard.tsx`
- `frontend/src/components/cards/RecommendationCard.tsx`
- `frontend/src/components/cards/CitationAnalysisCard.tsx`

---

## Task 1: 后端数据层 — AgentState 和 Schema 增加 attachments

**Files:**
- Modify: `mkg/agent/state.py:11-33`
- Modify: `backend/schemas.py:329-336`

- [ ] **Step 1: 修改 AgentState 增加 attachments 字段**

在 `mkg/agent/state.py` 的 `AgentState` TypedDict 中增加 `attachments` 字段：

```python
# mkg/agent/state.py
"""
LangGraph Agent 状态定义
"""

from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """
    LangGraph Agent 统一状态

    所有节点共享此状态，通过 Annotated 实现消息自动累加
    """

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
    concept_data: Optional[Dict[str, Any]]  # deprecated，向后兼容
    attachments: List[Dict[str, Any]]  # 新增：[{type: str, data: dict}]
```

- [ ] **Step 2: 修改 AgentChatResponse 增加 attachments 字段**

在 `backend/schemas.py` 的 `AgentChatResponse` 类中增加 `attachments`：

```python
class AgentChatResponse(BaseModel):
    """Response from agent chat endpoint"""
    message: str
    agent: str
    contextUpdate: Optional[dict] = None
    researchSessionId: Optional[str] = None
    conceptData: Optional[ConceptGraphData] = None  # deprecated，向后兼容
    attachments: Optional[List[dict]] = None  # 新增：结构化附件列表
```

- [ ] **Step 3: 修改 agent route 传递 attachments**

在 `backend/routes/agent.py` 的 `chat` 函数中，从 result 提取 attachments 并传递到响应：

```python
@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest):
    # ... 现有逻辑不变 ...

    # 执行图
    config = {"configurable": {"thread_id": "default"}}
    result = graph.invoke(initial_state, config)

    # 提取概念数据（向后兼容）
    concept_data = result.get("concept_data")

    # 提取附件
    attachments = result.get("attachments", [])

    # 如果有 concept_data 但 attachments 中没有 concept_graph，自动迁移
    if concept_data and not any(a.get("type") == "concept_graph" for a in attachments):
        attachments.append({"type": "concept_graph", "data": concept_data})

    return AgentChatResponse(
        message=result.get("response", "抱歉，处理请求时遇到问题。"),
        agent=result.get("agent_used", "lead"),
        conceptData=concept_data,
        attachments=attachments if attachments else None,
    )
```

- [ ] **Step 4: 验证后端启动无报错**

Run: `cd backend && python -c "from schemas import AgentChatResponse; print('OK')"`
Expected: `OK`

Run: `cd mkg/agent && python -c "from state import AgentState; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add mkg/agent/state.py backend/schemas.py backend/routes/agent.py
git commit -m "feat: add attachments field to AgentState and AgentChatResponse"
```

---

## Task 2: Lead Node 附件收集逻辑

**Files:**
- Modify: `mkg/agent/nodes/lead.py:1-153`

- [ ] **Step 1: 添加附件映射和辅助函数**

在 `mkg/agent/nodes/lead.py` 文件顶部（`LEAD_SYSTEM_PROMPT` 之前）增加附件映射和辅助函数：

```python
from typing import Dict, Any, Optional, List

# Tool -> Attachment 类型映射
TOOL_ATTACHMENT_MAP = {
    "analyze_research_points": "research_points",
    "get_paper_by_title": "paper_detail",
    "search_paper": "paper_list",
    "get_concept_graph": "concept_graph",
    "analyze_citations": "citation_analysis",
    "recommend_papers": "recommendation",
}


def make_attachment(tool_name: str, result) -> Optional[Dict[str, Any]]:
    """将 tool 执行结果转换为附件"""
    att_type = TOOL_ATTACHMENT_MAP.get(tool_name)
    if not att_type:
        return None
    if isinstance(result, str):
        return None
    if isinstance(result, dict) and "error" in result:
        return None
    return {"type": att_type, "data": result}


def summarize_for_llm(tool_name: str, result) -> str:
    """生成给 LLM 的精简摘要，避免传入完整数据浪费 token"""
    if isinstance(result, str):
        return result
    if isinstance(result, dict) and "error" in result:
        return f"错误: {result['error']}"

    if tool_name == "search_paper":
        count = result.get("count", 0)
        papers = result.get("papers", [])
        titles = [p.get("title", "?") for p in papers[:5]]
        return f"找到 {count} 篇论文：{', '.join(titles)}"

    if tool_name == "get_paper_by_title":
        return f"论文：{result.get('title', '?')}，作者：{', '.join((result.get('authors') or [])[:3])}，年份：{result.get('year', '?')}"

    if tool_name == "analyze_research_points":
        points = result.get("research_points", result.get("points", []))
        if isinstance(points, list):
            titles = [p.get("title", "?") if isinstance(p, dict) else str(p) for p in points[:5]]
            return f"发现 {len(points)} 个研究点：{', '.join(titles)}"
        return f"研究点分析完成：{str(result)[:200]}"

    if tool_name == "get_concept_graph":
        return f"已获取概念「{result.get('name', '?')}」的图谱数据"

    if tool_name == "analyze_citations":
        return f"论文「{result.get('paper', {}).get('title', '?')}」共有 {result.get('citation_count', 0)} 条引用"

    if tool_name == "recommend_papers":
        papers = result.get("papers", [])
        return f"推荐 {len(papers)} 篇相关论文"

    return str(result)[:500]
```

- [ ] **Step 2: 改造 lead_node 函数的 tool 处理循环**

替换 `lead_node` 函数中的 tool 处理循环，收集 attachments 并使用摘要给 LLM：

```python
def lead_node(state: AgentState) -> Dict[str, Any]:
    """
    Lead Node - 使用 LangChain tools 处理对话
    """
    llm = get_llm_or_raise()

    # 使用 LangChain 原生工具
    tools = legacy_tools.ALL_TOOLS
    llm_with_tools = llm.bind_tools(tools)

    # 构建消息
    context_info = build_context_info(state)
    system_prompt = LEAD_SYSTEM_PROMPT.format(context_info=context_info)

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state.get("messages", []))

    # 获取最后一条用户消息，用于工具选择验证
    last_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, 'content') and not hasattr(msg, 'type') or (hasattr(msg, 'type') and getattr(msg, 'type', '') != 'ai'):
            last_user_msg = msg.content if hasattr(msg, 'content') else str(msg)
            break

    # 调用 LLM
    response = llm_with_tools.invoke(messages)

    # 工具选择纠正逻辑（保持不变）
    if response.tool_calls:
        for i, tc in enumerate(response.tool_calls):
            tool_name = tc["name"]
            if tool_name == "get_concept_graph" and last_user_msg:
                research_keywords = ["研究点", "研究方向", "研究机会", "分析.*研究"]
                import re
                if any(re.search(kw, last_user_msg) for kw in research_keywords):
                    response.tool_calls[i]["name"] = "analyze_research_points"
                    if "concept_name" not in response.tool_calls[i]["args"]:
                        response.tool_calls[i]["args"]["concept_name"] = last_user_msg.replace("研究点", "").replace("研究方向", "").replace("分析", "").strip()

    # 处理 tool calls — 收集附件
    concept_data = None
    attachments = []
    response_content = extract_text_content(response.content)

    max_iterations = 5
    iteration = 0

    while response.tool_calls and iteration < max_iterations:
        iteration += 1

        tool_messages = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            for tool_item in tools:
                if tool_item.name == tool_name:
                    try:
                        result = tool_item.invoke(tool_args)

                        # 收集附件
                        attachment = make_attachment(tool_name, result)
                        if attachment:
                            attachments.append(attachment)

                        # 向后兼容：concept_graph 同时设置 concept_data
                        if tool_name == "get_concept_graph" and isinstance(result, dict) and "id" in result:
                            concept_data = result

                        # 给 LLM 传精简摘要
                        tool_messages.append(ToolMessage(
                            content=summarize_for_llm(tool_name, result),
                            tool_call_id=tool_call["id"]
                        ))
                    except Exception as e:
                        tool_messages.append(ToolMessage(
                            content=f"错误: {str(e)}",
                            tool_call_id=tool_call["id"]
                        ))
                    break

        messages.append(response)
        messages.extend(tool_messages)
        response = llm_with_tools.invoke(messages)
        response_content = extract_text_content(response.content)

    return {
        "response": response_content,
        "agent_used": "lead",
        "needs_summary": False,
        "messages": [AIMessage(content=response_content)],
        "concept_data": concept_data,
        "attachments": attachments,
    }
```

- [ ] **Step 3: 验证 lead node 可正常导入**

Run: `cd mkg && python -c "from agent.nodes.lead import lead_node, make_attachment, summarize_for_llm; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add mkg/agent/nodes/lead.py
git commit -m "feat: add attachment collection logic to lead node"
```

---

## Task 3: 新增 recommend_papers tool 并改造 analyze_research_points

**Files:**
- Modify: `mkg/agent/tools.py:230-474`

- [ ] **Step 1: 新增 recommend_papers tool**

在 `mkg/agent/tools.py` 的 `deep_research` tool 之前（约 line 420 前），添加 `recommend_papers`：

```python
# ============================================================
# 论文推荐 Tools
# ============================================================

@tool
def recommend_papers(concept_name: str, limit: int = 10) -> Dict[str, Any]:
    """推荐与某概念相关的论文。

    当用户说「推荐论文」「相关论文」「找相关工作」「有什么新论文」时调用。

    Args:
        concept_name: 概念名称
        limit: 返回数量限制，默认10

    Returns:
        推荐论文列表，包含标题、作者、摘要等
    """
    if not _db:
        return {"error": "数据库未初始化"}

    # 查找概念（获取英文名用于搜索）
    concept = _db.get_concept_by_text(concept_name)
    if not concept:
        all_concepts = _db.get_all_concepts()
        for c in all_concepts:
            if concept_name.lower() in (c.get('text') or '').lower():
                concept = c
                break

    # 使用英文名搜索（如果有），否则用中文名
    search_query = concept_name
    if concept and concept.get('text_en'):
        search_query = concept['text_en']
    elif concept:
        search_query = concept.get('text', concept_name)

    papers = []
    if _s2_client:
        try:
            results = _s2_client.search_papers(search_query, limit=limit)
            if isinstance(results, list):
                papers = results
            elif isinstance(results, dict):
                papers = results.get('data', results.get('papers', []))
        except Exception as e:
            return {"error": f"搜索失败: {str(e)}"}
    else:
        return {"error": "Semantic Scholar 客户端未初始化，无法推荐论文"}

    return {
        "concept_name": concept.get('text', concept_name) if concept else concept_name,
        "papers": [
            {
                "title": p.get("title", ""),
                "authors": [a.get("name", a) if isinstance(a, dict) else str(a) for a in (p.get("authors") or [])[:5]],
                "year": p.get("year"),
                "abstract": p.get("abstract", ""),
                "citation_count": p.get("citationCount") or p.get("citation_count", 0),
                "venue": p.get("venue", ""),
                "paper_id": p.get("paperId") or p.get("paper_id", ""),
                "open_access_url": (p.get("openAccessPdf") or {}).get("url") if isinstance(p.get("openAccessPdf"), dict) else None,
                "tldr": p.get("tldr", {}).get("text") if isinstance(p.get("tldr"), dict) else p.get("tldr"),
            }
            for p in papers[:limit]
        ],
        "count": len(papers),
    }
```

- [ ] **Step 2: 改造 analyze_research_points 返回 LLM 生成的研究点**

替换现有的 `analyze_research_points` tool，使其调用与概念页面相同的后端逻辑（`/api/concepts/{id}/research-points`），返回完整的研究点数据：

```python
@tool
def analyze_research_points(concept_name: str) -> Dict[str, Any]:
    """分析概念的研究点和研究方向。

    【重要】当用户提到「研究点」「研究方向」「研究机会」「分析...的研究点」时调用此工具！

    这个工具用于分析某个概念的研究现状和潜在研究方向。
    会调用 LLM 深入分析图谱结构，生成研究点建议。

    不要与 get_concept_graph 混淆：
    - 用户说「研究点」→ 用这个工具 analyze_research_points
    - 用户说「查看图谱」→ 用 get_concept_graph

    Args:
        concept_name: 概念名称

    Returns:
        研究点分析结果，包含 LLM 生成的研究点列表
    """
    if not _db:
        return {"error": "数据库未初始化"}

    concept = _db.get_concept_by_text(concept_name)
    if not concept:
        all_concepts = _db.get_all_concepts()
        for c in all_concepts:
            if concept_name.lower() in (c.get('text') or '').lower():
                concept = c
                break

    if not concept:
        return {"error": f"未找到概念「{concept_name}」"}

    concept_id = concept['id']

    # 调用与概念页面相同的研究点分析 API
    try:
        import requests
        res = requests.get(f"http://localhost:8000/api/concepts/{concept_id}/research-points", timeout=120)
        if res.status_code == 200:
            data = res.json()
            return {
                "concept_name": data.get("concept_name", concept.get("text", concept_name)),
                "research_points": data.get("research_points", []),
                "analysis_context": data.get("analysis_context", {}),
            }
        else:
            return {"error": f"研究点分析失败: HTTP {res.status_code}"}
    except Exception as e:
        # Fallback：返回基础概念数据
        papers = _db.get_papers_by_concept(concept_id) or []
        children = _db.get_concept_children(concept_id) or []
        parents = _db.get_concept_parents(concept_id) or []

        return {
            "concept_name": concept.get('text', concept_name),
            "research_points": [],
            "analysis_context": {
                "concept": {"id": concept_id, "name": concept.get("text"), "category": concept.get("category")},
                "ancestors": [{"id": p["id"], "name": p.get("text")} for p in parents],
                "descendants": [{"id": c["id"], "name": c.get("text")} for c in children],
                "edge_nodes": [],
                "related_papers": [{"title": p.get("title")} for p in papers[:5]],
            },
            "local_papers": papers,
            "children_concepts": [c.get('text') for c in children],
            "parent_concepts": [p.get('text') for p in parents],
        }
```

- [ ] **Step 3: 将 recommend_papers 加入 ALL_TOOLS**

更新 `ALL_TOOLS` 列表：

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
    # 论文推荐
    recommend_papers,
    # 深入研究
    deep_research,
    # 文件夹管理
    list_folders,
    move_paper_to_folder,
    create_folder,
]
```

- [ ] **Step 4: 更新 lead node 系统提示词增加推荐论文**

在 `mkg/agent/nodes/lead.py` 的 `LEAD_SYSTEM_PROMPT` 中增加推荐论文的规则：

```python
LEAD_SYSTEM_PROMPT = """你是 Meta Knowledge Graph 的研究助手。

【工具选择规则 - 非常重要】

用户说「有哪些论文」「搜索论文」→ 用 search_paper
用户说「研究点」「研究方向」「分析...的研究点」→ 用 analyze_research_points
用户说「查看图谱」「显示图谱」→ 用 get_concept_graph
用户说「引用」「被引用」→ 用 analyze_citations
用户说「论文内容」「这篇论文讲什么」→ 用 read_paper_content
用户说「推荐论文」「相关论文」「找相关工作」→ 用 recommend_papers

【特别注意】
- 「查看...的研究点」要用 analyze_research_points，不要用 get_concept_graph！
- 只有用户明确说「图谱」两个字时才用 get_concept_graph
- 「推荐论文」「相关工作」要用 recommend_papers，不要用 search_paper

当前上下文：
{context_info}

请根据用户问题选择合适的工具。回复时先给出文字分析和总结，工具返回的结构化数据会自动以卡片形式展示给用户。"""
```

- [ ] **Step 5: 验证工具导入**

Run: `cd mkg && python -c "from agent.tools import ALL_TOOLS; print(f'{len(ALL_TOOLS)} tools: {[t.name for t in ALL_TOOLS]}')"`
Expected: 输出 `11 tools: [...]` 包含 `recommend_papers`

- [ ] **Step 6: Commit**

```bash
git add mkg/agent/tools.py mkg/agent/nodes/lead.py
git commit -m "feat: add recommend_papers tool, enhance analyze_research_points with LLM analysis"
```

---

## Task 4: 前端数据层 — Store 和 API 类型更新

**Files:**
- Modify: `frontend/src/stores/agentStore.ts:20-38`
- Modify: `frontend/src/lib/api.ts:469-485`

- [ ] **Step 1: 在 agentStore 中定义 ChatAttachment 类型并更新 Message**

在 `frontend/src/stores/agentStore.ts` 中，在 `ConceptNode` 接口后面增加 `ChatAttachment` 类型，并更新 `Message` 接口：

```typescript
// 概念图谱节点数据
export interface ConceptNode {
  id: string
  name: string
  category?: string
  paper_count: number
  children?: ConceptNode[]
  parents?: ConceptNode[]
}

// 统一附件类型
export interface ChatAttachment {
  type: 'research_points' | 'paper_detail' | 'paper_list' | 'concept_graph' | 'recommendation' | 'citation_analysis'
  data: any
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: 'lead' | 'citation' | 'research' | 'deep_research' | 'merge' | 'paper_qa'
  researchSessionId?: string
  conceptData?: ConceptNode  // deprecated，向后兼容
  attachments?: ChatAttachment[]  // 新增：结构化附件
  timestamp: number
}
```

- [ ] **Step 2: 更新前端 api.ts 的 AgentChatResponse 类型**

在 `frontend/src/lib/api.ts` 中更新 `AgentChatResponse` 接口：

```typescript
interface AgentChatResponse {
  message: string
  agent: string
  contextUpdate?: Partial<AgentContextSummary>
  researchSessionId?: string
  conceptData?: ConceptGraphData  // deprecated
  attachments?: Array<{ type: string; data: any }>  // 新增
}
```

- [ ] **Step 3: 更新 Chat.tsx 中 addMessage 调用传递 attachments**

在 `frontend/src/pages/Chat.tsx` 的 `handleSend` 函数中，将 response.attachments 传递给 addMessage：

找到 Chat.tsx 中的 `addMessage` 调用（约 line 84-89）：

```typescript
      addMessage({
        role: 'assistant',
        content: response.message,
        agent: response.agent as any,
        conceptData: response.conceptData,  // 保留向后兼容
        attachments: response.attachments,  // 新增
      })
```

- [ ] **Step 4: 验证前端编译通过**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 无类型错误（或仅有既有的错误，无新增错误）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/agentStore.ts frontend/src/lib/api.ts frontend/src/pages/Chat.tsx
git commit -m "feat: add ChatAttachment type to store and API layer"
```

---

## Task 5: ChatAttachments 分发组件

**Files:**
- Create: `frontend/src/components/ChatAttachments.tsx`

- [ ] **Step 1: 创建 ChatAttachments 分发组件**

```typescript
// frontend/src/components/ChatAttachments.tsx
import { lazy, Suspense } from 'react'
import ConceptGraphInChat from './ConceptGraphInChat'

// Lazy load 卡片组件
const ResearchPointsCard = lazy(() => import('./cards/ResearchPointsCard'))
const PaperDetailCard = lazy(() => import('./cards/PaperDetailCard'))
const PaperListCard = lazy(() => import('./cards/PaperListCard'))
const RecommendationCard = lazy(() => import('./cards/RecommendationCard'))
const CitationAnalysisCard = lazy(() => import('./cards/CitationAnalysisCard'))

interface ChatAttachment {
  type: string
  data: any
}

interface Props {
  attachments: ChatAttachment[]
  onSendMessage: (text: string) => void
}

function CardFallback() {
  return (
    <div
      className="my-2 p-4 rounded-xl animate-pulse"
      style={{ background: 'rgba(184, 134, 11, 0.04)', height: 80 }}
    />
  )
}

export default function ChatAttachments({ attachments, onSendMessage }: Props) {
  if (!attachments || attachments.length === 0) return null

  return (
    <div className="chat-attachments space-y-3 mt-2">
      {attachments.map((att, i) => (
        <Suspense key={`${att.type}-${i}`} fallback={<CardFallback />}>
          {att.type === 'research_points' && (
            <ResearchPointsCard data={att.data} onAction={onSendMessage} />
          )}
          {att.type === 'paper_detail' && (
            <PaperDetailCard data={att.data} />
          )}
          {att.type === 'paper_list' && (
            <PaperListCard data={att.data} onAction={onSendMessage} />
          )}
          {att.type === 'concept_graph' && (
            <ConceptGraphInChat data={att.data} />
          )}
          {att.type === 'recommendation' && (
            <RecommendationCard data={att.data} onAction={onSendMessage} />
          )}
          {att.type === 'citation_analysis' && (
            <CitationAnalysisCard data={att.data} />
          )}
        </Suspense>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ChatAttachments.tsx
git commit -m "feat: create ChatAttachments dispatch component"
```

---

## Task 6: ResearchPointsCard 卡片组件

**Files:**
- Create: `frontend/src/components/cards/ResearchPointsCard.tsx`

- [ ] **Step 1: 创建 ResearchPointsCard**

```typescript
// frontend/src/components/cards/ResearchPointsCard.tsx
import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

interface ResearchPoint {
  title: string
  hypothesis?: string
  description: string
  discovery_method?: string
  rationale?: string
  related_concepts?: string[]
  difficulty?: string
  novelty?: string
  potential_impact?: string
}

interface Props {
  data: {
    concept_name: string
    research_points: ResearchPoint[]
    analysis_context?: any
  }
  onAction: (text: string) => void
}

const DIFFICULTY_COLORS: Record<string, string> = {
  low: '#2d5a27',
  medium: '#b8860b',
  high: '#a33b3b',
}

const NOVELTY_COLORS: Record<string, string> = {
  incremental: '#a89a8a',
  moderate: '#4a6b8a',
  high: '#c2410c',
}

const IMPACT_COLORS: Record<string, string> = {
  niche: '#a89a8a',
  broad: '#4a6b8a',
  transformative: '#d4a012',
}

const METHOD_LABELS: Record<string, string> = {
  gap_filling: '🔍 空白地带法',
  leaf_extension: '🌱 末端延伸法',
  bottleneck: '🔥 瓶颈识别法',
  transfer: '🔄 迁移应用法',
}

export default function ResearchPointsCard({ data, onAction }: Props) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)
  const points = data.research_points || []
  const context = data.analysis_context

  if (points.length === 0) return null

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, rgba(250, 248, 245, 0.98) 0%, rgba(245, 240, 232, 0.98) 100%)',
        border: '1px solid rgba(184, 134, 11, 0.12)',
        boxShadow: '0 4px 16px rgba(44, 24, 16, 0.06)',
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{
          borderBottom: '1px solid rgba(184, 134, 11, 0.08)',
          background: 'linear-gradient(180deg, rgba(184, 134, 11, 0.04) 0%, transparent 100%)',
        }}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">🔍</span>
          <span className="font-display text-sm font-medium" style={{ color: 'var(--color-sepia)' }}>
            研究点发现
          </span>
          <span className="font-mono text-xs px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(184, 134, 11, 0.08)', color: 'var(--color-sepia)' }}>
            {points.length}
          </span>
        </div>
        <span className="font-body text-xs" style={{ color: 'var(--color-muted)' }}>
          {data.concept_name}
        </span>
      </div>

      {/* Context stats */}
      {context && (
        <div
          className="px-4 py-2 flex items-center gap-4 text-xs"
          style={{ borderBottom: '1px solid rgba(184, 134, 11, 0.06)' }}
        >
          {context.ancestors && (
            <span style={{ color: 'var(--color-muted)' }}>⬆️ {context.ancestors.length} 祖先</span>
          )}
          {context.descendants && (
            <span style={{ color: 'var(--color-muted)' }}>⬇️ {context.descendants.length} 后代</span>
          )}
          {context.edge_nodes && (
            <span style={{ color: 'var(--color-muted)' }}>🍃 {context.edge_nodes.length} 边缘</span>
          )}
        </div>
      )}

      {/* Research points list */}
      <div className="p-3 space-y-2">
        {points.map((point, i) => {
          const isExpanded = expandedIndex === i
          return (
            <div
              key={i}
              className="rounded-lg overflow-hidden transition-all"
              style={{
                border: '1px solid rgba(184, 134, 11, 0.08)',
                background: isExpanded ? 'rgba(184, 134, 11, 0.02)' : 'transparent',
              }}
            >
              {/* Point header — clickable */}
              <button
                onClick={() => setExpandedIndex(isExpanded ? null : i)}
                className="w-full px-3 py-2.5 flex items-start gap-2.5 text-left"
              >
                <span
                  className="w-5 h-5 rounded-md flex items-center justify-center text-xs font-mono flex-shrink-0 mt-0.5"
                  style={{
                    background: 'linear-gradient(135deg, var(--color-sepia) 0%, var(--color-copper) 100%)',
                    color: 'var(--color-vellum)',
                  }}
                >
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="font-display text-sm leading-snug" style={{ color: 'var(--color-sepia)', fontWeight: 500 }}>
                    {point.title}
                  </div>
                  {point.hypothesis && !isExpanded && (
                    <div className="font-body text-xs mt-0.5 truncate italic" style={{ color: '#4a6b8a' }}>
                      {point.hypothesis}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0 mt-1">
                  {/* Difficulty / Novelty / Impact dots */}
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: DIFFICULTY_COLORS[point.difficulty || 'medium'] }} title={`难度: ${point.difficulty}`} />
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: NOVELTY_COLORS[point.novelty || 'moderate'] }} title={`创新性: ${point.novelty}`} />
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: IMPACT_COLORS[point.potential_impact || 'niche'] }} title={`影响力: ${point.potential_impact}`} />
                  {isExpanded ? <ChevronDown className="w-3.5 h-3.5 ml-1" style={{ color: 'var(--color-muted)' }} /> : <ChevronRight className="w-3.5 h-3.5 ml-1" style={{ color: 'var(--color-muted)' }} />}
                </div>
              </button>

              {/* Expanded content */}
              {isExpanded && (
                <div className="px-3 pb-3 pl-10 space-y-2">
                  {point.hypothesis && (
                    <p className="font-body text-xs italic" style={{ color: '#4a6b8a' }}>
                      {point.hypothesis}
                    </p>
                  )}
                  <p className="font-body text-sm leading-relaxed" style={{ color: 'var(--color-ink)' }}>
                    {point.description}
                  </p>

                  {/* Method & Rationale */}
                  {(point.discovery_method || point.rationale) && (
                    <div className="px-3 py-2 rounded-lg text-xs" style={{ background: 'rgba(184, 134, 11, 0.04)' }}>
                      {point.discovery_method && (
                        <span style={{ color: 'var(--color-muted)' }}>
                          {METHOD_LABELS[point.discovery_method] || point.discovery_method}
                        </span>
                      )}
                      {point.discovery_method && point.rationale && (
                        <span className="mx-2" style={{ color: 'rgba(184, 134, 11, 0.2)' }}>·</span>
                      )}
                      {point.rationale && (
                        <span style={{ color: 'var(--color-sepia)' }}>{point.rationale}</span>
                      )}
                    </div>
                  )}

                  {/* Related concepts */}
                  {point.related_concepts && point.related_concepts.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {point.related_concepts.slice(0, 4).map((c, j) => (
                        <span
                          key={j}
                          className="px-2 py-0.5 rounded-full text-xs font-mono"
                          style={{ backgroundColor: 'rgba(184, 134, 11, 0.06)', color: 'var(--color-sepia)' }}
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Action button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onAction(`深入研究「${data.concept_name}」的「${point.title}」`)
                    }}
                    className="mt-1 px-3 py-1.5 rounded-lg text-xs font-body transition-all"
                    style={{
                      background: 'linear-gradient(135deg, var(--color-sepia) 0%, var(--color-copper) 100%)',
                      color: 'var(--color-vellum)',
                    }}
                  >
                    深入研究此方向
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
mkdir -p frontend/src/components/cards
git add frontend/src/components/cards/ResearchPointsCard.tsx
git commit -m "feat: create ResearchPointsCard component"
```

---

## Task 7: PaperDetailCard 卡片组件

**Files:**
- Create: `frontend/src/components/cards/PaperDetailCard.tsx`

- [ ] **Step 1: 创建 PaperDetailCard**

```typescript
// frontend/src/components/cards/PaperDetailCard.tsx
import { useState } from 'react'
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'

interface Props {
  data: {
    title: string
    authors?: string[]
    year?: number
    venue?: string
    abstract?: string | null
    tldr?: string | null
    keywords?: string[]
    contributions?: string[]
    citation_count?: number
    doi?: string
    s2_doi?: string
  }
}

export default function PaperDetailCard({ data }: Props) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, rgba(250, 248, 245, 0.98) 0%, rgba(245, 240, 232, 0.98) 100%)',
        border: '1px solid rgba(184, 134, 11, 0.12)',
        boxShadow: '0 4px 16px rgba(44, 24, 16, 0.06)',
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3"
        style={{
          borderBottom: '1px solid rgba(184, 134, 11, 0.08)',
          background: 'linear-gradient(180deg, rgba(184, 134, 11, 0.04) 0%, transparent 100%)',
        }}
      >
        <h4 className="font-display text-sm leading-snug" style={{ color: 'var(--color-sepia)', fontWeight: 500 }}>
          {data.title}
        </h4>
        <div className="flex items-center gap-3 mt-2 flex-wrap">
          {data.year && (
            <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-muted)' }}>
              📅 {data.year}
            </span>
          )}
          {data.citation_count !== undefined && (
            <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-muted)' }}>
              📊 {data.citation_count} 引用
            </span>
          )}
          {data.venue && (
            <span className="flex items-center gap-1 text-xs truncate max-w-[160px]" style={{ color: 'var(--color-muted)' }}>
              📖 {data.venue}
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* TL;DR */}
        {data.tldr && (
          <div
            className="p-3 rounded-lg"
            style={{
              background: 'linear-gradient(135deg, rgba(45, 90, 39, 0.06) 0%, rgba(45, 90, 39, 0.02) 100%)',
              border: '1px solid rgba(45, 90, 39, 0.1)',
            }}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-xs">💡</span>
              <span className="font-mono text-[10px] uppercase tracking-wider" style={{ color: '#2d5a27' }}>TL;DR</span>
            </div>
            <p className="font-body text-sm leading-relaxed" style={{ color: '#2d5a27' }}>
              {data.tldr}
            </p>
          </div>
        )}

        {/* Authors */}
        {data.authors && data.authors.length > 0 && (
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider mb-1" style={{ color: 'var(--color-muted)' }}>作者</div>
            <div className="font-body text-sm" style={{ color: 'var(--color-sepia)' }}>
              {data.authors.slice(0, 4).join(', ')}
              {data.authors.length > 4 && <span style={{ color: 'var(--color-muted)' }}> +{data.authors.length - 4} 位</span>}
            </div>
          </div>
        )}

        {/* Keywords */}
        {data.keywords && data.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {data.keywords.slice(0, 8).map((kw, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded-full text-xs font-mono"
                style={{ backgroundColor: 'rgba(184, 134, 11, 0.06)', color: 'var(--color-sepia)', border: '1px solid rgba(184, 134, 11, 0.1)' }}
              >
                {kw}
              </span>
            ))}
          </div>
        )}

        {/* Expandable section */}
        {(data.abstract || (data.contributions && data.contributions.length > 0)) && (
          <>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs font-body transition-colors"
              style={{ color: 'var(--color-sepia)' }}
            >
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              {expanded ? '收起' : '展开详情'}
            </button>

            {expanded && (
              <div className="space-y-3">
                {data.abstract && (
                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-wider mb-1" style={{ color: 'var(--color-muted)' }}>摘要</div>
                    <p className="font-body text-sm leading-relaxed" style={{ color: 'var(--color-ink)' }}>{data.abstract}</p>
                  </div>
                )}
                {data.contributions && data.contributions.length > 0 && (
                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--color-muted)' }}>核心贡献</div>
                    <div className="space-y-1.5">
                      {data.contributions.slice(0, 3).map((c, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <span
                            className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-mono flex-shrink-0 mt-0.5"
                            style={{ background: 'linear-gradient(135deg, var(--color-sepia) 0%, var(--color-copper) 100%)', color: 'var(--color-vellum)' }}
                          >
                            {i + 1}
                          </span>
                          <span className="font-body text-sm" style={{ color: 'var(--color-ink)' }}>{c}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* DOI */}
        {(data.doi || data.s2_doi) && (
          <div className="pt-2" style={{ borderTop: '1px solid rgba(184, 134, 11, 0.06)' }}>
            {data.s2_doi ? (
              <a
                href={`https://doi.org/${data.s2_doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 font-mono text-xs transition-colors"
                style={{ color: '#4a6b8a' }}
              >
                {data.s2_doi} <ExternalLink className="w-3 h-3" />
              </a>
            ) : (
              <span className="font-mono text-xs" style={{ color: 'var(--color-muted)' }}>{data.doi}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/cards/PaperDetailCard.tsx
git commit -m "feat: create PaperDetailCard component"
```

---

## Task 8: PaperListCard 卡片组件

**Files:**
- Create: `frontend/src/components/cards/PaperListCard.tsx`

- [ ] **Step 1: 创建 PaperListCard**

```typescript
// frontend/src/components/cards/PaperListCard.tsx

interface PaperItem {
  title: string
  authors?: string[]
  year?: number
  citation_count?: number
  doi?: string
}

interface Props {
  data: {
    query?: string
    papers: PaperItem[]
    count: number
  }
  onAction: (text: string) => void
}

export default function PaperListCard({ data, onAction }: Props) {
  const papers = data.papers || []
  if (papers.length === 0) return null

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, rgba(250, 248, 245, 0.98) 0%, rgba(245, 240, 232, 0.98) 100%)',
        border: '1px solid rgba(184, 134, 11, 0.12)',
        boxShadow: '0 4px 16px rgba(44, 24, 16, 0.06)',
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{
          borderBottom: '1px solid rgba(184, 134, 11, 0.08)',
          background: 'linear-gradient(180deg, rgba(184, 134, 11, 0.04) 0%, transparent 100%)',
        }}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">📄</span>
          <span className="font-display text-sm font-medium" style={{ color: 'var(--color-sepia)' }}>
            {data.query ? `搜索结果：${data.query}` : '论文列表'}
          </span>
        </div>
        <span className="font-mono text-xs px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(184, 134, 11, 0.08)', color: 'var(--color-sepia)' }}>
          {data.count}
        </span>
      </div>

      {/* Paper list */}
      <div className="divide-y" style={{ borderColor: 'rgba(184, 134, 11, 0.06)' }}>
        {papers.map((paper, i) => (
          <button
            key={i}
            onClick={() => onAction(`详细介绍《${paper.title}》`)}
            className="w-full px-4 py-3 text-left transition-colors hover:bg-paper/50"
          >
            <div className="font-body text-sm leading-snug" style={{ color: 'var(--color-sepia)', fontWeight: 500 }}>
              {paper.title}
            </div>
            <div className="flex items-center gap-3 mt-1.5 text-xs" style={{ color: 'var(--color-muted)' }}>
              {paper.authors && paper.authors.length > 0 && (
                <span className="truncate max-w-[200px]">
                  {paper.authors.slice(0, 2).join(', ')}
                  {paper.authors.length > 2 && ' et al.'}
                </span>
              )}
              {paper.year && <span>{paper.year}</span>}
              {paper.citation_count !== undefined && paper.citation_count > 0 && (
                <span>📊 {paper.citation_count}</span>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/cards/PaperListCard.tsx
git commit -m "feat: create PaperListCard component"
```

---

## Task 9: RecommendationCard 卡片组件

**Files:**
- Create: `frontend/src/components/cards/RecommendationCard.tsx`

- [ ] **Step 1: 创建 RecommendationCard**

```typescript
// frontend/src/components/cards/RecommendationCard.tsx
import { useState } from 'react'
import { Plus, Check, Loader2 } from 'lucide-react'
import { s2PaperApi } from '../lib/api'

interface RecommendedPaper {
  title: string
  authors?: string[]
  year?: number
  abstract?: string
  citation_count?: number
  venue?: string
  paper_id?: string
  open_access_url?: string | null
  tldr?: string | null
}

interface Props {
  data: {
    concept_name: string
    papers: RecommendedPaper[]
    count?: number
  }
  onAction: (text: string) => void
}

export default function RecommendationCard({ data, onAction }: Props) {
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set())
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const papers = data.papers || []

  if (papers.length === 0) return null

  const handleAdd = async (paper: RecommendedPaper) => {
    if (!paper.paper_id || addedIds.has(paper.paper_id)) return
    setLoadingId(paper.paper_id)
    try {
      await s2PaperApi.addMetadata({
        s2_paper_id: paper.paper_id,
        title: paper.title,
        year: paper.year,
        abstract: paper.abstract,
        authors: paper.authors?.map(a => ({ name: a })),
        venue: paper.venue,
        citation_count: paper.citation_count,
        tldr: paper.tldr ? { text: paper.tldr } : undefined,
        open_access_pdf_url: paper.open_access_url || undefined,
      })
      setAddedIds(prev => new Set(prev).add(paper.paper_id!))
    } catch (e) {
      console.error('Failed to add paper:', e)
    } finally {
      setLoadingId(null)
    }
  }

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, rgba(250, 248, 245, 0.98) 0%, rgba(245, 240, 232, 0.98) 100%)',
        border: '1px solid rgba(184, 134, 11, 0.12)',
        boxShadow: '0 4px 16px rgba(44, 24, 16, 0.06)',
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{
          borderBottom: '1px solid rgba(184, 134, 11, 0.08)',
          background: 'linear-gradient(180deg, rgba(184, 134, 11, 0.04) 0%, transparent 100%)',
        }}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">📚</span>
          <span className="font-display text-sm font-medium" style={{ color: 'var(--color-sepia)' }}>
            推荐论文
          </span>
        </div>
        <span className="font-body text-xs" style={{ color: 'var(--color-muted)' }}>
          基于「{data.concept_name}」
        </span>
      </div>

      {/* Paper list */}
      <div className="divide-y" style={{ borderColor: 'rgba(184, 134, 11, 0.06)' }}>
        {papers.map((paper, i) => {
          const isAdded = paper.paper_id ? addedIds.has(paper.paper_id) : false
          const isLoading = paper.paper_id === loadingId

          return (
            <div key={i} className="px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <button
                  onClick={() => onAction(`详细介绍《${paper.title}》`)}
                  className="text-left flex-1 min-w-0"
                >
                  <div className="font-body text-sm leading-snug" style={{ color: 'var(--color-sepia)', fontWeight: 500 }}>
                    {paper.title}
                  </div>
                </button>

                {/* Add to library button */}
                {paper.paper_id && (
                  <button
                    onClick={() => handleAdd(paper)}
                    disabled={isAdded || isLoading}
                    className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all"
                    style={{
                      background: isAdded ? 'rgba(45, 90, 39, 0.1)' : 'rgba(184, 134, 11, 0.08)',
                      color: isAdded ? '#2d5a27' : 'var(--color-sepia)',
                      cursor: isAdded ? 'default' : 'pointer',
                    }}
                    title={isAdded ? '已添加' : '添加到知识库'}
                  >
                    {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> :
                     isAdded ? <Check className="w-3.5 h-3.5" /> :
                     <Plus className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>

              <div className="flex items-center gap-3 mt-1.5 text-xs" style={{ color: 'var(--color-muted)' }}>
                {paper.authors && paper.authors.length > 0 && (
                  <span className="truncate max-w-[180px]">
                    {paper.authors.slice(0, 2).join(', ')}
                    {paper.authors.length > 2 && ' et al.'}
                  </span>
                )}
                {paper.year && <span>{paper.year}</span>}
                {paper.citation_count !== undefined && paper.citation_count > 0 && (
                  <span>📊 {paper.citation_count}</span>
                )}
                {paper.venue && <span className="truncate max-w-[100px]">{paper.venue}</span>}
              </div>

              {paper.tldr && (
                <p className="font-body text-xs mt-1.5 leading-relaxed" style={{ color: 'var(--color-ink)' }}>
                  {paper.tldr}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/cards/RecommendationCard.tsx
git commit -m "feat: create RecommendationCard component"
```

---

## Task 10: CitationAnalysisCard 卡片组件

**Files:**
- Create: `frontend/src/components/cards/CitationAnalysisCard.tsx`

- [ ] **Step 1: 创建 CitationAnalysisCard**

```typescript
// frontend/src/components/cards/CitationAnalysisCard.tsx

interface CitationItem {
  title?: string
  year?: number
  citation_count?: number
  is_internal?: boolean
  paper_id?: string
}

interface Props {
  data: {
    paper?: {
      title: string
      doi?: string
      citation_count?: number
    }
    paper_title?: string
    citations: CitationItem[]
    citation_count: number
  }
}

export default function CitationAnalysisCard({ data }: Props) {
  const citations = data.citations || []
  const paperTitle = data.paper?.title || data.paper_title || '未知论文'
  const totalCount = data.citation_count || data.paper?.citation_count || citations.length

  if (citations.length === 0 && totalCount === 0) return null

  const internalCitations = citations.filter(c => c.is_internal)
  const externalCitations = citations.filter(c => !c.is_internal)

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, rgba(250, 248, 245, 0.98) 0%, rgba(245, 240, 232, 0.98) 100%)',
        border: '1px solid rgba(184, 134, 11, 0.12)',
        boxShadow: '0 4px 16px rgba(44, 24, 16, 0.06)',
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3"
        style={{
          borderBottom: '1px solid rgba(184, 134, 11, 0.08)',
          background: 'linear-gradient(180deg, rgba(184, 134, 11, 0.04) 0%, transparent 100%)',
        }}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">🔗</span>
          <span className="font-display text-sm font-medium" style={{ color: 'var(--color-sepia)' }}>
            引用分析
          </span>
          <span className="font-mono text-xs px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(184, 134, 11, 0.08)', color: 'var(--color-sepia)' }}>
            {totalCount}
          </span>
        </div>
        <p className="font-body text-xs mt-1 truncate" style={{ color: 'var(--color-muted)' }}>
          {paperTitle}
        </p>
      </div>

      {/* Citation groups */}
      <div className="p-3 space-y-3">
        {/* Internal (in library) */}
        {internalCitations.length > 0 && (
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: '#2d5a27' }}>
              <span className="w-2 h-2 rounded-full" style={{ background: '#2d5a27' }} />
              库内论文 ({internalCitations.length})
            </div>
            <div className="space-y-1.5">
              {internalCitations.map((c, i) => (
                <div key={i} className="px-3 py-2 rounded-lg" style={{ background: 'rgba(45, 90, 39, 0.04)' }}>
                  <div className="font-body text-sm" style={{ color: 'var(--color-sepia)' }}>{c.title || '未知标题'}</div>
                  <div className="flex gap-3 mt-1 text-xs" style={{ color: 'var(--color-muted)' }}>
                    {c.year && <span>{c.year}</span>}
                    {c.citation_count !== undefined && <span>📊 {c.citation_count}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* External */}
        {externalCitations.length > 0 && (
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: 'var(--color-muted)' }}>
              <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-muted)' }} />
              外部论文 ({externalCitations.length})
            </div>
            <div className="space-y-1.5">
              {externalCitations.slice(0, 10).map((c, i) => (
                <div key={i} className="px-3 py-2 rounded-lg" style={{ background: 'rgba(184, 134, 11, 0.02)' }}>
                  <div className="font-body text-sm" style={{ color: 'var(--color-ink)' }}>{c.title || '未知标题'}</div>
                  <div className="flex gap-3 mt-1 text-xs" style={{ color: 'var(--color-muted)' }}>
                    {c.year && <span>{c.year}</span>}
                    {c.citation_count !== undefined && <span>📊 {c.citation_count}</span>}
                  </div>
                </div>
              ))}
              {externalCitations.length > 10 && (
                <p className="text-xs text-center py-1" style={{ color: 'var(--color-muted)' }}>
                  还有 {externalCitations.length - 10} 条引用未显示
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/cards/CitationAnalysisCard.tsx
git commit -m "feat: create CitationAnalysisCard component"
```

---

## Task 11: 接入 Chat.tsx 渲染附件

**Files:**
- Modify: `frontend/src/pages/Chat.tsx:1-459`

- [ ] **Step 1: 导入 ChatAttachments 并添加 sendMessage 处理**

在 `Chat.tsx` 顶部添加导入：

```typescript
import ChatAttachments from '../components/ChatAttachments'
```

- [ ] **Step 2: 在 Chat 组件内添加 programmatic send 函数**

在 `Chat.tsx` 的 `handleSend` 函数之后添加一个供卡片调用的发送函数：

```typescript
  // Handle programmatic send from card actions
  const handleCardAction = useCallback((text: string) => {
    setInput(text)
    // Use setTimeout to let state update, then trigger send
    setTimeout(() => {
      const textarea = inputRef.current
      if (textarea) {
        textarea.focus()
      }
    }, 100)
  }, [])
```

- [ ] **Step 3: 在消息渲染中接入 ChatAttachments**

在 `Chat.tsx` 的消息渲染部分，在现有的 `ConceptGraphInChat` 渲染之后（约 line 322-327），替换为统一附件渲染逻辑：

找到这段代码：
```tsx
                  {/* 概念图谱 - 放在消息气泡外面以避免 CSS 干扰 */}
                  {msg.role === 'assistant' && msg.conceptData && (
                    <ConceptGraphInChat
                      data={msg.conceptData}
                    />
                  )}
```

替换为：
```tsx
                  {/* 附件卡片 — 统一渲染 */}
                  {msg.role === 'assistant' && msg.attachments && msg.attachments.length > 0 && (
                    <ChatAttachments
                      attachments={msg.attachments}
                      onSendMessage={handleCardAction}
                    />
                  )}
                  {/* 向后兼容：旧消息的 conceptData */}
                  {msg.role === 'assistant' && msg.conceptData && (!msg.attachments || msg.attachments.length === 0) && (
                    <ConceptGraphInChat
                      data={msg.conceptData}
                    />
                  )}
```

- [ ] **Step 4: 验证前端编译通过**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: 无新增类型错误

- [ ] **Step 5: 启动前端验证页面渲染正常**

Run: `cd frontend && npm run dev`

手动验证：
1. 打开 Chat 页面，发送 "搜索论文 多智能体" — 应看到文字回复 + PaperListCard
2. 发送 "显示图谱" — 应看到 ConceptGraphInChat
3. 发送 "分析多智能体系统的研究点" — 应看到 ResearchPointsCard
4. 点击 PaperListCard 中的论文 — 应自动填充输入框

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Chat.tsx
git commit -m "feat: integrate ChatAttachments into Chat page with backward compat"
```

---

## Task 12: 最终集成验证

**Files:** 无新文件，全栈验证

- [ ] **Step 1: 启动后端**

Run: `python -m uvicorn backend.main:app --reload --port 8000`

- [ ] **Step 2: 启动前端**

Run: `cd frontend && npm run dev`

- [ ] **Step 3: 端到端验证**

在 Chat 页面测试以下对话：

1. **搜索论文**: 输入 "搜索多智能体论文" → 应返回文字 + PaperListCard
2. **论文详情**: 点击列表中一篇论文 → 应返回文字 + PaperDetailCard
3. **研究点**: 输入 "分析多智能体系统的研究点" → 应返回文字 + ResearchPointsCard（含可展开的研究点）
4. **推荐论文**: 输入 "推荐关于多智能体的论文" → 应返回文字 + RecommendationCard（含添加按钮）
5. **引用分析**: 输入 "分析 AgentScope 的引用" → 应返回文字 + CitationAnalysisCard
6. **概念图谱**: 输入 "显示概念图谱" → 应返回文字 + ConceptGraphInChat
7. **卡片交互**: 在 ResearchPointsCard 中点击 "深入研究此方向" → 应填入输入框

- [ ] **Step 4: 验证向后兼容**

确认已有的消息中 `conceptData` 仍能正确渲染。

- [ ] **Step 5: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete chat attachment system — agent-driven concept page parity"
```
