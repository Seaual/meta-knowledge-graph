# SSE 后台运行实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Agent 对话 SSE 连接从组件生命周期解耦，实现后台运行，用户切换页面后继续接收结果。

**Architecture:** 创建 SSEManager 单例模块管理 SSE 连接，脱离组件生命周期。事件回调直接更新 zustand store。Chat.tsx 只负责触发和渲染。

**Tech Stack:** TypeScript, fetch API (SSE), Zustand

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/lib/sse/types.ts` | 创建 | SSE 事件类型定义 |
| `frontend/src/lib/sse/manager.ts` | 创建 | SSEManager 单例类 |
| `frontend/src/lib/sse/index.ts` | 创建 | 导出入口 |
| `frontend/src/stores/agentStore.ts` | 修改 | 添加 sseStatus 字段 |
| `frontend/src/pages/Chat.tsx` | 修改 | 使用 SSEManager |

---

### Task 1: 创建 SSE 类型定义

**Files:**
- Create: `frontend/src/lib/sse/types.ts`

- [ ] **Step 1: 创建 types.ts 文件**

```typescript
// frontend/src/lib/sse/types.ts
/**
 * SSE 事件类型定义
 */

// SSE 连接状态
export type SSEStatus = 'idle' | 'connecting' | 'connected' | 'error'

// SSE 事件类型（从后端接收）
export interface SSEEvent {
  type: 'status' | 'tool' | 'response' | 'error'
  status?: string
  message?: string
  tool?: string
  label?: string
  attachments?: any[]
}

// 工具状态（用于 UI 显示）
export interface ToolStatus {
  tool: string
  label: string
  status: 'idle' | 'running' | 'completed'
}

// SSE 回调函数
export interface SSECallbacks {
  onToolStatus: (status: ToolStatus | null) => void
  onResponse: (message: string, attachments: any[]) => void
  onComplete: () => void
  onError: (error: string) => void
}

// 内部连接状态
export interface SSEConnection {
  abortController: AbortController
  status: SSEStatus
}
```

- [ ] **Step 2: 验证文件创建**

Run: `cat frontend/src/lib/sse/types.ts`
Expected: 文件内容正确显示

---

### Task 2: 创建 SSEManager 单例类

**Files:**
- Create: `frontend/src/lib/sse/manager.ts`

- [ ] **Step 1: 创建 manager.ts 文件**

```typescript
// frontend/src/lib/sse/manager.ts
/**
 * SSE 连接管理器 - 单例模式
 * 脱离组件生命周期，支持后台运行
 */

import type { SSEStatus, SSECallbacks, SSEConnection, SSEEvent, ToolStatus } from './types'
import type { AgentContextSummary, AgentMessage } from '../api/agent'

class SSEManager {
  private connection: SSEConnection | null = null
  private callbacks: SSECallbacks | null = null

  /**
   * 获取当前 SSE 状态
   */
  getStatus(): SSEStatus {
    return this.connection?.status ?? 'idle'
  }

  /**
   * 启动 Agent 对话 SSE 连接
   */
  startChatStream(
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[],
    callbacks: SSECallbacks
  ): void {
    // 新连接启动前，断开旧连接
    this.disconnect()

    // 创建 AbortController 用于取消请求
    const abortController = new AbortController()
    this.connection = {
      abortController,
      status: 'connecting',
    }
    this.callbacks = callbacks

    // 异步执行 SSE 连接（不阻塞调用方）
    this._executeStream(message, context, history, abortController)
  }

  /**
   * 执行 SSE 流式请求
   */
  private async _executeStream(
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[],
    abortController: AbortController
  ): void {
    try {
      const response = await fetch('/api/agent/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, context, history }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`SSE request failed: ${response.status}`)
      }

      // 更新状态
      if (this.connection) {
        this.connection.status = 'connected'
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 解析 SSE 事件
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            try {
              const event: SSEEvent = JSON.parse(data)
              this._handleEvent(event)
            } catch (e) {
              console.warn('Failed to parse SSE event:', data)
            }
          }
        }
      }

