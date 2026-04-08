---
name: SSE 后台运行设计
description: Agent 对话 SSE 流式响应支持后台运行，用户切换页面后继续接收结果
type: project
---

# SSE 后台运行设计

## 背景

当前 Agent 对话使用 SSE 流式响应，但连接绑定在 Chat.tsx 组件生命周期中。用户切换页面时组件卸载，SSE 连接中断，无法接收后续响应。

## 目标

将 SSE 连接管理从组件生命周期中解耦，实现：
- 发送消息后切换页面，SSE 连接继续运行
- 任务完成时，结果自动追加到对话历史（持久化到数据库）
- 回到 Chat 页面时，自动显示进度和新消息

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        frontend/src                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐     ┌──────────────────┐                   │
│  │  Chat.tsx   │────▶│   SSEManager     │                   │
│  │  (触发连接) │     │  (lib/sse/)      │                   │
│  └─────────────┘     └──────────────────┘                   │
│         │                    │                               │
│         │                    │ 事件回调                       │
│         │                    ▼                               │
│         │              ┌──────────────────┐                  │
│         │              │   agentStore     │                  │
│         │              │ (状态更新)       │                  │
│         │              └──────────────────┘                  │
│         │                    │                               │
│         ▼                    ▼                               │
│  ┌─────────────────────────────────────────┐                 │
│  │           Chat.tsx 渲染                  │                 │
│  │  (从 store 读取状态，显示进度/消息)       │                 │
│  └─────────────────────────────────────────┘                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**核心变化：**
- SSE 连接由 SSEManager 管理，脱离组件生命周期
- 事件回调直接更新 agentStore / conversationStore
- Chat.tsx 只负责触发和渲染，不再持有 SSE 连接

## 文件结构

```
frontend/src/lib/sse/
  ├── index.ts         # 导出入口
  ├── manager.ts       # SSEManager 单例类
  └── types.ts         # SSE 事件类型定义
```

## SSEManager API

```typescript
// manager.ts
class SSEManager {
  private connection: SSEConnection | null = null
  private status: 'idle' | 'connecting' | 'connected' | 'error' = 'idle'

  // 启动 SSE 连接
  startChatStream(
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[],
    callbacks: {
      onToolStatus: (status: ToolStatus) => void
      onResponse: (message: string, attachments: any[]) => void
      onComplete: () => void
      onError: (error: string) => void
    }
  ): void

  // 获取当前状态
  getStatus(): SSEStatus

  // 主动断开连接（用户取消）
  disconnect(): void
}

export const sseManager = new SSEManager()
```

## Store 变化

**agentStore.ts 扩展：**

```typescript
// 新增字段
interface AgentState {
  // ... 现有字段 ...

  // SSE 连接状态（用于 UI 显示）
  sseStatus: 'idle' | 'connecting' | 'connected' | 'error'

  // 新增 action
  setSSEStatus: (status: SSEStatus) => void
}
```

## Chat.tsx 变化

**主要改动点：**

1. `handleSend` 中不再直接调用 `agentApi.chatStreamFetch`
2. 调用 `sseManager.startChatStream()`，传入回调函数
3. 回调函数内调用 `setToolStatus` / `addMessageToStore`
4. 移除 useEffect 中对 SSE 的清理逻辑（如有）

**简化后的 handleSend：**

```typescript
const handleSend = useCallback(async () => {
  if (!input.trim() || isLoading) return

  const userMessage = input.trim()
  setInput('')

  // 添加用户消息
  await addMessageToStore({ role: 'user', content: userMessage })

  // 启动 SSE（后台运行，不阻塞）
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
          attachments,
        })
      },
      onComplete: () => setLoading(false),
      onError: (err) => addMessageToStore({ role: 'assistant', content: `错误：${err}` }),
    }
  )

  setLoading(true)
}, [input, isLoading, ...])
```

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 网络中断 | SSEManager 检测到 error 事件，回调 onError，更新 store |
| 用户取消 | 提供 `disconnect()` 方法，UI 可添加取消按钮 |
| 连接超时 | 设置合理超时（如 60s），超时后触发 onError |
| 多次发送 | 新连接启动前，自动断开旧连接 |

## 页面切换行为

| 操作 | 结果 |
|------|------|
| 发送消息后切换到 Papers 页面 | SSE 连接继续运行，回调继续更新 store |
| 任务完成时 | 消息自动追加到 conversationStore，持久化到数据库 |
| 回到 Chat 页面 | 从 store 读取最新 messages，自动显示新消息 |

## 实现范围

1. 新增 `frontend/src/lib/sse/` 目录，包含 SSEManager 模块
2. 修改 `frontend/src/stores/agentStore.ts`，添加 sseStatus 字段
3. 修改 `frontend/src/pages/Chat.tsx`，使用 SSEManager 替代直接 SSE 调用

**Why:** 用户切换页面时 Agent 对话中断，影响体验。后台运行让用户可以同时浏览其他内容。
**How to apply:** 实现后，用户发送消息后可自由切换页面，结果自动保存到对话历史。