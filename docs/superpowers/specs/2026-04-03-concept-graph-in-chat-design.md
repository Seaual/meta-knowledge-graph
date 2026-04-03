# 概念图谱嵌入聊天功能设计

## 概述

当用户在聊天中询问概念相关问题时，在对话消息气泡中直接嵌入一个迷你概念图谱，展示概念的层级结构和关联论文，然后在其下方显示AI的回答。

## 功能需求

### 触发条件

当满足以下条件之一时触发：
1. 用户消息中包含"概念"关键词（如"这个概念"、"分析概念"）
2. 上下文 `currentTarget.type === 'concept'`
3. 路由到 `research` 节点的请求

### 数据流程

```
用户提问 "分析多智能体系统的研究点"
    ↓
后端路由识别 → research 节点
    ↓
research_node 调用 get_concept_info 工具
    ↓
返回 AgentChatResponse，新增 conceptData 字段
    ↓
前端渲染概念图谱 + 文字回答
```

## 技术设计

### 1. 后端修改

#### 1.1 扩展 AgentChatResponse schema

```python
# backend/schemas.py

class ConceptGraphData(BaseModel):
    """概念图谱数据"""
    id: str
    name: str
    category: Optional[str] = None
    paper_count: int = 0
    children: List['ConceptGraphData'] = []
    parents: List['ConceptGraphData'] = []

class AgentChatResponse(BaseModel):
    """Response from agent chat endpoint"""
    message: str
    agent: str
    contextUpdate: Optional[dict] = None
    researchSessionId: Optional[str] = None
    conceptData: Optional[ConceptGraphData] = None  # 新增
```

#### 1.2 修改 research_node 返回概念数据

```python
# mkg/agent/nodes/research.py

def research_node(state: AgentState) -> Dict[str, Any]:
    # ... 现有逻辑 ...

    # 获取概念图谱数据
    concept_data = None
    target_name = state.get("target_name")

    if target_name and _db:
        concept = _db.get_concept_by_name(target_name)
        if concept:
            children = _db.get_concept_children(concept['id'])
            parents = _db.get_concept_parents(concept['id'])

            concept_data = {
                "id": concept['id'],
                "name": concept['text'],
                "category": concept.get('category'),
                "paper_count": concept.get('paper_count', 0),
                "children": [{"id": c['id'], "name": c['text'], "paper_count": c.get('paper_count', 0)} for c in children[:10]],
                "parents": [{"id": p['id'], "name": p['text'], "paper_count": p.get('paper_count', 0)} for p in parents[:5]],
            }

    return {
        "response": response_content,
        "agent_used": "research",
        "needs_summary": len(response_content) > 1000,
        "messages": [AIMessage(content=response_content)],
        "concept_data": concept_data,  # 新增
    }
```

#### 1.3 修改 backend/routes/agent.py

```python
@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest):
    # ... 现有逻辑 ...

    result = graph.invoke(initial_state, config)

    # 提取概念数据
    concept_data = result.get("concept_data")

    return AgentChatResponse(
        message=result.get("response", "抱歉，处理请求时遇到问题。"),
        agent=result.get("agent_used", "lead"),
        contextUpdate=context_update,
        conceptData=concept_data,  # 新增
    )
```

### 2. 前端修改

#### 2.1 扩展 Message 类型

```typescript
// frontend/src/stores/agentStore.ts

interface ConceptNode {
  id: string
  name: string
  category?: string
  paper_count: number
  children?: ConceptNode[]
  parents?: ConceptNode[]
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: string
  researchSessionId?: string
  conceptData?: ConceptNode  // 新增
}
```

#### 2.2 创建 MiniConceptGraph 组件

