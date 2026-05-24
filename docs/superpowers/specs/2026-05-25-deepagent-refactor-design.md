# DeepAgent 重构设计文档

> 将现有 LangGraph Agent 系统全面迁移到 LangChain DeepAgents，同时前端对话 UI 改为 DeepAgent 工作区风格。

---

## 1. 背景与目标

### 1.1 当前架构问题

- 后端 `mkg/agent/` 是自定义 LangGraph 节点，维护成本高
- Deep Research 是独立后台线程，无法与主对话流整合
- 前端聊天是纯消息列表，用户看不到 agent 的 planning 和执行过程
- 子代理（citation/research/paper_qa）通过硬编码路由，不够灵活

### 1.2 目标

- **后端**：用 DeepAgents 替换自定义 LangGraph 架构，利用内置的 planning、subagent、filesystem、memory 能力
- **前端**：UI 改为 DeepAgent 工作区风格，todo 规划、执行轨迹、文件操作、子代理状态全部可视
- **体验**：用户能实时看到 agent "在想什么"、"在做什么"、"做到了哪一步"

---

## 2. 架构总览

### 2.1 技术栈变更

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| Python | >=3.10 | >=3.11 |
| Agent 框架 | 自定义 LangGraph | DeepAgents 0.5.1 |
| 文件系统 | 无 | CompositeBackend (State + Filesystem) |
| 记忆持久化 | MemorySaver | SqliteSaver + SqliteStore |
| 流式输出 | 自定义 SSE | DeepAgents stream() v2 |

### 2.2 目录结构变更

**`mkg/agent/` 重构后：**

```
mkg/agent/
├── __init__.py          # 导出 get_main_agent(), init_agent()
├── agent.py             # create_deep_agent() 配置与主 agent 实例
├── skills/              # 技能目录（替代原 nodes/）
│   ├── __init__.py
│   ├── citation.py      # 引用分析 skill
│   ├── research.py      # 研究点发现 skill
│   ├── paper_qa.py      # 论文问答 skill
│   └── deep_research.py # 深度研究 skill（作为 subagent）
├── tools.py             # 底层工具函数（数据库查询、S2 API、PDF 解析）
├── filesystem.py        # CompositeBackend 配置
├── memory.py            # SqliteSaver + SqliteStore 配置
└── streaming.py         # SSE 流式事件转换器
```

**`frontend/src/pages/` 新增/改造：**

```
frontend/src/pages/
├── Chat.tsx                  # 改造为 AgentWorkspace 容器
└── components/
    ├── AgentWorkspace.tsx    # 三栏布局主容器（新）
    ├── TodoPanel.tsx         # Todo 规划面板（新）
    ├── ExecutionTrace.tsx    # 执行轨迹（新）
    ├── FileExplorer.tsx      # 虚拟文件浏览器（新）
    ├── SubagentBadge.tsx     # 子代理状态徽章（新）
    ├── HumanInTheLoop.tsx    # 人机确认模态框（新）
    ├── ChatAttachments.tsx   # 现有，保留
    └── ConceptGraphInChat.tsx # 现有，保留
```

---

## 3. 后端设计

### 3.1 主 Agent 配置

`mkg/agent/agent.py`：

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore

from mkg.llm import get_llm_or_raise
from .tools import _build_tools
from .skills import _build_subagents

def build_main_agent(db_path: str, workspace_dir: str):
    llm = get_llm_or_raise()

    checkpointer = SqliteSaver.from_conn_string(db_path)
    store = SqliteStore(db_path=db_path)

    backend = CompositeBackend(
        default=StateBackend(),
        routes={
            "/workspace/": FilesystemBackend(
                root_dir=workspace_dir,
                virtual_mode=True,
            ),
        },
    )

    return create_deep_agent(
        model=llm,
        system_prompt=_MAIN_SYSTEM_PROMPT,
        tools=_build_tools(),
        subagents=_build_subagents(),
        backend=lambda rt: backend,
        checkpointer=checkpointer,
        store=store,
    )
```

**`model` 参数**：直接传入 `MKGChatModel`（我们的 `BaseChatModel` 适配器）。DeepAgents 要求模型支持 tool calling，`MKGChatModel` 通过 LangChain 接口已经满足。

**`system_prompt`** 定义 agent 身份、可用 tools、可用 subagents，以及 planning 和文件操作的行为规范。

### 3.2 工具迁移

现有 `mkg/agent/tools.py` 中的函数改造为 DeepAgents 可调用的纯函数。依赖注入通过 `langgraph.config.get_config()` 获取 `runtime.config`：

```python
from langgraph.config import get_config

def search_paper(query: str, limit: int = 5) -> list[dict]:
    """搜索论文"""
    runtime = get_config()
    db = runtime["configurable"]["db"]
    # ... 查询逻辑