      // 流结束，触发完成回调
      this._complete()
    } catch (error: any) {
      // AbortError 是用户主动取消，不触发错误回调
      if (error.name === 'AbortError') {
        this._cleanup()
        return
      }

      // 更新状态
      if (this.connection) {
        this.connection.status = 'error'
      }

      // 触发错误回调
      if (this.callbacks) {
        this.callbacks.onError(error.message || 'Unknown error')
      }
      this._cleanup()
    }
  }

  /**
   * 处理 SSE 事件
   */
  private _handleEvent(event: SSEEvent): void {
    if (!this.callbacks) return

    if (event.type === 'tool') {
      if (event.status === 'running') {
        this.callbacks.onToolStatus({
          tool: event.tool || '',
          label: event.label || event.tool || '',
          status: 'running',
        })
      } else if (event.status === 'completed') {
        this.callbacks.onToolStatus(null)
      }
    } else if (event.type === 'response') {
      this.callbacks.onResponse(event.message || '', event.attachments || [])
    } else if (event.type === 'status' && event.status === 'completed') {
      // 最终完成状态
    } else if (event.type === 'error') {
      this.callbacks.onError(event.message || 'Unknown error')
    }
  }

  /**
   * 完成处理
   */
  private _complete(): void {
    if (this.callbacks) {
      this.callbacks.onComplete()
    }
    this._cleanup()
  }

  /**
   * 清理连接
   */
  private _cleanup(): void {
    this.connection = null
    this.callbacks = null
  }

  /**
   * 主动断开连接（用户取消）
   */
  disconnect(): void {
    if (this.connection) {
      this.connection.abortController.abort()
      this._cleanup()
    }
  }
}

// 单例导出
export const sseManager = new SSEManager()
```

- [ ] **Step 2: 验证文件创建**

Run: `cat frontend/src/lib/sse/manager.ts`
Expected: 文件内容正确显示

---

### Task 3: 创建 SSE 模块导出入口

**Files:**
- Create: `frontend/src/lib/sse/index.ts`

- [ ] **Step 1: 创建 index.ts 文件**

```typescript
// frontend/src/lib/sse/index.ts
/**
 * SSE 模块导出入口
 */

export { sseManager } from './manager'
export type { SSEStatus, SSECallbacks, ToolStatus, SSEEvent } from './types'
```

- [ ] **Step 2: 验证文件创建**

Run: `cat frontend/src/lib/sse/index.ts`
Expected: 文件内容正确显示

- [ ] **Step 3: 提交 SSE 模块**

```bash
git add frontend/src/lib/sse/
git commit -m "feat(frontend): add SSEManager module for background SSE execution"
```

---

### Task 4: 扩展 agentStore 添加 sseStatus

**Files:**
- Modify: `frontend/src/stores/agentStore.ts`

- [ ] **Step 1: 在 agentStore.ts 顶部导入 SSE 类型**

在文件顶部添加导入：

```typescript
// frontend/src/stores/agentStore.ts
import { create } from 'zustand'
import type { SSEStatus } from '../lib/sse/types'  // 新增
```

- [ ] **Step 2: 在 AgentState 接口中添加 sseStatus 字段**

在 `interface AgentState` 中，`toolStatus: ToolStatus | null` 行之后添加：

```typescript
  // SSE Status (background execution)
  sseStatus: SSEStatus

  // Actions
  // ... 现有 actions ...
  setSSEStatus: (status: SSEStatus) => void
