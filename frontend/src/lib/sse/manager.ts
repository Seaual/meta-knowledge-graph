// frontend/src/lib/sse/manager.ts
/**
 * SSE 连接管理器 - 单例模式
 * 脱离组件生命周期，支持后台运行
 */

import type { SSEStatus, SSECallbacks, SSEConnection, SSEEvent } from "./types";
import type { AgentContextSummary, AgentMessage } from "../api/agent";

class SSEManager {
  private connection: SSEConnection | null = null;
  private callbacks: SSECallbacks | null = null;
  private _toolStepCount = 0;

  /**
   * 获取当前 SSE 状态
   */
  getStatus(): SSEStatus {
    return this.connection?.status ?? "idle";
  }

  /**
   * 启动 Agent 对话 SSE 连接
   */
  startChatStream(
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[],
    conversationId: string | null,
    callbacks: SSECallbacks
  ): void {
    // 新连接启动前，断开旧连接
    this.disconnect();

    // 重置步骤计数
    this._toolStepCount = 0;

    // 创建 AbortController 用于取消请求
    const abortController = new AbortController();
    this.connection = {
      abortController,
      status: "connecting",
    };
    this.callbacks = callbacks;

    // 异步执行 SSE 连接（不阻塞调用方）
    this._executeStream(
      message,
      context,
      history,
      conversationId,
      abortController
    );
  }

  /**
   * 执行 SSE 流式请求
   */
  private async _executeStream(
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[],
    conversationId: string | null,
    abortController: AbortController
  ): Promise<void> {
    try {
      const response = await fetch("/api/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, context, history, conversationId }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`SSE request failed: ${response.status}`);
      }

      // 更新状态
      if (this.connection) {
        this.connection.status = "connected";
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 解析 SSE 事件
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            try {
              const event: SSEEvent = JSON.parse(data);
              this._handleEvent(event);
            } catch (e) {
              console.warn("Failed to parse SSE event:", data);
            }
          }
        }
      }

      // 流结束，触发完成回调
      this._complete();
    } catch (error: any) {
      // AbortError 是用户主动取消，不触发错误回调
      if (error.name === "AbortError") {
        this._cleanup();
        return;
      }

      // 更新状态
      if (this.connection) {
        this.connection.status = "error";
      }

      // 触发错误回调
      if (this.callbacks) {
        this.callbacks.onError(error.message || "Unknown error");
      }
      this._cleanup();
    }
  }

  /**
   * 处理 SSE 事件
   */
  private _handleEvent(event: SSEEvent): void {
    if (!this.callbacks) return;

    if (event.type === "tool") {
      if (event.status === "running") {
        this._toolStepCount += 1;
        this.callbacks.onToolStatus({
          tool: event.tool || "",
          label: event.label || event.tool || "",
          status: "running",
          step: this._toolStepCount,
          maxSteps: 5,
        });
      } else if (event.status === "completed") {
        this.callbacks.onToolStatus(null);
      }
    } else if (event.type === "response") {
      this.callbacks.onResponse(event.message || "", event.attachments || []);
      // response 事件即完成
      this.callbacks.onComplete();
      // 完成后清理，防止后续事件重复触发
      this._cleanup();
    } else if (event.type === "status" && event.status === "completed") {
      // 最终完成状态（兜底）
      if (this.callbacks) {
        this.callbacks.onComplete();
      }
      this._cleanup();
    } else if (event.type === "error") {
      this.callbacks.onError(event.message || "Unknown error");
    }
  }

  /**
   * 完成处理
   */
  private _complete(): void {
    if (this.callbacks) {
      this.callbacks.onComplete();
    }
    // 确保清理，防止重复触发
    this._cleanup();
  }

  /**
   * 清理连接
   */
  private _cleanup(): void {
    this.connection = null;
    this.callbacks = null;
  }

  /**
   * 主动断开连接（用户取消）
   */
  disconnect(): void {
    if (this.connection) {
      this.connection.abortController.abort();
      this._cleanup();
    }
  }
}

// 单例导出
export const sseManager = new SSEManager();
