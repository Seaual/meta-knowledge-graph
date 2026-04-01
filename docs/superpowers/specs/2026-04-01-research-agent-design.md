---
name: research-agent-design
description: 研究助手 Agent 功能设计 - 多 Agent 协作的对话式研究助手
type: project
---

# 研究助手 Agent 设计文档

## 概述

为 Meta Knowledge Graph 添加一个全局浮动对话框式的研究助手，支持自然语言交互，提供引用分析、研究点分析、深入研究三大功能。

**核心特性：**
- 气泡式 UI，半透明可拖动，跨页面持久
- 自然语言触发，Agent 自动识别意图
- 多 Agent 协作架构，Lead Agent 分发任务
- 深入研究采用 Anthropic 风格的多 Agent 设计

---

## 1. UI 设计

### 1.1 交互形式

| 属性 | 设计 |
|------|------|
| 触发方式 | 右下角气泡按钮，点击展开对话框 |
| 窗口样式 | 半透明背景 `rgba(255,255,255,0.85)`，圆角 16px |
| 可拖动 | 标题栏作为拖动区域 |
| 全局性 | App 层级组件，路由切换时保持状态 |
| 最小化 | 点击 − 按钮回到气泡状态，保持对话上下文 |

### 1.2 组件位置

```
App.tsx
├── BrowserRouter
│   ├── Header
│   ├── Routes (页面内容)
│   └── ResearchAgentBubble  ← 全局组件
```

### 1.3 状态管理

使用 Zustand 管理全局状态：
- `isOpen`: 对话框是否展开
- `isMinimized`: 是否最小化为气泡
- `position`: 窗口位置 { x, y }
- `currentAgent`: 当前活跃的 Agent
- `messages`: 对话历史
- `contextSummary`: 全局上下文摘要

---

## 2. Agent 架构

### 2.1 整体架构

```
用户输入
    ↓
┌─────────────────────────────────────┐
│         Lead Agent                  │
│  · 意图识别                          │
│  · 任务分发                          │
│  · 上下文摘要维护                    │
└─────────────────────────────────────┘
    ↓ 分发
┌──────────┬──────────┬───────────────┐
│ Citation │ Research │ Deep Research │
│  Agent   │  Agent   │    Agent      │
└──────────┴──────────┴───────────────┘
```

### 2.2 Lead Agent 职责

**意图识别：**
- `citation_analysis`: 分析论文引用关系
- `research_point`: 分析概念研究点
- `deep_research`: 启动深入研究模式
- `follow_up`: 继续当前对话

**上下文摘要维护：**
- 当前研究对象（论文 DOI / 概念 ID）
- 研究上下文标签
- 已获取的关键结论
- 用户意图历史

**任务分发：**
- 根据意图选择专业 Agent
- 传递上下文摘要
- 接收并整合结果

### 2.3 专业 Agent 职责

#### Citation Agent

**功能：** 分析论文的引用和被引用关系

**输入：**
- 论文标识（DOI / 标题 / S2 Paper ID）
- 研究上下文（从 Lead Agent 传递）

**处理流程：**
1. 通过 S2 API 获取引用数据
2. 统计分析（被引次数、年份分布、领域分布）
3. 深度分析（高影响力引用者、引用脉络演变、引用聚类）
4. 生成分析报告

**输出：**
- 引用统计摘要
- 高影响力引用者列表
- 引用脉络分析
- 领域分布图表数据

#### Research Point Agent

**功能：** 分析图谱中概念的研究点

**输入：**
- 概念标识（概念 ID / 概念名称）
- 研究上下文

**处理流程：**
1. 在图谱中定位概念
2. 追溯上游节点（祖先链）
3. 发现下游节点（后代）
4. 获取邻域节点（兄弟分支）
5. 调用 S2 API 获取领域热度数据
6. LLM 分析生成研究点建议
7. 支持后续追问