```

**迁移清单：**

| 原工具 | 归属 | 说明 |
|--------|------|------|
| `search_paper` | 主 agent | 论文搜索 |
| `get_paper_by_title` | 主 agent | 获取论文详情 |
| `read_paper_content` | 主 agent | 读取 PDF 内容 |
| `get_concept_graph` | 主 agent | 获取概念图谱 |
| `recommend_papers` | 主 agent | 推荐论文 |
| `analyze_citations` | citation subagent | 引用分析 |
| `analyze_research_points` | research subagent | 研究点发现 |
| `deep_research` | deep_research subagent | 多维度深度研究 |

### 3.3 Subagent 设计

4 个专业子代理：

```python
def _build_subagents():
    return [
        {
            "name": "citation-analyst",
            "description": "分析论文的引用关系、引用趋势和关键引用论文",
            "system_prompt": _CITATION_PROMPT,
            "tools": [analyze_citations, get_paper_by_title],
            "model": llm,
        },
        {
            "name": "research-discoverer",
            "description": "基于概念图谱发现研究点和研究机会",
            "system_prompt": _RESEARCH_PROMPT,
            "tools": [analyze_research_points, get_concept_graph, recommend_papers],
            "model": llm,
        },
        {
            "name": "paper-qa",
            "description": "回答关于特定论文的详细问题",
            "system_prompt": _PAPER_QA_PROMPT,
            "tools": [read_paper_content, get_paper_by_title, search_paper],
            "model": llm,
        },
        {
            "name": "deep-researcher",
            "description": "执行多维度深度研究并生成综合报告",
            "system_prompt": _DEEP_RESEARCH_PROMPT,
            "tools": [search_paper, recommend_papers, read_paper_content],
            "model": llm,
        },
    ]
