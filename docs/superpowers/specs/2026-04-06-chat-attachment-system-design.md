# Chat 附件系统设计 — 让 Agent 完全覆盖概念页面功能

**日期**: 2026-04-06
**目标**: 通过统一附件系统，让 Chat 页面的 LLM Agent 以对话驱动方式覆盖概念页面的所有功能，返回结果以"文字分析 + 结构化可交互卡片"混合呈现。

---

## 1. 核心思路

- **对话驱动**：用户在 Chat 中用自然语言触发操作（"分析研究点"、"推荐论文"等），Agent 调用 tool 获取数据
- **混合呈现**：Agent 返回文字总结 + 结构化附件数据，前端把附件渲染为可交互卡片
- **卡片内操作回流对话**：卡片上的操作按钮发送消息给 Agent，保持对话一致性

## 2. 附件类型系统

### 2.1 统一接口

```typescript
interface ChatAttachment {
  type: 'research_points' | 'paper_detail' | 'paper_list' | 'concept_graph' | 'recommendation' | 'citation_analysis'
  data: any
}
```

### 2.2 各类型 schema

| type | 触发场景 | data 结构 | 来源 tool |
|------|---------|-----------|-----------|
| `research_points` | "分析研究点" | `{concept_name, points: [{title, hypothesis, description, difficulty, novelty, impact, method, rationale, related_concepts}]}` | `analyze_research_points` |
| `paper_detail` | "这篇论文讲什么" | `{title, authors, year, venue, abstract, tldr, keywords, contributions, citation_count, doi}` | `get_paper_by_title` |
| `paper_list` | "搜索论文" | `{query, papers: [{title, authors, year, citation_count, doi}], count}` | `search_paper` |
| `concept_graph` | "显示图谱" | 现有 `conceptData` 结构 | `get_concept_graph` |
| `recommendation` | "推荐论文" | `{concept_name, papers: [{title, authors, year, abstract, citation_count, venue, open_access_url}]}` | `recommend_papers`（新增） |
| `citation_analysis` | "分析引用" | `{paper_title, citation_count, citations: [{title, year, citation_count}]}` | `analyze_citations` |

## 3. 后端改造

### 3.1 AgentState 增加 attachments

```python
# mkg/agent/state.py
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    current_target: Optional[Dict[str, Any]]
    uploaded_papers: List[Dict[str, str]]
    intent: str
    target_name: Optional[str]
    response: str
    agent_used: str
    needs_summary: bool
    concept_data: Optional[Dict[str, Any]]    # deprecated，向后兼容
    attachments: List[Dict[str, Any]]          # 新增
```

### 3.2 AgentChatResponse 增加 attachments

```python
# backend/schemas.py
class AgentChatResponse(BaseModel):
    message: str
    agent: str
    conceptData: Optional[dict] = None       # deprecated
    attachments: Optional[List[dict]] = None  # 新增
```

### 3.3 Lead Node 改造

核心变化：tool 执行结果同时写入 attachments 和 ToolMessage。

```python
TOOL_ATTACHMENT_MAP = {
    "analyze_research_points": "research_points",
    "get_paper_by_title": "paper_detail",
    "search_paper": "paper_list",
    "get_concept_graph": "concept_graph",
    "analyze_citations": "citation_analysis",
    "recommend_papers": "recommendation",
}

def make_attachment(tool_name: str, result) -> Optional[dict]:
    att_type = TOOL_ATTACHMENT_MAP.get(tool_name)
    if not att_type:
        return None
    if isinstance(result, str) or (isinstance(result, dict) and "error" in result):
        return None
    return {"type": att_type, "data": result}
```

Lead node 中：
- 执行 tool 后调用 `make_attachment` 收集附件
- ToolMessage 传给 LLM 的内容保持文字摘要（不传完整数据，避免 token 浪费）
- 最终返回 `attachments` 列表

### 3.4 新增 tool: recommend_papers

```python
@tool
def recommend_papers(concept_name: str, limit: int = 10) -> Dict[str, Any]:
    """推荐与某概念相关的论文。
    当用户说「推荐论文」「相关论文」「找相关工作」时调用。
    """
    # 1. 查找概念
    # 2. 调用 S2 搜索
    # 3. 返回论文列表
```

### 3.5 analyze_research_points 改造

当前 `analyze_research_points` 返回的是原始数据（local_papers、children_concepts 等），不包含 LLM 生成的研究点。概念页面是通过 `conceptsApi.researchPoints(id)` 调用后端 `/api/concepts/{id}/research-points` 获取 LLM 分析的研究点。

改造：让 tool 也调用同样的研究点分析逻辑，返回包含 LLM 生成研究点的完整结果。

## 4. 前端改造

### 4.1 Store 变更