```

- [ ] **Step 3: 在 create 函数初始状态中添加 sseStatus**

在 `export const useAgentStore = create<AgentState>((set) => ({` 中，`toolStatus: null,` 行之后添加：

```typescript
  // SSE Status
  sseStatus: 'idle',

  // Tool Status Actions
  setToolStatus: (status) => set({ toolStatus: status }),

  // SSE Status Action (新增)
  setSSEStatus: (status) => set({ sseStatus: status }),
```

- [ ] **Step 4: 验证修改**

Run: `cat frontend/src/stores/agentStore.ts`
Expected: 新增 sseStatus 字段和 setSSEStatus action

- [ ] **Step 5: 提交 store 修改**

```bash
git add frontend/src/stores/agentStore.ts
git commit -m "feat(frontend): add sseStatus to agentStore for SSE state tracking"
```

---

### Task 5: 修改 Chat.tsx 使用 SSEManager

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`

- [ ] **Step 1: 在文件顶部导入 SSEManager**

在现有导入之后添加：

```typescript
// frontend/src/pages/Chat.tsx
// ... 现有 imports ...
import { sseManager } from '../lib/sse'
```

- [ ] **Step 2: 从 useAgentStore 获取 setSSEStatus**

在 `const { ... } = useAgentStore()` 中添加 `setSSEStatus`：

```typescript
  const {
    isLoading,
    toolStatus,
    contextSummary,
    setLoading,
    setToolStatus,
    updateContext,
    addUploadedPapers,
    setSSEStatus,  // 新增
  } = useAgentStore()
```

- [ ] **Step 3: 修改 handleSend 函数，使用 SSEManager**

将现有的 `handleSend` 函数中的 SSE 调用部分替换为：

```typescript
  // Handle send message
  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')

    // Create conversation if none exists
    let convId = currentConversationId
    if (!convId) {
      convId = await createConversation()
    }

    // Add user message to store (and backend)
    await addMessageToStore({ role: 'user', content: userMessage })
    setLoading(true)
    setToolStatus(null)
    setSSEStatus('connecting')

    // Build history from currentMessages
    const history = messages.map(m => ({
      role: m.role,
      content: m.content,
      agent: m.agent as 'lead' | 'citation' | 'research' | 'deep_research' | 'paper_qa' | 'merge' | undefined,
    }))

    // 使用 SSEManager 启动后台 SSE 连接
    sseManager.startChatStream(
      userMessage,
      contextSummary,
      history,
      {
        onToolStatus: (status) => setToolStatus(status),
        onResponse: (msg, attachments) => {
          addMessageToStore({
            role: 'assistant',
            content: msg,
            agent: 'lead',
            attachments: attachments,
          }).catch(err => console.error('Failed to save message:', err))

          // Generate title if first message
          const { conversations, currentConversationId } = useConversationStore.getState()
          const currentConv = conversations.find(c => c.id === currentConversationId)
          if (messages.length === 0 && !currentConv?.title) {
            const title = userMessage.slice(0, 20).replace(/[？。！.!?]/, '') || '新对话'
            updateTitle(title).catch(err => console.error('Failed to update title:', err))
            loadConversations().catch(err => console.error('Failed to load conversations:', err))
          }
        },
        onComplete: () => {
          setLoading(false)
          setToolStatus(null)
          setSSEStatus('idle')
        },
        onError: (err) => {
          addMessageToStore({
            role: 'assistant',
            content: `抱歉，处理请求时遇到问题：${err}`,
          }).catch(err => console.error('Failed to save message:', err))
          setLoading(false)
          setToolStatus(null)
          setSSEStatus('error')
        },
      }
    )
  }, [input, isLoading, contextSummary, messages, addMessageToStore, updateTitle, loadConversations, setToolStatus, setSSEStatus])
```

- [ ] **Step 4: 验证修改**

Run: `cat frontend/src/pages/Chat.tsx`
Expected: handleSend 使用 sseManager.startChatStream

- [ ] **Step 5: 提交 Chat.tsx 修改**

```bash
git add frontend/src/pages/Chat.tsx
git commit -m "refactor(frontend): use SSEManager in Chat.tsx for background SSE execution"
```

---

### Task 6: 验证整体功能

- [ ] **Step 1: 启动前后端服务**

Run: `./start.bat` 或手动启动前后端

- [ ] **Step 2: 测试基本对话功能**

1. 打开 http://localhost:5173
2. 进入 Chat 页面
3. 发送一条消息，观察 SSE 流式响应正常工作

Expected: 对话正常，工具状态显示正常

- [ ] **Step 3: 测试后台运行**

1. 发送一条需要较长时间处理的消息（如"分析 AgentScope 这篇论文的引用关系"）
2. 在响应过程中，点击侧边栏切换到 Papers 页面
3. 等待几秒后，切换回 Chat 页面

Expected: 回到 Chat 页面时，可以看到完整的响应消息

- [ ] **Step 4: 检查控制台无错误**

打开浏览器开发者工具，检查 Console 无报错

Expected: 无 TypeScript 编译错误，无运行时错误

---

## 自检结果

**1. Spec 覆盖检查:**

| Spec 要求 | 对应 Task |
|-----------|-----------|
| 创建 SSEManager 单例模块 | Task 1, 2, 3 |
| SSE 脱离组件生命周期 | Task 2 (manager.ts 单例设计) |
| 事件回调更新 store | Task 5 (callbacks 内调用 setToolStatus/addMessageToStore) |
| 添加 sseStatus 字段 | Task 4 |
| Chat.tsx 使用 SSEManager | Task 5 |
| 页面切换后继续运行 | Task 2 (_executeStream 异步执行，不阻塞) |
| 结果自动追加到对话历史 | Task 5 (onResponse 回调调用 addMessageToStore) |

✅ 所有 Spec 要求均有对应 Task

**2. Placeholder 扫描:**

✅ 无 TBD/TODO 占位符
✅ 无 "Add appropriate error handling" 等模糊描述
✅ 每个代码步骤包含完整代码

**3. 类型一致性检查:**

✅ `SSEStatus` 在 types.ts 定义，manager.ts 和 agentStore.ts 使用一致
✅ `ToolStatus` 在 types.ts 定义，与 agentStore.ts 原有定义兼容
✅ `SSECallbacks` 类型与 handleSend 中传入的回调对象匹配