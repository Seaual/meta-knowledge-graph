// frontend/src/components/ResearchAgentBubble.tsx
import { useState, useRef, useEffect, useCallback } from "react";
import { useLocation } from "react-router-dom";
import {
  Send,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { useAgentStore, Message } from "../stores/agentStore";
import { agentApi } from "../lib/api";
import { DeepResearchProgress } from "./DeepResearchProgress";
import { useTranslation } from "../i18n";

// 静默状态 - 右侧垂直窄条
function CollapsedBar({
  onExpand,
  messageCount,
}: {
  onExpand: () => void;
  messageCount: number;
}) {
  return (
    <div
      onClick={onExpand}
      className="fixed z-50 cursor-pointer group"
      style={{
        right: 0,
        top: "50%",
        transform: "translateY(-50%)",
        width: "28px",
        height: "180px",
        background: "rgba(250, 248, 245, 0.01)",
        backdropFilter: "blur(1px)",
        WebkitBackdropFilter: "blur(1px)",
        border: "1px solid rgba(184, 134, 11, 0.06)",
        borderRight: "none",
        borderRadius: "14px 0 0 14px",
        boxShadow: "-1px 0 8px rgba(44, 24, 16, 0.01)",
        transition: "all 0.25s ease-out",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "6px",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "rgba(250, 248, 245, 0.02)";
        e.currentTarget.style.width = "32px";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "rgba(250, 248, 245, 0.01)";
        e.currentTarget.style.width = "28px";
      }}
    >
      {/* 图标 */}
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center"
        style={{
          background:
            "linear-gradient(135deg, var(--color-amber) 0%, var(--color-gold) 100%)",
        }}
      >
        <Sparkles className="w-3 h-3 text-white" />
      </div>

      {/* 垂直文字 */}
      <div
        className="font-display text-[10px] font-medium"
        style={{
          color: "var(--color-muted)",
          writingMode: "vertical-rl",
          textOrientation: "mixed",
          letterSpacing: "0.05em",
        }}
      >
        RESEARCH
      </div>

      {/* 消息数 */}
      {messageCount > 0 && (
        <span
          className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-mono"
          style={{
            background: "rgba(184, 134, 11, 0.1)",
            color: "var(--color-amber)",
          }}
        >
          {messageCount}
        </span>
      )}

      {/* 展开箭头 */}
      <ChevronLeft
        className="w-3 h-3 group-hover:translate-x-[-1px] transition-transform"
        style={{ color: "var(--color-faint)" }}
      />
    </div>
  );
}

// 展开状态头部
function DialogHeader({
  onMouseDown,
  onCollapse,
  t,
}: {
  onMouseDown: (e: React.MouseEvent) => void;
  onCollapse: () => void;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <div
      className="flex items-center justify-between px-5 py-3 cursor-move select-none"
      style={{
        background: "transparent",
        borderBottom: "1px solid rgba(184, 134, 11, 0.06)",
      }}
      onMouseDown={onMouseDown}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center"
          style={{
            background:
              "linear-gradient(135deg, var(--color-amber) 0%, var(--color-gold) 100%)",
          }}
        >
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <span
          className="font-display text-base font-medium"
          style={{ color: "var(--color-sepia)" }}
        >
          Research Assistant
        </span>
      </div>

      <button
        onClick={onCollapse}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-medium transition-all"
        style={{ color: "var(--color-muted)" }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "rgba(184, 134, 11, 0.06)";
          e.currentTarget.style.color = "var(--color-sepia)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
          e.currentTarget.style.color = "var(--color-muted)";
        }}
      >
        <span className="text-sm">{t.common.collapse}</span>
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}

// 上下文指示器
function ContextIndicator({
  target,
  onClear,
  t,
}: {
  target?: { type: "concept" | "paper"; id: string; name: string };
  onClear: () => void;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (!target) return null;

  const icon = target.type === "paper" ? "📄" : "💡";

  return (
    <div
      className="flex items-center justify-between px-4 py-2 mx-4 mt-2 rounded-medium"
      style={{
        background: "rgba(184, 134, 11, 0.04)",
        border: "1px solid rgba(184, 134, 11, 0.08)",
      }}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm">{icon}</span>
        <span
          className="text-xs font-medium truncate max-w-[200px]"
          style={{ color: "var(--color-sepia)" }}
        >
          {target.name}
        </span>
        <span
          className="text-[10px] px-1.5 py-0.5 rounded-soft"
          style={{
            background: "rgba(184, 134, 11, 0.08)",
            color: "var(--color-muted)",
          }}
        >
          {target.type === "paper" ? t.nav.papers : t.nav.concepts}
        </span>
      </div>
      <button
        onClick={onClear}
        className="w-5 h-5 rounded-full flex items-center justify-center text-xs hover:bg-amber/10 transition-colors"
        style={{ color: "var(--color-muted)" }}
      >
        ×
      </button>
    </div>
  );
}

// 消息气泡
function MessageBubble({ msg, isUser }: { msg: Message; isUser: boolean }) {
  return (
    <div
      className={`max-w-[80%] px-4 py-2.5 rounded-medium text-sm ${
        isUser ? "ml-auto" : "mr-auto"
      }`}
      style={{
        fontFamily: "var(--font-body)",
        ...(isUser
          ? {
              background:
                "linear-gradient(135deg, var(--color-amber) 0%, var(--color-gold) 100%)",
              color: "var(--color-vellum)",
              boxShadow: "0 2px 8px rgba(184, 134, 11, 0.1)",
            }
          : {
              background: "rgba(245, 240, 232, 0.02)",
              border: "1px solid rgba(184, 134, 11, 0.04)",
              color: "var(--color-ink)",
            }),
      }}
    >
      <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
    </div>
  );
}

// 消息列表
function MessageList({
  messages,
  onResearchComplete,
  t,
}: {
  messages: Message[];
  onResearchComplete: (sessionId: string, report: string) => void;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div
      ref={listRef}
      className="flex-1 overflow-y-auto p-4 space-y-3"
      style={{ background: "transparent", minHeight: "200px" }}
    >
      {messages.length === 0 && (
        <div className="text-center py-8">
          <p
            className="text-base font-medium"
            style={{ color: "var(--color-sepia)" }}
          >
            {t.researchAgent.ready}
          </p>
          <div
            className="flex flex-col gap-2 text-sm mt-5"
            style={{ color: "var(--color-muted)" }}
          >
            {[t.researchAgent.analyzeCitations, t.researchAgent.discoverConcepts, t.researchAgent.deepDive].map(
              (item, i) => (
                <div
                  key={i}
                  className="py-1.5 hover:text-sepia transition-colors cursor-pointer"
                >
                  → {item}
                </div>
              )
            )}
          </div>
        </div>
      )}

      {messages.map((msg) => (
        <div key={msg.id} className="animate-slide-up">
          <MessageBubble msg={msg} isUser={msg.role === "user"} />
          {msg.role === "assistant" &&
            msg.agent === "deep_research" &&
            msg.researchSessionId && (
              <div className="mt-2 max-w-[80%]">
                <DeepResearchProgress
                  sessionId={msg.researchSessionId}
                  onComplete={(report) =>
                    onResearchComplete(msg.researchSessionId!, report)
                  }
                />
              </div>
            )}
        </div>
      ))}
    </div>
  );
}

// 输入区域
function ChatInput({
  onSend,
  isLoading,
  t,
}: {
  onSend: (message: string) => void;
  isLoading: boolean;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSend(input.trim());
      setInput("");
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-4 flex-shrink-0"
      style={{
        background: "transparent",
        borderTop: "1px solid rgba(184, 134, 11, 0.06)",
      }}
    >
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t.researchAgent.placeholder}
          style={{
            flex: 1,
            padding: "0.75rem 1rem",
            background: "rgba(245, 240, 232, 0.02)",
            border: "1px solid rgba(184, 134, 11, 0.08)",
            borderRadius: "8px",
            color: "var(--color-ink)",
            fontFamily: "var(--font-body)",
            fontSize: "0.9rem",
            outline: "none",
          }}
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="btn-primary px-5 py-3"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>
    </form>
  );
}

// 主组件
export default function ResearchAgentBubble() {
  const location = useLocation();
  const { t } = useTranslation();

  // 在 Chat 页面和 Concepts 页面不显示这个浮框
  if (location.pathname === "/chat" || location.pathname === "/concepts") {
    return null;
  }

  const {
    isOpen,
    messages,
    isLoading,
    contextSummary,
    setPosition,
    addMessage,
    setLoading,
    updateContext,
    setCurrentAgent,
  } = useAgentStore();

  // 清除当前上下文
  const handleClearContext = () => {
    updateContext({ currentTarget: undefined });
  };

  const [isExpanded, setIsExpanded] = useState(false);
  const [dialogPosition, setDialogPosition] = useState({ y: 0 });
  const dragging = useRef(false);
  const dragOffset = useRef({ y: 0 });
  const dialogRef = useRef<HTMLDivElement>(null);

  // 初始化位置 - 垂直居中
  useEffect(() => {
    const y = (window.innerHeight - 550) / 2;
    setDialogPosition({ y });
    setPosition({ x: window.innerWidth - 400, y });
  }, [setPosition]);

  // Handle drag
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      if (dialogRef.current && isExpanded) {
        const rect = dialogRef.current.getBoundingClientRect();
        dragOffset.current = {
          y: e.clientY - rect.top,
        };
        dragging.current = true;
      }
    },
    [isExpanded]
  );

  useEffect(() => {
    if (!dragging.current) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newY = Math.max(
        20,
        Math.min(e.clientY - dragOffset.current.y, window.innerHeight - 580)
      );
      setDialogPosition({ y: newY });
      setPosition({ x: window.innerWidth - 400, y: newY });
    };

    const handleMouseUp = () => {
      dragging.current = false;
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [setPosition]);

  // Send message
  const handleSend = async (message: string) => {
    addMessage({ role: "user", content: message });
    setLoading(true);

    try {
      const response = await agentApi.chat(message, contextSummary, []);
      if (response.agent) setCurrentAgent(response.agent as any);

      if (response.researchSessionId) {
        addMessage({
          role: "assistant",
          content: response.message,
          agent: "deep_research",
          researchSessionId: response.researchSessionId,
        });
      } else {
        addMessage({
          role: "assistant",
          content: response.message,
          agent: response.agent as any,
          conceptData: response.conceptData,
        });
      }

      if (response.contextUpdate) updateContext(response.contextUpdate as any);
    } catch {
      addMessage({
        role: "assistant",
        content: t.researchAgent.errorMsg,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleResearchComplete = useCallback(
    (_sessionId: string, report: string) => {
      addMessage({
        role: "assistant",
        content: report,
        agent: "deep_research",
      });
    },
    [addMessage]
  );

  if (!isOpen) return null;

  // 静默状态 - 右侧窄条
  if (!isExpanded) {
    return (
      <CollapsedBar
        onExpand={() => setIsExpanded(true)}
        messageCount={messages.length}
      />
    );
  }

  // 展开状态 - 从右侧滑出
  return (
    <div
      ref={dialogRef}
      className="fixed z-50 flex flex-col overflow-hidden"
      style={{
        width: "380px",
        height: "550px",
        right: 0,
        top: dialogPosition.y,
        background: "rgba(250, 248, 245, 0.01)",
        backdropFilter: "blur(2px)",
        WebkitBackdropFilter: "blur(2px)",
        border: "1px solid rgba(184, 134, 11, 0.08)",
        borderRight: "none",
        borderRadius: "20px 0 0 20px",
        boxShadow: "-4px 0 32px rgba(44, 24, 16, 0.03)",
        animation: "slideInRight 0.35s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      <style>{`
        @keyframes slideInRight {
          0% {
            opacity: 0;
            transform: translateX(20px);
          }
          100% {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>

      <DialogHeader
        onMouseDown={handleMouseDown}
        onCollapse={() => setIsExpanded(false)}
        t={t}
      />
      <ContextIndicator
        target={contextSummary.currentTarget}
        onClear={handleClearContext}
        t={t}
      />
      <MessageList
        messages={messages}
        onResearchComplete={handleResearchComplete}
        t={t}
      />
      <ChatInput onSend={handleSend} isLoading={isLoading} t={t} />
    </div>
  );
}