```typescript
// agentStore.ts
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: string
  conceptData?: ConceptNode      // deprecated
  attachments?: ChatAttachment[] // 新增
  timestamp: number
}
```

### 4.2 组件架构

```
Chat.tsx
  └── 每条消息
        ├── AgentBadge
        ├── Markdown 内容（文字分析）
        └── ChatAttachments（附件分发）
              ├── ResearchPointsCard
              ├── PaperDetailCard
              ├── PaperListCard
              ├── ConceptGraphInChat（现有）
              ├── RecommendationCard
              └── CitationAnalysisCard
```

### 4.3 分发组件

```typescript
// components/ChatAttachments.tsx
function ChatAttachments({ attachments, onSendMessage }: Props) {
  return attachments.map((att, i) => {
    switch (att.type) {
      case 'research_points':   return <ResearchPointsCard key={i} data={att.data} onAction={onSendMessage} />
      case 'paper_detail':      return <PaperDetailCard key={i} data={att.data} />
      case 'paper_list':        return <PaperListCard key={i} data={att.data} onAction={onSendMessage} />
      case 'concept_graph':     return <ConceptGraphInChat key={i} data={att.data} />
      case 'recommendation':    return <RecommendationCard key={i} data={att.data} />
      case 'citation_analysis': return <CitationAnalysisCard key={i} data={att.data} />
      default: return null
    }
  })
}
```

### 4.4 各卡片设计

所有卡片沿用概念页面的学术暖色调风格（sepia/amber/copper 配色，圆角卡片，Source Sans 3 字体）。

**ResearchPointsCard**:
- 标题栏：概念名 + 研究点数量
- 折叠式研究点列表：标题、假设、难度/创新性/影响力三色指示器
- 展开显示描述、发现方法、理由、相关概念标签
- "深入研究" 按钮 → 发送消息

**PaperDetailCard**:
- 标题、年份/引用数/venue 行
- TL;DR 高亮块（绿色调）
- 可折叠：作者、关键词标签、摘要、贡献列表
- DOI 外链

**PaperListCard**:
- 搜索词 + 结果数标题
- 论文行：标题、作者缩略、年份、引用数
- 点击论文 → 发送 "详细介绍《论文名》"

**RecommendationCard**:
- 概念名标题
- 论文条目含 TL;DR
- "添加到知识库" 按钮 → 直接调用 `s2PaperApi.addMetadata`（不经 Agent）

**CitationAnalysisCard**:
- 论文名 + 引用总数
- 引用列表：标题、年份、引用数
- 区分库内/外部论文

### 4.5 卡片交互原则

- **对话驱动操作**（需要 Agent 参与）：按钮发送消息到 Chat，由 Agent 处理
- **纯操作**（不需要分析）：直接调用 API（如"添加到知识库"）

### 4.6 Chat.tsx 改造

消息渲染部分：
```tsx
{msg.role === 'assistant' && msg.attachments && msg.attachments.length > 0 && (
  <ChatAttachments
    attachments={msg.attachments}
    onSendMessage={(text) => {
      setInput(text)
      // 或直接触发 handleSend
    }}
  />
)}
```

### 4.7 向后兼容

- 旧消息的 `conceptData` 仍然渲染（检查 `msg.conceptData` 兜底）
- 新消息统一走 `attachments`

## 5. 文件变更清单

### 后端
- `mkg/agent/state.py` — 增加 `attachments` 字段
- `mkg/agent/nodes/lead.py` — 增加附件收集逻辑、tool-attachment 映射
- `mkg/agent/tools.py` — 新增 `recommend_papers` tool，改造 `analyze_research_points` 返回完整研究点
- `backend/schemas.py` — `AgentChatResponse` 增加 `attachments`
- `backend/routes/agent.py` — 传递 `attachments` 到响应

### 前端
- `frontend/src/stores/agentStore.ts` — `Message` 增加 `attachments` 类型
- `frontend/src/lib/api.ts` — `AgentChatResponse` 增加 `attachments`
- `frontend/src/components/ChatAttachments.tsx` — 新建，附件分发组件
- `frontend/src/components/cards/ResearchPointsCard.tsx` — 新建
- `frontend/src/components/cards/PaperDetailCard.tsx` — 新建
- `frontend/src/components/cards/PaperListCard.tsx` — 新建
- `frontend/src/components/cards/RecommendationCard.tsx` — 新建
- `frontend/src/components/cards/CitationAnalysisCard.tsx` — 新建
- `frontend/src/pages/Chat.tsx` — 接入 ChatAttachments，处理 onSendMessage

## 6. 不在范围内

- 概念页面的搜索筛选、导出、去重扫描 — 这些是图谱管理功能，不适合对话驱动
- 力度调节滑块 — 图谱渲染的内部参数，由 ConceptGraphInChat 自行处理
- 流式响应 — 后续优化，当前保持请求-响应模式
