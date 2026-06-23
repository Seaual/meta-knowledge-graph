// Chat.tsx - LLM Conversation Page
// 墨迹书房风格 - Ink & Study Design

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  lazy,
  Suspense,
  Component,
  ReactNode,
} from "react";
import { useAgentStore } from "../stores/agentStore";
import { useConversationStore } from "../stores/conversationStore";
import { agentApi, type SSEEvent } from "../lib/api/agent";
import {
  Send,
  X,
  Loader2,
  FileText,
  Sparkles,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Brain,
  Wrench,
} from "lucide-react";
import DragUploadZone from "../components/DragUploadZone";
import ChatAttachments from "../components/ChatAttachments";
import AgentWorkspace from "../components/AgentWorkspace";
import SubagentBadge from "../components/SubagentBadge";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const ConceptGraphInChat = lazy(() => import("../components/ConceptGraphInChat"));

// 解析消息中的思考过程
function parseThinkingContent(content: string): {
  thinking: string | null;
  response: string;
} {
  // 匹配 <think>...</think> 或 🤔... 格式
  const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/);
  const emojiMatch = content.match(/🤔\s*([\s\S]*?)(?=\n\n|\n[^\s]|$)/);

  if (thinkMatch) {
    return {
      thinking: thinkMatch[1].trim(),
      response: content.replace(/<think>[\s\S]*?<\/think>/, "").trim(),
    };
  }

  if (emojiMatch) {
    return {
      thinking: emojiMatch[1].trim(),
      response: content.replace(/🤔\s*[\s\S]*?(?=\n\n|\n[^#*-])/gm, "").trim(),
    };
  }

  return { thinking: null, response: content };
}

// 可折叠的思考组件
function ThinkingBlock({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="mb-3 rounded-lg overflow-hidden"
      style={{
        background: "rgba(139, 69, 19, 0.05)",
        border: "1px solid rgba(139, 69, 19, 0.15)",
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center gap-2 text-sm transition-colors hover:bg-amber/5"
        style={{ color: "var(--color-ink-secondary)" }}
      >
        <Brain className="w-4 h-4" style={{ color: "var(--color-accent)" }} />
        <span className="font-body">思考过程</span>
        {expanded ? (
          <ChevronUp className="w-4 h-4 ml-auto" />
        ) : (
          <ChevronDown className="w-4 h-4 ml-auto" />
        )}
      </button>
      {expanded && (
        <div
          className="px-3 py-2 text-sm border-t"
          style={{
            borderColor: "rgba(139, 69, 19, 0.1)",
            color: "var(--color-ink-secondary)",
          }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

// 错误边界组件
class ChatErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: string }
> {
  state = { hasError: false, error: "" };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-full flex items-center justify-center p-8">
          <div
            className="max-w-md p-6 rounded-xl text-center"
            style={{
              background: "rgba(180, 60, 60, 0.05)",
              border: "1px solid rgba(180, 60, 60, 0.2)",
            }}
          >
            <AlertTriangle
              className="w-12 h-12 mx-auto mb-4"
              style={{ color: "#8b4040" }}
            />
            <h2
              className="font-display text-lg mb-2"
              style={{ color: "#8b4040" }}
            >
              渲染出错
            </h2>
            <p
              className="font-body text-sm mb-4"
              style={{ color: "var(--color-ink-secondary)" }}
            >
              {this.state.error || "页面渲染时发生错误"}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-lg text-sm font-medium"
              style={{
                background: "var(--color-accent)",
                color: "var(--color-cream)",
              }}
            >
              刷新页面
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// Agent 徽章配色 - 朱砂印章风格
const AGENT_COLORS: Record<string, string> = {
  lead: "#8b4513",
  citation: "#4a6b8a",
  research: "#2d5a4a",
  deep_research: "#6b4423",
  merge: "#a65d2e",
  paper_qa: "#5c4a3a",
};

const AGENT_LABELS: Record<string, string> = {
  lead: "助手",
  citation: "引用分析",
  research: "研究点",
  deep_research: "深入研究",
  merge: "概念合并",
  paper_qa: "论文问答",
};

export default function Chat() {
  const {
    isLoading,
    toolStatus,
    contextSummary,
    setLoading,
    setToolStatus,
    updateContext,
    addUploadedPapers,
    setSSEStatus,
  } = useAgentStore();

  const {
    currentConversationId,
    currentMessages: messages,
    addMessage: addMessageToStore,
    updateTitle,
    loadConversations,
    createConversation,
  } = useConversationStore();

  // Load conversations on mount if not already selected
  useEffect(() => {
    const initConversation = async () => {
      // 如果已经有选中的对话，不需要重新加载
      if (currentConversationId) return;

      await loadConversations();
      // 如果有对话历史但不切换，保持空状态等待用户选择
    };

    initConversation().catch((err) => {
      console.error("Failed to load conversations:", err);
    });
  }, [currentConversationId, loadConversations]);

  const [input, setInput] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const streamingContentRef = useRef("");
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount: abort any active stream
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 200) + "px";
    }
  }, [input]);

  // Handle send message
  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");

    // Create conversation if none exists
    let convId = currentConversationId;
    if (!convId) {
      convId = await createConversation();
    }

    // Abort any previous stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    // Add user message to store (and backend)
    await addMessageToStore({ role: "user", content: userMessage });
    setLoading(true);
    setToolStatus(null);
    setSSEStatus("connecting");
    streamingContentRef.current = "";

    // Build history from currentMessages
    const history = messages.map((m) => ({
      role: m.role,
      content: m.content,
      agent: m.agent as
        | "lead"
        | "citation"
        | "research"
        | "deep_research"
        | "paper_qa"
        | "merge"
        | undefined,
    }));

    // Use new agentApi.chatStreamFetch with DeepAgent event handling
    agentApi
      .chatStreamFetch(
        userMessage,
        contextSummary,
        history,
        convId,
        (event: SSEEvent) => {
          if (event.type === "todo" && Array.isArray(event.todos)) {
            useAgentStore.getState().setTodos(event.todos);
          } else if (event.type === "tool_call") {
            useAgentStore.getState().addExecutionStep({
              id: event.id || `${event.name || "tool"}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
              type: "tool_call",
              name: event.name || event.tool || "",
              args: event.args || event.arguments || {},
              subagentName: event.subagentName,
            });
            // Maintain backward-compatible tool status UI
            setToolStatus({
              tool: event.name || event.tool || "",
              label: event.label || event.name || event.tool || "",
              status: "running",
            });
          } else if (event.type === "tool_result") {
            useAgentStore.getState().addExecutionStep({
              id: event.id || `${event.name || "tool"}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
              type: "tool_result",
              name: event.name || event.tool || "",
              result: event.result,
              duration: event.duration,
              subagentName: event.subagentName,
            });
          } else if (event.type === "subagent_start") {
          const current = useAgentStore.getState().activeSubagents;
          const incoming = Array.isArray(event.subagents)
            ? event.subagents
            : [{ name: event.name || "", task: event.task || "", status: "running" as const }];
          useAgentStore.getState().setActiveSubagents([...current, ...incoming]);
        } else if (event.type === "subagent_end") {
          const current = useAgentStore.getState().activeSubagents;
          const endedName = event.name || "";
          useAgentStore.getState().setActiveSubagents(
            current
              .map((s) => (s.name === endedName ? { ...s, status: "completed" as const } : s))
              .filter((s) => s.status === "running" || s.name !== endedName)
          );
        } else if (event.type === "approval_request") {
          useAgentStore.getState().setPendingApproval({
            id: event.id || `approval-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            action: event.action || "",
            message: event.message || "",
          });
        } else if (event.type === "file_op" && Array.isArray(event.files)) {
          useAgentStore.getState().updateVirtualFiles(event.files);
        } else if (event.type === "token" && typeof event.token === "string") {
          streamingContentRef.current += event.token;
        } else if (event.type === "status" && event.status === "completed") {
          // Save accumulated streaming content as assistant message
          const content = streamingContentRef.current.trim();
          if (content) {
            addMessageToStore({
              role: "assistant",
              content,
              agent: "lead",
            }).catch((err) => console.error("Failed to save message:", err));
          }
          setLoading(false);
          setToolStatus(null);
          setSSEStatus("idle");
          streamingContentRef.current = "";

          // Generate title if first message
          const { conversations, currentConversationId } = useConversationStore.getState();
          const currentConv = conversations.find(
            (c) => c.id === currentConversationId
          );
          if (messages.length === 0 && !currentConv?.title) {
            const title =
              userMessage.slice(0, 20).replace(/[？。！.!?]/, "") || "新对话";
            updateTitle(title).catch((err) =>
              console.error("Failed to update title:", err)
            );
            loadConversations().catch((err) =>
              console.error("Failed to load conversations:", err)
            );
          }
        } else if (event.type === "error") {
          const errMsg = event.message || "Unknown error";
          addMessageToStore({
            role: "assistant",
            content: `抱歉，处理请求时遇到问题：${errMsg}`,
          }).catch((err) => console.error("Failed to save message:", err));
          setLoading(false);
          setToolStatus(null);
          setSSEStatus("error");
          streamingContentRef.current = "";
        }
      }, abortControllerRef.current!.signal)
      .catch((err: any) => {
        addMessageToStore({
          role: "assistant",
          content: `抱歉，处理请求时遇到问题：${err?.message || err || "未知错误"}`,
        }).catch((e) => console.error("Failed to save message:", e));
        setLoading(false);
        setToolStatus(null);
        setSSEStatus("error");
        streamingContentRef.current = "";
      });
  }, [
    input,
    isLoading,
    contextSummary,
    messages,
    addMessageToStore,
    updateTitle,
    loadConversations,
    setToolStatus,
    setSSEStatus,
    createConversation,
    setLoading,
    currentConversationId,
  ]);

  // Handle programmatic send from card actions
  const handleCardAction = useCallback((text: string) => {
    setInput(text);
    // Use setTimeout to let state update, then trigger send
    setTimeout(() => {
      const textarea = inputRef.current;
      if (textarea) {
        textarea.focus();
      }
    }, 100);
  }, []);

  // Handle key press
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Handle upload success
  const handleUploadSuccess = useCallback(
    (papers: Array<{ doi: string; title: string }>) => {
      addUploadedPapers(papers);

      // Set the last uploaded paper as current target
      const lastPaper = papers[papers.length - 1];
      updateContext({
        currentTarget: {
          type: "paper",
          id: lastPaper.doi,
          name: lastPaper.title,
        },
      });

      // Generate AI message
      const titles = papers.map((p) => `《${p.title}》`).join("、");
      const message =
        papers.length === 1
          ? `已上传论文${titles}，你可以问我关于这篇论文的问题。`
          : `已上传 ${papers.length} 篇论文：${titles}。你可以问我关于这些论文的问题。`;

      addMessageToStore({
        role: "assistant",
        content:
          message +
          '\n\n默认存放在"全部论文"文件夹，如需移动到其他文件夹请告诉我。',
      }).catch((err) => console.error("Failed to save message:", err));
    },
    [addUploadedPapers, updateContext, addMessageToStore]
  );

  // Handle upload error
  const handleUploadError = useCallback(
    (error: string) => {
      setIsUploading(false);
      addMessageToStore({
        role: "assistant",
        content: `上传失败：${error}`,
      }).catch((err) => console.error("Failed to save message:", err));
    },
    [addMessageToStore]
  );

  // Handle file button upload
  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []).filter(
        (file) => file.type === "application/pdf"
      );

      if (files.length === 0) {
        addMessageToStore({
          role: "assistant",
          content: "请选择 PDF 文件",
        }).catch((err) => console.error("Failed to save message:", err));
        return;
      }

      // Clear input for next selection
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      setIsUploading(true);

      const uploadedPapers: Array<{ doi: string; title: string }> = [];

      for (const file of files) {
        try {
          const res = await papersApi.upload(file);
          if (res.data?.success && res.data?.doi) {
            uploadedPapers.push({
              doi: res.data.doi,
              title: res.data.title || file.name,
            });
          }
        } catch (err: any) {
          console.error(`Upload failed for ${file.name}:`, err);
        }
      }

      setIsUploading(false);

      if (uploadedPapers.length > 0) {
        handleUploadSuccess(uploadedPapers);
      } else {
        handleUploadError("上传失败，请重试");
      }
    },
    [addMessageToStore, handleUploadSuccess, handleUploadError]
  );

  // Context indicator
  const currentTarget = contextSummary.currentTarget;

  return (
    <ChatErrorBoundary>
      <AgentWorkspace>
        <div className="chat-container h-full flex flex-col relative">
          <style>{`
        .markdown-body {
          line-height: 1.6;
          font-size: 0.9rem;
        }
        .markdown-body p {
          margin: 0.5em 0;
        }
        .markdown-body p:first-child {
          margin-top: 0;
        }
        .markdown-body p:last-child {
          margin-bottom: 0;
        }
        .markdown-body strong {
          color: #5a3e28;
        }
        .markdown-body a {
          color: #8B4513;
          text-decoration: underline;
        }
        .markdown-body code {
          background: #F0EDE6;
          padding: 0.15em 0.4em;
          border-radius: 4px;
          font-size: 0.85em;
        }
        .markdown-body pre {
          background: #F0EDE6;
          padding: 12px;
          border-radius: 8px;
          overflow-x: auto;
          margin: 0.5em 0;
        }
        .markdown-body pre code {
          background: none;
          padding: 0;
        }
        .markdown-body table {
          border-collapse: collapse;
          width: 100%;
          margin: 0.5em 0;
          font-size: 0.85rem;
        }
        .markdown-body th, .markdown-body td {
          border: 1px solid #E8E4DC;
          padding: 6px 10px;
          text-align: left;
        }
        .markdown-body th {
          background: #F0EDE6;
          font-weight: 600;
          color: #5a3e28;
        }
        .markdown-body ul, .markdown-body ol {
          padding-left: 1.2em;
          margin: 0.3em 0;
        }
        .markdown-body li {
          margin: 0.2em 0;
        }
        .markdown-body blockquote {
          border-left: 3px solid #D4C4B0;
          padding-left: 12px;
          margin: 0.5em 0;
          color: #6b5d4f;
        }
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {
          margin: 0.8em 0 0.4em 0;
          color: #5a3e28;
        }
        .markdown-body h1 { font-size: 1.3em; }
        .markdown-body h2 { font-size: 1.15em; }
        .markdown-body h3 { font-size: 1.05em; }
      `}</style>
          {/* Drag upload zone */}
          <DragUploadZone
            onUploadSuccess={handleUploadSuccess}
            onUploadError={handleUploadError}
          />

          {/* Header - 书卷气息 */}
          <div className="chat-header flex-shrink-0 px-6 py-4">
            <div className="max-w-4xl mx-auto flex items-center justify-between">
              <div>
                <h1
                  className="font-display text-xl font-medium"
                  style={{ color: "var(--color-ink)" }}
                >
                  AI 研究助手
                </h1>
                <p
                  className="font-body text-sm mt-0.5"
                  style={{ color: "var(--color-ink-tertiary)" }}
                >
                  分析论文引用 · 发现研究点 · 深入研究主题
                </p>
              </div>

              {/* Current context indicator - 书签角标 */}
              {currentTarget && (
                <div className="chat-context-badge flex items-center gap-2">
                  <span className="text-sm">
                    {currentTarget.type === "paper" ? "📄" : "💡"}
                  </span>
                  <span
                    className="font-body text-sm"
                    style={{ color: "var(--color-ink-secondary)" }}
                  >
                    {currentTarget.name.length > 25
                      ? currentTarget.name.slice(0, 25) + "..."
                      : currentTarget.name}
                  </span>
                  <button
                    onClick={() =>
                      useAgentStore
                        .getState()
                        .updateContext({ currentTarget: undefined })
                    }
                    className="ml-1 p-0.5 rounded hover:bg-overlay transition-colors"
                    style={{ color: "var(--color-ink-muted)" }}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-4 py-6 relative z-10">
            <div className="max-w-4xl mx-auto space-y-5">
              {messages.length === 0 ? (
                // Welcome message - 卷轴展开动画
                <div className="chat-welcome text-center py-16">
                  <div
                    className="w-20 h-20 mx-auto mb-8 rounded-2xl flex items-center justify-center relative"
                    style={{
                      background:
                        "linear-gradient(135deg, var(--color-accent) 0%, var(--color-amber) 50%, var(--color-copper) 100%)",
                      boxShadow: "0 8px 32px rgba(139, 69, 19, 0.2)",
                    }}
                  >
                    <Sparkles
                      className="w-10 h-10"
                      style={{ color: "var(--color-cream)" }}
                    />
                  </div>
                  <h2
                    className="font-display text-3xl font-medium mb-4"
                    style={{ color: "var(--color-ink)" }}
                  >
                    欢迎使用 AI 研究助手
                  </h2>
                  <p
                    className="font-body text-base mb-10 max-w-md mx-auto"
                    style={{ color: "var(--color-ink-tertiary)" }}
                  >
                    我可以帮你分析论文引用、发现概念研究点、深入研究主题
                  </p>

                  {/* Quick actions - 书签标签风格 */}
                  <div className="flex flex-wrap justify-center gap-3">
                    {[
                      {
                        label: "📄 分析论文引用",
                        prompt: "分析 AgentScope 这篇论文的引用关系",
                      },
                      {
                        label: "💡 发现研究点",
                        prompt: "帮我分析多智能体系统这个概念的研究点",
                      },
                      {
                        label: "🔬 深入研究",
                        prompt: "深入研究 AgentScope 平台架构",
                      },
                    ].map((action, i) => (
                      <button
                        key={i}
                        onClick={() => setInput(action.prompt)}
                        className="chat-quick-action"
                        style={{ animationDelay: `${i * 100}ms` }}
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                // Messages - 印章风格气泡
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={
                        msg.role === "user"
                          ? "w-fit"
                          : "w-[85%] max-w-[800px]"
                      }
                    >
                      {msg.role === "assistant" &&
                        msg.agent &&
                        msg.agent !== "lead" && (
                          <div className="flex items-center gap-2 mb-2">
                            <span
                              className="agent-badge"
                              style={{
                                backgroundColor: AGENT_COLORS[msg.agent] + "12",
                                color: AGENT_COLORS[msg.agent],
                              }}
                            >
                              {AGENT_LABELS[msg.agent] || msg.agent}
                            </span>
                          </div>
                        )}
                      {/* Active subagent badges for assistant messages */}
                      {msg.role === "assistant" && (
                        <div>
                          {useAgentStore
                            .getState()
                            .activeSubagents.filter((s) => s.status === "running")
                            .map((s) => (
                              <SubagentBadge
                                key={s.name}
                                name={s.name}
                                status={s.status}
                              />
                            ))}
                        </div>
                      )}
                      {/* 附件卡片 — 统一渲染 */}
                      {msg.role === "assistant" &&
                        msg.attachments &&
                        msg.attachments.length > 0 && (
                          <ChatAttachments
                            attachments={msg.attachments}
                            onSendMessage={handleCardAction}
                          />
                        )}
                      {/* 向后兼容：旧消息的 conceptData */}
                      {msg.role === "assistant" &&
                        msg.conceptData &&
                        (!msg.attachments || msg.attachments.length === 0) && (
                          <ConceptGraphInChat data={msg.conceptData} />
                        )}
                      {/* 统一消息样式 */}
                      {msg.role === "user" ? (
                        <div
                          className="w-fit max-w-[70%] px-3 py-1.5 prose prose-sm prose-invert max-w-none [&_p]:m-0 [&_p:not(:first-child)]:mt-1.5 [&_ul]:mt-1 [&_ul]:mb-1 [&_ol]:mt-1 [&_ol]:mb-1 [&_li]:my-0.5"
                          style={{
                            background:
                              "linear-gradient(135deg, #5D4037 0%, #6D4C41 100%)",
                            color: "#FAFAF7",
                            borderRadius: "16px 16px 4px 16px",
                            boxShadow: "0 2px 8px rgba(93, 64, 55, 0.25)",
                          }}
                        >
                          <div className="prose-p:text-[#FAFAF7] prose-strong:text-[#FFFFFF] prose-a:text-[#FFD54F] prose-em:text-[#E0E0E0]">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                        </div>
                      ) : (
                        <div
                          className="px-4 py-3"
                          style={{
                            background: "#FAFAF7",
                            color: "#2c1810",
                            borderRadius: "16px 16px 16px 4px",
                            border: "1px solid #E8E4DC",
                            boxShadow: "0 1px 4px rgba(0, 0, 0, 0.04)",
                          }}
                        >
                          <div
                            className="markdown-body"
                            style={{ color: "#2c1810" }}
                          >
                            {(() => {
                              const { thinking, response } = parseThinkingContent(
                                msg.content
                              );
                              return (
                                <>
                                  {thinking && (
                                    <ThinkingBlock content={thinking} />
                                  )}
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {response}
                                  </ReactMarkdown>
                                </>
                              );
                            })()}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}

              {/* Loading indicator - 简洁加载动画 + Tool Status */}
              {isLoading && (
                <div className="flex justify-start">
                  <div
                    className="px-4 py-3"
                    style={{
                      background: "#f5f0e8",
                      borderRadius: "16px",
                      border: "1px solid #d4c4b0",
                      boxShadow: "0 2px 8px rgba(0, 0, 0, 0.05)",
                    }}
                  >
                    {toolStatus && toolStatus.status === "running" ? (
                      <div className="flex items-center gap-2">
                        <Wrench
                          className="w-4 h-4"
                          style={{ color: "var(--color-accent)" }}
                        />
                        <span
                          className="font-body text-sm"
                          style={{ color: "var(--color-ink-secondary)" }}
                        >
                          正在调用：{toolStatus.label}
                          {toolStatus.step && toolStatus.maxSteps && (
                            <span className="ml-1" style={{ opacity: 0.7 }}>
                              （步骤 {toolStatus.step}/{toolStatus.maxSteps}）
                            </span>
                          )}
                        </span>
                        <Loader2
                          className="w-4 h-4 animate-spin"
                          style={{ color: "var(--color-accent)" }}
                        />
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Loader2
                          className="w-4 h-4 animate-spin"
                          style={{ color: "var(--color-accent)" }}
                        />
                        <span
                          className="font-body text-sm"
                          style={{ color: "var(--color-ink-secondary)" }}
                        >
                          思考中...
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area - 印章风格输入框 */}
          <div
            className="flex-shrink-0 px-4 py-4"
            style={{
              background:
                "linear-gradient(180deg, var(--color-base) 0%, var(--color-surface) 100%)",
            }}
          >
            <div className="max-w-4xl mx-auto">
              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                multiple
                onChange={handleFileSelect}
                style={{ display: "none" }}
              />
              <div
                className="flex items-end gap-3"
                style={{
                  background: "#FFFFFF",
                  border: "1px solid var(--color-border)",
                  borderRadius: "24px",
                  boxShadow: "0 2px 12px rgba(139, 69, 19, 0.1)",
                  padding: "20px 24px",
                  minHeight: "80px",
                }}
              >
                {/* Upload button */}
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all"
                  style={{
                    background: "rgba(139, 69, 19, 0.08)",
                    color: "var(--color-ink-secondary)",
                  }}
                  title="上传 PDF"
                >
                  {isUploading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <FileText className="w-5 h-5" />
                  )}
                </button>
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入消息..."
                  rows={1}
                  className="flex-1 font-body text-base resize-none outline-none"
                  style={{
                    color: "var(--color-ink)",
                    background: "transparent",
                    maxHeight: "200px",
                    minHeight: "52px",
                    lineHeight: "1.6",
                  }}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all"
                  style={{
                    background:
                      input.trim() && !isLoading
                        ? "linear-gradient(135deg, #8B4513 0%, #A0522D 100%)"
                        : "rgba(139, 69, 19, 0.1)",
                    color:
                      input.trim() && !isLoading
                        ? "#FFFFFF"
                        : "var(--color-ink-muted)",
                  }}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>

              <div className="mt-2 text-center">
                <span
                  className="font-mono text-xs"
                  style={{ color: "var(--color-ink-muted)" }}
                >
                  Shift + Enter 换行 · Enter 发送
                </span>
              </div>
            </div>
          </div>
        </div>
      </AgentWorkspace>
    </ChatErrorBoundary>
  );
}
