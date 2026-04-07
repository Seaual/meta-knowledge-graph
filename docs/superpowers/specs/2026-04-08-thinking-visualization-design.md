# 思考过程可视化与卡片内容过滤

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现思考过程的实时可视化，并过滤卡片中的思考标签内容

**Architecture:** 后端使用SSE流式推送工具调用状态，前端实时显示状态条，卡片组件过滤思考内容

**Tech Stack:** FastAPI StreamingResponse, EventSource, React State

---

## 功能1: 卡片内容过滤

### 问题
LLM返回的内容包含````````思考标签，在卡片中也会显示，影响用户体验。

### 方案
在卡片组件的ReactMarkdown渲染前，用正则表达式移除思考内容。

### 修改文件
- `frontend/src/components/cards/ResearchPointsCard.tsx`
- `frontend/src/components/cards/DeepResearchCard.tsx`
- `frontend/src/components/cards/PaperDetailCard.tsx`（如有需要）

### 代码实现
```typescript
// 移除思考内容标签
function removeThinkingTags(content: string): string {
  return content.replace(/<tool_call>[\s\S]*?<\/think>/g, '').trim()
}
```

---

## 功能2: 思考过程可视化（流式推送）

### 架构设计

```
后端 (FastAPI)                          前端 (React)
    │                                      │
    │  POST /api/agent/chat (SSE)         │
    │─────────────────────────────────────>│
    │                                      │
    │  event: tool_start                   │
    │  data: {"tool": "analyze_research_points"} │
    │─────────────────────────────────────>│
    │                                      │  显示: "正在分析研究点..."
    │                                      │
    │  event: tool_end                     │
    │  data: {"tool": "analyze_research_points"} │
    │─────────────────────────────────────>│
    │                                      │
    │  event: message                      │
    │  data: {"content": "..."}            │
    │─────────────────────────────────────>│
    │                                      │  显示最终消息
```

### Task 1: 后端SSE支持

**Files:**
- Modify: `backend/routes/agent.py`

- [ ] **Step 1: 添加SSE响应模型**

在 `backend/routes/agent.py` 中添加：

```python
from fastapi.responses import StreamingResponse
import json

class ToolStatusEvent(BaseModel):
    event: str  # tool_start, tool_end, message
    tool: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
```

- [ ] **Step 2: 修改chat端点返回SSE流**

```python
@router.post("/chat/stream")
async def chat_stream(request: AgentChatRequest):
    async def event_generator():
        # 在工具调用前后发送状态事件
        yield f"event: tool_start\ndata: {json.dumps({'tool': 'analyze_research_points'})}\n\n"
        # ... 执行工具
        yield f"event: tool_end\ndata: {json.dumps({'tool': 'analyze_research_points'})}\n\n"
        # 发送最终消息
        yield f"event: message\ndata: {json.dumps({'content': response_content, 'attachments': attachments})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 3: 修改lead node支持回调**

在 `mkg/agent/nodes/lead.py` 中添加工具状态回调支持。

### Task 2: 前端状态管理

**Files:**
- Modify: `frontend/src/stores/agentStore.ts`
- Create: `frontend/src/hooks/useStreamChat.ts`

- [ ] **Step 1: 添加工具状态到store**

```typescript
interface AgentState {
  // ... existing fields
  currentTool: string | null
  toolStatus: 'idle' | 'running' | 'done'
}

// Actions
setCurrentTool: (tool: string | null) => void
```

- [ ] **Step 2: 创建SSE hook**

```typescript
// frontend/src/hooks/useStreamChat.ts
export function useStreamChat() {
  const { setCurrentTool, setLoading } = useAgentStore()
  
  const sendMessage = async (message: string, onMessage: (data: any) => void) => {
    const response = await fetch('/api/agent/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, ... })
    })
    
    const reader = response.body?.getReader()
    // 解析SSE事件并更新状态
  }
  
  return { sendMessage }
}
```

### Task 3: UI状态条组件

**Files:**
- Create: `frontend/src/components/ThinkingStatusBar.tsx`
- Modify: `frontend/src/pages/Chat.tsx`

- [ ] **Step 1: 创建状态条组件**

```typescript
// frontend/src/components/ThinkingStatusBar.tsx
const TOOL_LABELS: Record<string, string> = {
  analyze_research_points: '分析研究点',
  deep_research: '深入研究',
  search_paper: '搜索论文',
  get_concept_graph: '获取概念图谱',
  // ...
}

export default function ThinkingStatusBar({ currentTool }: { currentTool: string | null }) {
  if (!currentTool) return null
  
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-amber/5 rounded-lg">
      <Loader2 className="w-4 h-4 animate-spin" />
      <span className="text-sm">正在{TOOL_LABELS[currentTool] || currentTool}...</span>
    </div>
  )
}
```

- [ ] **Step 2: 集成到Chat页面**

在消息列表上方显示状态条，位于loading indicator同一位置或替换它。

### Task 4: 工具名称中文映射

**Files:**
- Create: `frontend/src/lib/toolLabels.ts`

```typescript
export const TOOL_LABELS: Record<string, string> = {
  analyze_research_points: '分析研究点',
  deep_research: '深入研究',
  search_paper: '搜索论文',
  get_paper_by_title: '获取论文详情',
  read_paper_content: '阅读论文内容',
  analyze_citations: '分析引用关系',
  get_concept_graph: '获取概念图谱',
  recommend_papers: '推荐相关论文',
}
```

---

## 测试计划

1. **卡片过滤测试**：发送包含````````的内容，验证卡片中不显示
2. **状态条测试**：验证工具调用时显示正确的中文状态
3. **流式响应测试**：验证SSE事件正确发送和接收
4. **错误处理测试**：验证工具调用失败时的状态恢复

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| SSE连接中断 | 添加重连逻辑和超时处理 |
| 工具执行时间过长 | 显示已用时间，提供取消按钮 |
| 前端状态不同步 | 使用单一数据源(store)，定期同步 |