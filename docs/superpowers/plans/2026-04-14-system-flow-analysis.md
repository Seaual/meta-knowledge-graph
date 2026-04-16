# 系统操作流程分析

> **文档目的：** 梳理从前端到后端的完整调用链路，验证系统流程是否正确。

---

## 页面概览

系统有 5 个路由页面：

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | Home | 系统首页，展示统计信息、服务状态 |
| `/chat` | Chat | 核心对话页面，所有研究功能集中在此 |
| `/concepts` | ConceptsGraph | 知识图谱可视化 |
| `/papers` | Papers | 论文上传、管理、处理 |
| `/settings` | Settings | LLM 配置、Semantic Scholar 配置 |

**核心页面是 Chat**，所有研究点发现、引用分析、论文搜索等功能都在对话气泡中完成。

---

## 一、Chat 页面 — 按钮与交互形式

### 1.1 欢迎页快捷按钮（首次打开对话时显示）

位置：`Chat.tsx:604-628`

| 按钮 | 显示文本 | 触发的 prompt |
|------|----------|---------------|
| 分析论文引用 | "分析论文引用" | `"分析 AgentScope 这篇论文的引用关系"` |
| 发现研究点 | "发现研究点" | `"帮我分析多智能体系统这个概念的研究点"` |
| 深入研究 | "深入研究" | `"深入研究 AgentScope 平台架构"` |

点击后仅将文本填入输入框，不自动发送。

### 1.2 输入框区域

- **文本输入框**：Enter 发送，Shift+Enter 换行
- **上传 PDF 按钮**：点击触发文件选择器，选择 PDF 后调用 `papersApi.upload()`
- **拖拽上传**：拖入 PDF 文件到整个页面，由 `DragUploadZone` 组件处理

### 1.3 消息气泡中的附件卡片

当 AI 回复携带 `attachments` 时，`ChatAttachments` 组件渲染对应卡片：

| attachment.type | 组件 | 用户可操作 |
|----------------|------|-----------|
| `research_points` | `ResearchPointsCard` | 查看研究点列表 |
| `paper_list` | `PaperListCard` | 查看论文列表 |
| `paper_detail` | `PaperDetailCard` | 查看论文详情 |
| `concept_graph` | `ConceptGraphInChat` | 查看概念图谱 |
| `citation_analysis` | `CitationAnalysisCard` | 查看引用分析 |
| `recommendation` | `RecommendationCard` | 查看推荐论文 |

### 1.4 对话形式

典型的聊天界面：
1. 用户输入文本消息
2. 后端通过 SSE 流式返回响应
3. 可能触发多次 tool 调用，前端显示"正在调用：xxx（步骤 N/5）"
4. 最终返回 AI 回复 + 附件卡片

---

## 二、前端 API 调用列表

### 2.1 SSE 流式对话（核心接口）

**端点：** `POST /api/agent/chat/stream`

**调用位置：** `frontend/src/lib/sse/manager.ts:59`

**请求体：**
```json
{
  "message": "用户输入的消息",
  "context": {
    "currentTarget": { "type": "concept|paper", "id": "...", "name": "..." },
    "uploadedPapers": [],
    "contextTags": [],
    "keyFindings": [],
    "intentHistory": [],
    "lastActiveAgent": "lead"
  },
  "history": [
    { "role": "user|assistant", "content": "...", "agent": "lead" }
  ]
}
```

**SSE 事件流：**
```
data: {"type": "status", "status": "thinking", "message": "正在思考..."}
data: {"type": "tool", "tool": "analyze_research_points", "label": "分析研究点", "status": "running"}
data: {"type": "tool", "status": "completed"}
data: {"type": "response", "message": "AI回复内容", "attachments": [...]}
data: {"type": "status", "status": "completed"}
```

### 2.2 非流式对话（备用）

**端点：** `POST /api/agent/chat`

**调用位置：** `frontend/src/lib/api/agent.ts:67`

返回一次性 `AgentChatResponse`，不走 SSE。