**输出：**
- 概念结构关系
- 研究点建议列表
- S2 热度数据
- 支持追问交互

#### Deep Research Agent

**功能：** 系统化深入研究，生成完整报告

**架构：** 内部多 Agent 协作（参考 Anthropic 方案）

```
┌─────────────────────────────────────┐
│      Lead Researcher Agent          │
│  · 规划研究维度                      │
│  · 协调 Sub-agents                  │
│  · 压缩整合结果                      │
│  · 生成最终报告                      │
└─────────────────────────────────────┘
         ↓ 任务契约分发
┌──────────┬──────────┬──────────┬─────┐
│Sub-agent │Sub-agent │Sub-agent │ ... │
│  维度1   │  维度2   │  维度3   │     │
└──────────┴──────────┴──────────┴─────┘
         ↓ 压缩输出
```

**Sub-agent 设计：**
- 独立上下文窗口，互不干扰
- 内部 ReAct 循环：Reasoning → Action → Observation → 迭代
- 输出压缩：完整探索过程 → 关键发现 + 引用

**任务契约：**
每个 Sub-agent 接收清晰的任务定义：
- 目标（具体要找什么）
- 输出格式（结构化要求）
- 可用工具（S2 API、图谱查询）
- 边界约束（什么不该做）

**异步执行：**
- 研究任务运行 10-30 分钟
- 前端显示实时进度
- 支持检查点恢复
- 单步失败不影响全局

**输出：**
- 网页格式研究报告
- 可导出 Markdown / PDF
- 每个结论带引用追溯

---

## 3. 上下文共享机制

### 3.1 Lead Agent 维护的上下文

```json
{
  "currentTarget": {
    "type": "concept | paper",
    "id": "transformer-architecture",
    "name": "Transformer 架构"
  },
  "contextTags": ["技术演进", "NLP", "注意力机制"],
  "keyFindings": [
    "该论文被引 12,847 次",
    "主要应用领域：NLP(45%), CV(30%)"
  ],
  "intentHistory": ["citation_analysis", "research_point"],
  "lastActiveAgent": "research_point"
}
```

### 3.2 Agent 切换时传递

切换 Agent 时，Lead Agent 传递：
- 当前研究对象 ID
- 研究上下文标签
- 用户最新意图

**示例：**
用户："分析 Transformer 的引用" → Citation Agent
用户追问："深入研究这个概念" → Deep Research Agent

Deep Research Agent 接收：
```json
{
  "conceptId": "transformer-architecture",
  "conceptName": "Transformer 架构",
  "priorFindings": ["被引 12,847 次", "NLP/CV 主要应用"],
  "userIntent": "deep_research"
}
```

---

## 4. 数据存储

### 4.1 新增数据库表

#### research_sessions 表

```sql
CREATE TABLE research_sessions (
  id TEXT PRIMARY KEY,
  user_query TEXT NOT NULL,
  target_type TEXT,  -- concept | paper
  target_id TEXT,
  status TEXT DEFAULT 'running',  -- running | completed | failed
  dimensions TEXT,  -- JSON: 研究维度列表
  progress INTEGER DEFAULT 0,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  report_path TEXT  -- 生成的报告文件路径
);
```

#### research_findings 表

```sql
CREATE TABLE research_findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  dimension TEXT,  -- 研究维度
  finding TEXT,  -- 关键发现
  sources TEXT,  -- JSON: 引用来源列表
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES research_sessions(id)
);
```

#### agent_context 表

```sql
CREATE TABLE agent_context (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,  -- 对话会话 ID
  context_json TEXT,  -- JSON: 上下文摘要
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 报告存储

研究报告存储在 `reports/` 目录：
- `{session_id}.html` - 网页报告
- `{session_id}.md` - Markdown 导出
- `{session_id}.pdf` - PDF 导出

---

## 5. API 设计

### 5.1 新增后端路由

```
POST /api/agent/chat
  - 接收用户消息
  - 返回 Agent 响应（流式）