```tsx
// frontend/src/components/MiniConceptGraph.tsx

import { useEffect, useRef } from 'react'
import ForceGraph from 'force-graph'

interface Props {
  data: ConceptNode
  width?: number
  height?: number
}

export default function MiniConceptGraph({ data, width = 300, height = 200 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    // 构建节点和边
    const nodes = [
      { id: data.id, name: data.name, type: 'center', paperCount: data.paper_count },
    ]

    const links: { source: string; target: string }[] = []

    // 添加子概念
    data.children?.forEach((child, i) => {
      nodes.push({
        id: child.id,
        name: child.name,
        type: 'child',
        paperCount: child.paper_count
      })
      links.push({ source: data.id, target: child.id })
    })

    // 添加父概念
    data.parents?.forEach((parent) => {
      nodes.push({
        id: parent.id,
        name: parent.name,
        type: 'parent',
        paperCount: parent.paper_count
      })
      links.push({ source: parent.id, target: data.id })
    })

    // 创建迷你图谱
    const graph = ForceGraph()(containerRef.current)
      .graphData({ nodes, links })
      .width(width)
      .height(height)
      .nodeId('id')
      .nodeLabel('name')
      .nodeColor(node => {
        const n = node as any
        if (n.type === 'center') return '#d4a012'  // gold
        if (n.type === 'parent') return '#6b4423'  // sepia
        return '#4a6b8a'  // slate blue
      })
      .nodeSize(node => {
        const n = node as any
        return n.type === 'center' ? 8 : 5
      })
      .linkColor(() => 'rgba(184, 134, 11, 0.3)')
      .linkWidth(1)
      .cooldownTicks(50)
      .enableZoomInteraction(false)
      .enableNodeDrag(false)

    return () => graph._destructor()
  }, [data, width, height])

  return (
    <div
      ref={containerRef}
      style={{
        width,
        height,
        borderRadius: '8px',
        background: 'rgba(245, 240, 232, 0.02)',
        border: '1px solid rgba(184, 134, 11, 0.08)',
      }}
    />
  )
}
```

#### 2.3 修改 Chat.tsx 渲染消息

```tsx
// frontend/src/pages/Chat.tsx

import MiniConceptGraph from '../components/MiniConceptGraph'

// 在消息渲染部分添加：
{msg.role === 'assistant' && msg.conceptData && (
  <div className="mb-3">
    <MiniConceptGraph data={msg.conceptData} width={320} height={180} />
  </div>
)}
```

#### 2.4 修改 API 调用处理概念数据

```tsx
// frontend/src/lib/api.ts

async chat(
  message: string,
  context: ContextSummary,
  history?: Message[]
): Promise<AgentChatResponse & { conceptData?: ConceptNode }> {
  const response = await fetch(`${BASE_URL}/api/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, context, history: history || [] }),
  })

  const data = await response.json()
  return data
}
```

## 视觉设计

### 迷你图谱样式

- **尺寸**：320px × 180px（在消息气泡内）
- **节点颜色**：
  - 当前概念：金色 (#d4a012)
  - 父概念：深褐色 (#6b4423)
  - 子概念：石板蓝 (#4a6b8a)
- **交互**：禁用缩放和拖拽，仅显示静态布局
- **边框**：淡金色边框，与整体设计风格一致

### 消息布局

```
┌────────────────────────────────────┐
│ [research 标签]                     │
├────────────────────────────────────┤
│ ┌──────────────────────────────┐   │
│ │     迷你概念图谱              │   │
│ │    ForceGraph 可视化          │   │
│ └──────────────────────────────┘   │
│                                    │
│ 文字回答内容...                     │
│                                    │
└────────────────────────────────────┘
```

## 文件修改清单

### 后端
1. `backend/schemas.py` - 添加 ConceptGraphData 和扩展 AgentChatResponse
2. `mkg/agent/nodes/research.py` - 返回 concept_data
3. `backend/routes/agent.py` - 传递 conceptData 到响应
4. `mkg/database.py` - 添加 get_concept_by_name 方法（如不存在）

### 前端
1. `frontend/src/stores/agentStore.ts` - 扩展 Message 类型
2. `frontend/src/components/MiniConceptGraph.tsx` - 新建组件
3. `frontend/src/pages/Chat.tsx` - 渲染概念图谱
4. `frontend/src/lib/api.ts` - 更新返回类型

## 测试要点

1. **路由测试**：验证概念相关问题正确路由到 research 节点
2. **数据测试**：验证后端正确返回概念图谱数据
3. **渲染测试**：验证前端正确渲染迷你图谱
4. **空数据处理**：概念不存在时的优雅降级
5. **性能测试**：多个图谱时的渲染性能