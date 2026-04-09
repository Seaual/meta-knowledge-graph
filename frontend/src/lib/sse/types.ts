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
  step?: number       // 当前是第几步（从 1 开始）
  maxSteps?: number   // 最大步数（用于显示进度，如 "步骤 2/5"）
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