### 2.3 概念相关 API

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/concepts/` | GET | 获取所有概念列表 |
| `/api/concepts/roots` | GET | 获取根概念 |
| `/api/concepts/tree` | GET | 获取概念树 |
| `/api/concepts/search?q=` | GET | 搜索概念 |
| `/api/concepts/{id}` | GET | 获取概念详情 |
| `/api/concepts/{id}/papers` | GET | 获取概念关联论文 |
| `/api/concepts/{id}/research-points` | GET | **发现研究点** |
| `/api/concepts/{id}/search-papers` | GET | 搜索概念相关论文 |

### 2.4 论文相关 API

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/papers/` | GET | 获取论文列表 |
| `/api/papers/upload` | POST | 上传 PDF |
| `/api/papers/process` | POST | 批量处理论文 |
| `/api/papers/process-single` | POST | 处理单篇论文 |
| `/api/papers/{doi}` | GET | 获取论文详情 |
| `/api/papers/{doi}/contribution` | GET | 获取论文贡献 |

### 2.5 对话管理 API

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/conversations` | POST | 创建新对话 |
| `/api/conversations` | GET | 获取对话列表 |
| `/api/conversations/{id}` | GET | 获取对话详情+消息 |
| `/api/conversations/{id}/title` | PUT | 更新对话标题 |
| `/api/conversations/{id}/messages` | POST | 添加消息 |

### 2.6 深入研究 API

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/agent/deep-research/start` | POST | 启动深入研究任务 |
| `/api/agent/deep-research/{id}/status` | GET | 获取研究进度 |
| `/api/agent/deep-research/{id}/report` | GET | 获取研究报告 |

---

## 三、核心函数逻辑详解

### 3.1 `handleSend` — 发送消息（`Chat.tsx:231-319`）

```
输入框不为空 且 不处于加载状态
  ↓
清空输入框
  ↓
如果无当前对话 → createConversation() 创建新对话
  ↓
将用户消息添加到 store（同时保存到后端）
  ↓
设置 isLoading=true, sseStatus="connecting"
  ↓
构建对话历史 messages → [{role, content, agent}]
  ↓
sseManager.startChatStream(userMessage, contextSummary, history, callbacks)
  ↓
callbacks:
  - onToolStatus: 更新工具状态显示
  - onResponse: 将 AI 回复添加到 store
  - onComplete: 设置 isLoading=false
  - onError: 显示错误消息
```

### 3.2 `sseManager.startChatStream` — SSE 连接管理（`manager.ts:25-47`）

```
断开旧连接（如果有）
  ↓
创建 AbortController
  ↓
异步执行 _executeStream()
```

### 3.3 `_executeStream` — 执行 SSE 请求（`manager.ts:52-126`）

```
fetch POST /api/agent/chat/stream
  body: { message, context, history }
  ↓
获取 ReadableStream reader
  ↓
循环读取数据 → 解析 SSE 事件 → _handleEvent()
  ↓
_handleEvent 分发：
  - type="tool" status="running" → onToolStatus 回调
  - type="tool" status="completed" → 清除工具状态
  - type="response" → onResponse + onComplete 回调
  - type="error" → onError 回调
```

### 3.4 后端 `chat_stream` — SSE 流式响应（`backend/routes/agent.py:204-291`）

```
1. 初始化 LLM（从数据库读取配置）
2. 初始化 Tools（db, s2_client, pdf_parser）
3. 构建 LangGraph 初始状态：
   - messages: 历史 + 当前消息
   - current_target: 当前关注的概念/论文
   - intent: "lead"（统一对话节点）
   ↓
4. async generator yield SSE 事件：
   a. yield {"type": "status", "status": "thinking"}
   b. lead_node_stream(initial_state) 迭代：
      - type="tool_call" → yield tool running
      - type="tool_result" → yield tool completed
      - type="response" → yield final response + attachments
   c. yield {"type": "status", "status": "completed"}
```

### 3.5 `lead_node_stream` — 统一对话节点（`mkg/agent/nodes/lead.py:293-391`）

```
1. 构建系统提示 LEAD_SYSTEM_PROMPT
   - 包含工具选择规则、禁止行为、当前上下文
2. messages = [SystemMessage, ...history]
3. llm_with_tools = llm.bind_tools(ALL_TOOLS)
4. 调用 LLM → response
  ↓
5. 工具选择纠正逻辑：
   - 如果 LLM 错误调用 get_concept_graph 处理研究点查询
   - 强制改为 analyze_research_points
  ↓
6. while response.tool_calls (最多 5 轮):
   a. yield {"type": "tool_call", "tool_name": ...}
   b. 执行工具 → 收集结果
   c. yield {"type": "tool_result"}
   d. messages.append(response, tool_results)
   e. 继续调用 LLM
  ↓
7. yield {"type": "response", "content": ..., "attachments": [...]}
```