POST /api/agent/deep-research/start
  - 启动深入研究任务
  - 返回 session_id

GET /api/agent/deep-research/{session_id}/status
  - 获取研究进度

GET /api/agent/deep-research/{session_id}/report
  - 获取研究报告

GET /api/agent/context
  - 获取当前上下文摘要

PUT /api/agent/context
  - 更新上下文摘要
```

### 5.2 前端 API 调用

```typescript
// 对话接口
const response = await fetch('/api/agent/chat', {
  method: 'POST',
  body: JSON.stringify({
    message: userMessage,
    context: currentContext
  })
})

// 深入研究
const { sessionId } = await fetch('/api/agent/deep-research/start', {
  method: 'POST',
  body: JSON.stringify({
    targetId: conceptId,
    targetType: 'concept',
    query: userQuery
  })
}).then(r => r.json())

// 轮询进度
const status = await fetch(`/api/agent/deep-research/${sessionId}/status`)
  .then(r => r.json())
```

---

## 6. 技术实现要点

### 6.1 LLM 调用

复用现有的 `LiteLLMClient`，根据 Agent 类型选择不同 Prompt：

- **Lead Agent**: 意图识别 Prompt + 任务分发逻辑
- **Citation Agent**: 引用分析 Prompt + S2 API 工具
- **Research Agent**: 研究点分析 Prompt + 图谱查询工具
- **Deep Research**: 多 Agent 协调 Prompt + 完整工具集

### 6.2 流式响应

使用 Server-Sent Events (SSE) 实现流式对话：

```python
@router.post("/chat")
async def chat(request: ChatRequest):
    async def generate():
        async for chunk in agent.stream_response(request.message):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

### 6.3 深入研究异步执行

使用 `asyncio` 后台任务：

```python
async def run_deep_research(session_id: str, query: str):
    lead_researcher = LeadResearcherAgent()
    await lead_researcher.plan_dimensions(query)
    
    for dimension in lead_researcher.dimensions:
        sub_agent = SubAgent(dimension)
        result = await sub_agent.explore()
        compressed = compress_result(result)
        lead_researcher.integrate(compressed)
    
    report = lead_researcher.generate_report()
    save_report(session_id, report)
```

### 6.4 前端状态管理

```typescript
// stores/agentStore.ts
import { create } from 'zustand'

interface AgentState {
  isOpen: boolean
  isMinimized: boolean
  position: { x: number; y: number }
  currentAgent: 'lead' | 'citation' | 'research' | 'deep_research'
  messages: Message[]
  contextSummary: ContextSummary
  
  // Actions
  toggleOpen: () => void
  minimize: () => void
  setPosition: (pos: { x: number; y: number }) => void
  addMessage: (msg: Message) => void
  updateContext: (ctx: Partial<ContextSummary>) => void
}
```

---

## 7. 实现优先级

### Phase 1: 基础框架
1. 全局浮动对话框组件
2. Zustand 状态管理
3. Lead Agent 意图识别
4. 基础对话接口

### Phase 2: Citation Agent
1. S2 引用数据获取
2. 引用统计分析
3. 深度分析报告

### Phase 3: Research Point Agent
1. 图谱结构分析
2. 研究点生成
3. S2 热度数据整合
4. 追问支持

### Phase 4: Deep Research Agent
1. 多 Agent 协调框架
2. 任务契约机制
3. Sub-agent ReAct 循环
4. 异步执行 + 进度推送
5. 报告生成 + 导出

---

## 8. 测试计划

### 8.1 单元测试
- Lead Agent 意图识别准确率
- 各 Agent 工具调用正确性
- 上下文传递完整性

### 8.2 集成测试
- 端到端对话流程
- Agent 切换时上下文保持
- 深入研究异步执行

### 8.3 用户测试
- 意图识别是否符合用户预期
- 深入研究进度反馈是否清晰
- 报告质量是否满足学术需求