```

DeepAgents 自动提供 `task` 工具。主 agent 根据子代理的 `description` 决定何时委派。

### 3.4 文件系统配置

使用 `CompositeBackend`：

- **`/`（默认 StateBackend）**：agent 内部临时文件，生命周期绑定 thread（对话），通过 checkpointer 持久化
- **`/workspace/`（FilesystemBackend）**：用户可见的工作目录，真实落盘到 `data/agent_files/{thread_id}/`，`virtual_mode=True` 防止路径逃逸

每个对话独立子目录，对话结束后文件保留（可作为历史研究产物）。

### 3.5 记忆持久化

- **Checkpointer**: `SqliteSaver` — 每个 thread 的对话状态（消息历史、todo 进度、执行上下文）
- **Store**: `SqliteStore` — 跨 thread 的长期记忆（用户偏好、常用概念、历史研究主题）

### 3.6 流式输出与 SSE 协议

后端 SSE 端点重写：

```python
async def chat_stream(request: AgentChatRequest):
    agent = get_main_agent()
    thread_id = request.conversationId or "default"

    async def generate():
        for chunk in agent.stream(
            {"messages": _build_messages(request)},
            stream_mode=["updates", "messages", "custom"],
            subgraphs=True,
            version="v2",
            config={"configurable": {"thread_id": thread_id, "db": get_db()},
        ):
            event = _convert_chunk_to_sse(chunk)
            yield f"data: {json.dumps(event)}\n\n"
```

**事件映射表：**

| DeepAgents 事件 | SSE 事件类型 | 内容 |
|-----------------|-------------|------|
| `updates` (planning/todo) | `todo` | `{id, title, status, detail}` |
| `updates` (tool call start) | `tool_call` | `{name, args}` |
| `updates` (tool call end) | `tool_result` | `{name, result, duration}` |
| `updates` (file operation) | `file_op` | `{path, operation, content_preview}` |
| `updates` (subagent start) | `subagent_start` | `{name, task}` |
| `updates` (subagent end) | `subagent_end` | `{name, result}` |
| `messages` (token) | `token` | `{content}` |
| `custom` (progress) | `progress` | `{value, message}` |
| `interrupt` (approval) | `approval_request` | `{id, action, message}` |

### 3.7 Human-in-the-Loop

在以下场景触发 `interrupt`：

1. 调用 `deep-researcher` subagent（耗时较长）
2. 数据库写操作（概念合并、删除）
3. 向 `/workspace/` 覆盖已有文件

前端收到 `approval_request` 后弹出模态框，用户确认后发送 `POST /api/agent/approve`，后端调用 `Command(resume="approved")` 继续执行。用户拒绝则返回 `Command(resume="denied")`，agent 解释无法执行的原因。

---

## 4. 前端设计

### 4.1 整体布局

三栏布局（左侧 Todo+轨迹、中间对话、右侧文件+Subagent）。左右栏可折叠。

### 4.2 组件规格

#### `TodoPanel.tsx`

- 输入：
  ```ts
  interface TodoItem {
    id: string;
    title: string;
    status: "pending" | "running" | "completed" | "failed";
    detail?: string;
    toolName?: string;
    timestamp: number;
  }
  ```
- 行为：步骤可展开查看详情；运行中步骤有琥珀色流动竖线动画；失败步骤可查看错误

#### `ExecutionTrace.tsx`

- 输入：
  ```ts
  interface ExecutionStep {
    id: string;
    type: "tool_call" | "tool_result" | "subagent_start" | "subagent_end";
    name: string;
    args?: Record<string, any>;
    result?: string;
    duration?: number;
    subagentName?: string;
  }
  ```
- 行为：按时间正序显示（从上到下）；每个步骤可展开/折叠；参数和结果 JSON 格式化

#### `FileExplorer.tsx`

- 树形结构展示 `/workspace/` 下文件
- 点击文件预览内容（Markdown 渲染或纯文本）
- 文件被修改时短暂显示"已更新"徽章

#### `SubagentBadge.tsx`

- 嵌入在 assistant 消息气泡上方
- 显示子代理名称和状态（运行中 / 已完成）

#### `HumanInTheLoop.tsx`

- 居中模态框，半透明遮罩
- 显示操作类型、涉及资源、预估影响
- 两个按钮："取消" / "确认执行"

### 4.3 状态管理扩展

`agentStore.ts` 新增：

```ts
interface AgentState {
  // ... 现有状态 ...
  todos: TodoItem[];
  executionSteps: ExecutionStep[];
  virtualFiles: VirtualFile[];
  activeSubagents: ActiveSubagent[];
  pendingApproval: ApprovalRequest | null;
}
```

### 4.4 流式事件分发

SSE 事件到达后，根据 `type` 字段分发到对应的状态更新：

| SSE 事件 | Action |
|----------|--------|
| `todo` | `addTodo()` / `updateTodoStatus()` |
| `tool_call` | `addExecutionStep()` |
| `tool_result` | 更新对应 step |
| `file_op` | `updateVirtualFiles()`，右侧栏自动展开 |
| `subagent_start` | `activeSubagents.push()`，显示徽章 |
| `subagent_end` | 更新 subagent 状态 |
| `token` | 追加到当前 assistant 消息 |
| `approval_request` | `setPendingApproval()`，阻塞后续事件处理 |

### 4.5 兼容现有功能

- 拖拽上传 PDF → 自动触发 `addUploadedPapers()` + 上下文更新
- 附件卡片（概念图谱、论文列表、引用分析）→ 继续在消息区渲染
- 快速操作按钮 → 填入输入框
- 思考过程折叠（`<think>` 标签）→ 保留

---

## 5. 数据流

```
用户输入
  → Chat Input / 快速操作 / PDF 上传
  → POST /api/agent/chat/stream
    → DeepAgent.stream()
      → Planning (write_todos)
      → Tool 调用 (主 agent tools)
      → Subagent 委派 (task)
      → File 操作 (CompositeBackend)
      → Token 生成
    → SSE 事件流 (updates + messages + custom)
  → 前端事件分发器
    → TodoPanel 更新
    → ExecutionTrace 追加
    → FileExplorer 刷新
    → MessageArea 追加 token / 卡片
    → SubagentBadge 显示/隐藏
```

每个对话（thread）隔离：
- SQLite checkpointer 状态按 `thread_id` 隔离
- 文件系统按 `data/agent_files/{thread_id}/` 隔离
- Memory Store 中的跨对话记忆共享

---

## 6. 错误处理

| 场景 | 策略 |
|------|------|
| DeepAgents 内部异常 | 捕获为 SSE `error` 事件，前端显示错误消息，保留已完成步骤 |
| Tool 调用失败 | 返回错误信息给 agent，由 agent 自主决定重试或换方式 |
| LLM API 超时/429 | 利用现有 `mkg/resilience.py` retry 逻辑 |
| Subagent 超时 | 120s 超时，返回部分结果，主 agent 继续 |
| Filesystem 越界 | `virtual_mode=True` 自动阻止，返回权限错误 |
| HITL 拒绝 | `Command(resume="denied")`，agent 解释原因 |

---

## 7. 测试策略

- **单元测试**：每个 tool/skill 独立测试（复用现有 `pytest` 模式）
- **集成测试**：`test_agent_streaming.py` — 验证 SSE 事件流格式和顺序正确
- **端到端测试**：模拟完整对话流程，验证 todo → tool → subagent → response 链路
- **前端测试**：组件级测试（TodoPanel 状态变化、事件分发器逻辑）

---

## 8. 迁移顺序

1. **Phase 1**（1 天）：Python 3.11 升级、`deepagents==0.5.1` 引入、工具层改造为 skills
2. **Phase 2**（2 天）：主 agent + subagents 配置、filesystem + memory 配置、流式输出
3. **Phase 3**（2 天）：前端 DeepAgent UI 组件开发
4. **Phase 4**（1 天）：集成测试、端到端验证、旧代码清理

---

## 9. 风险与缓解

| 风险 | 缓解 |
|------|------|
| DeepAgents 0.5.1 有未发现的 bug | 锁定版本，保留回滚到旧架构的能力（git branch） |
| Python 3.11 升级影响部署 | Docker 镜像同步升级，CI 更新 |
| Tool calling 模型兼容性 | MKGChatModel 已支持 tool calling（通过 LangChain 接口） |
| SSE 流式事件格式不稳定 | 前端事件分发器加容错（未知 type 则忽略） |
| Subagent 委派不准确 | 优化 `description` 和 `system_prompt`，必要时加显式路由提示 |

---

*设计完成，等待实现计划。*