### 3.6 工具执行链路（`mkg/agent/tools.py`）

| 工具函数 | 后端调用 | 用途 |
|---------|---------|------|
| `analyze_research_points(concept_name)` | `ResearchService.discover_research_points(concept_id)` | **发现研究点** |
| `get_concept_graph(concept_name)` | `db.get_concept_by_text()` → 获取父子概念 | 获取概念图谱结构 |
| `search_paper(query)` | `s2_client.search_papers()` | 搜索 Semantic Scholar 论文 |
| `get_paper_by_title(title)` | `s2_client.search_papers()` → 取第一篇 | 获取论文详情 |
| `analyze_citations(doi)` | `s2_client.get_citations()` | 分析引用关系 |
| `recommend_papers(concept_name)` | 概念图谱 + S2 搜索 | 推荐相关论文 |
| `read_paper_content(doi)` | PDF 解析 + LLM | 阅读论文内容 |

### 3.7 `analyze_research_points` 工具 → 研究点发现

```
1. 调用 analyze_research_points(concept_name="...")
  ↓
2. tools.py 中:
   - 根据名称查找概念 → db.get_concept_by_text(name)
   - 获取 concept_id
   - 调用 ResearchService.discover_research_points(concept_id)
  ↓
3. research_service.py discover_research_points():
   - 获取概念信息
   - 构建祖先链（遍历父概念直到根）
   - BFS 获取后代节点（最大深度 5，限 10 个）
   - 获取兄弟概念（共享父节点的不同分支，限 10 个）
   - 获取边缘节点（叶子节点，限 15 个）
   - 获取相关论文（限 5 篇）
  ↓
4. _build_research_prompt(concept, ancestors, descendants, siblings, edge_nodes, papers)
   → 构建包含四种方法论的提示词
  ↓
5. llm.invoke(prompt) → 解析 JSON → 返回研究点列表
  ↓
6. 返回结果，包含 research_points 和 analysis_context
```

---

## 四、研究点发现 — 完整调用链路

```
用户操作：点击"发现研究点"快捷按钮，或在聊天输入"分析XXX的研究点"
  ↓
前端 Chat.tsx: handleSend() → 发送消息
  ↓
前端 sseManager.startChatStream() → POST /api/agent/chat/stream
  ↓
后端 agent.py: chat_stream() → 初始化 LLM + Tools
  ↓
后端 lead_node_stream() → llm.bind_tools() → LLM 决定调用 analyze_research_points
  ↓
后端 tools.py: analyze_research_points()
  - 根据概念名称查找 concept_id
  - 调用 ResearchService.discover_research_points(concept_id)
  ↓
后端 research_service.py: discover_research_points()
  - 构建完整上下文（祖先、后代、兄弟、边缘节点、论文）
  - _build_research_prompt() → 四种方法论提示词
  - llm.invoke(prompt) → 生成研究点
  ↓
后端 lead_node_stream → yield response + attachments
  ↓
前端 sseManager._handleEvent → onResponse(message, attachments)
  - attachments 包含 research_points 类型的数据
  ↓
前端 ChatAttachments 组件 → ResearchPointsCard 渲染卡片
```

---

## 五、论文处理流程

```
用户操作：在 Papers 页面上传 PDF / 拖拽上传到 Chat 页面
  ↓
前端 papersApi.upload(file) → POST /api/papers/upload
  ↓
后端提取论文信息（DOI、标题、摘要）
  ↓
返回 { success, doi, title }
  ↓
前端 handleUploadSuccess → 设置 currentTarget 为刚上传的论文
  ↓
AI 自动回复："已上传论文《XXX》，你可以问我关于这篇论文的问题。"
  ↓
用户后续操作（聊天中）：
  - "分析这篇论文的引用" → LLM 调用 analyze_citations
  - "处理这篇论文" → papersApi.process(doi) → POST /api/papers/process
    → PDF 解析 → 概念提取 → 保存到知识图谱
```
