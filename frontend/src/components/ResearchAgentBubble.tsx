// frontend/src/components/ResearchAgentBubble.tsx
import { useState, useRef, useEffect, useCallback } from 'react'
import { X, Send, Loader2, Maximize2, Minimize2, Sparkles } from 'lucide-react'
import { useAgentStore, Message } from '../stores/agentStore'
import { agentApi } from '../lib/api'
import { DeepResearchProgress } from './DeepResearchProgress'

// 科技感头部 - 学术风格
function DialogHeader({
  onMouseDown,
  isExpanded,
  onToggleExpand,
  onClose,
}: {
  onMouseDown: (e: React.MouseEvent) => void
  isExpanded: boolean
  onToggleExpand: () => void
  onClose: () => void
}) {
  return (
    <div
      className="flex items-center justify-between px-4 py-2.5 cursor-move select-none relative"
      style={{
        background: 'linear-gradient(135deg, rgba(184, 134, 11, 0.08) 0%, rgba(212, 160, 18, 0.04) 100%)',
        borderBottom: '1px solid rgba(184, 134, 11, 0.15)',
      }}
      onMouseDown={onMouseDown}
    >
      {/* 流光动画 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute inset-0 opacity-30"
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(212, 160, 18, 0.3), transparent)',
            animation: 'shimmer 3s linear infinite',
            backgroundSize: '200% 100%',
          }}
        />
      </div>

      <div className="flex items-center gap-2.5 relative z-10">
        <div
          className="w-6 h-6 rounded-md flex items-center justify-center"
          style={{
            background: 'linear-gradient(135deg, #b8860b 0%, #d4a012 100%)',
            boxShadow: '0 0 8px rgba(184, 134, 11, 0.3)',
          }}
        >
          <Sparkles className="w-3.5 h-3.5 text-white" />
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="font-display text-base font-semibold text-academic-ink">
            Research Assistant
          </span>
          <span className="text-academic-amber text-[10px] font-mono animate-pulse-soft">●</span>
        </div>
      </div>

      <div className="flex items-center gap-1 relative z-10">
        <button
          onClick={onToggleExpand}
          className="w-7 h-7 rounded-soft flex items-center justify-center text-academic-muted hover:text-academic-sepia hover:bg-academic-amber/10 transition-all"
          title={isExpanded ? "缩小" : "放大"}
        >
          {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
        </button>
        <button
          onClick={onClose}
          className="w-7 h-7 rounded-soft flex items-center justify-center text-academic-muted hover:text-status-error hover:bg-status-error/10 transition-all"
          title="关闭"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}

// 消息气泡
function MessageBubble({ msg, isUser }: { msg: Message; isUser: boolean }) {
  return (
    <div
      className={`max-w-[85%] px-3 py-2 rounded-medium text-sm relative transition-all duration-200 hover:shadow-paper ${
        isUser ? 'ml-auto' : 'mr-auto'
      }`}
      style={{
        fontFamily: '"Source Sans 3", system-ui, sans-serif',
        ...(isUser ? {
          background: 'linear-gradient(135deg, #b8860b 0%, #d4a012 100%)',
          color: '#fffef9',
          boxShadow: '0 2px 8px rgba(184, 134, 11, 0.2)',
        } : {
          background: 'rgba(245, 240, 232, 0.9)',
          border: '1px solid rgba(184, 134, 11, 0.12)',
          color: '#2c1810',
        })
      }}
    >
      {/* 装饰性角标 */}
      {!isUser && (
        <div
          className="absolute -left-1 top-3 w-2 h-2 rotate-45"
          style={{ background: 'rgba(245, 240, 232, 0.9)', borderLeft: '1px solid rgba(184, 134, 11, 0.12)', borderBottom: '1px solid rgba(184, 134, 11, 0.12)' }}
        />
      )}
      <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
    </div>
  )
}

// 消息列表
function MessageList({ messages, onResearchComplete }: { messages: Message[]; onResearchComplete: (sessionId: string, report: string) => void }) {
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div
      ref={listRef}
      className="flex-1 overflow-y-auto p-4 space-y-3"
      style={{
        background: 'linear-gradient(180deg, rgba(250, 248, 245, 0.95) 0%, rgba(245, 240, 232, 0.98) 100%)',
        backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23b8860b\' fill-opacity=\'0.02\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
      }}
    >
      {messages.length === 0 && (
        <div className="text-center py-8 animate-fade-in">
          <div
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-medium mb-4"
            style={{
              background: 'rgba(184, 134, 11, 0.08)',
              border: '1px solid rgba(184, 134, 11, 0.15)',
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-academic-amber animate-pulse" />
            <span className="text-xs font-mono text-academic-sepia">READY</span>
          </div>
          <p className="text-sm text-academic-ink font-medium mb-1">研究助手已就绪</p>
          <p className="text-xs text-academic-muted mb-4">支持以下研究功能</p>
          <div className="flex flex-col gap-2 text-xs text-academic-muted">
            {['分析论文引用关系', '发现概念研究点', '深入研究主题'].map((item, i) => (
              <div
                key={i}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-soft mx-auto hover:bg-academic-amber/5 hover:text-academic-sepia transition-all cursor-pointer"
              >
                <span className="text-academic-gold">→</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {messages.map((msg) => (
        <div key={msg.id} className="animate-slide-up">
          <MessageBubble msg={msg} isUser={msg.role === 'user'} />

          {msg.role === 'assistant' && msg.agent === 'deep_research' && msg.researchSessionId && (
            <div className="mt-2 max-w-[85%]">
              <DeepResearchProgress
                sessionId={msg.researchSessionId}
                onComplete={(report) => onResearchComplete(msg.researchSessionId!, report)}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// 输入区域
function ChatInput({
  onSend,
  isLoading,
}: {
  onSend: (message: string) => void
  isLoading: boolean
}) {
  const [input, setInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSend(input.trim())
      setInput('')
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="p-3 relative"
      style={{
        background: 'rgba(250, 248, 245, 0.98)',
        borderTop: '1px solid rgba(184, 134, 11, 0.1)',
      }}
    >
      <div className="flex items-center gap-2">
        <div className="flex-1 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入研究问题..."
            className="w-full px-3 py-2 rounded-medium text-sm outline-none transition-all focus:ring-2 focus:ring-academic-amber/30"
            style={{
              fontFamily: '"Source Sans 3", system-ui, sans-serif',
              background: 'rgba(245, 240, 232, 0.8)',
              border: '1px solid rgba(184, 134, 11, 0.15)',
              color: '#2c1810',
            }}
            disabled={isLoading}
          />
          {/* 输入框装饰线 */}
          <div
            className="absolute bottom-0 left-3 right-3 h-px opacity-50"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(184, 134, 11, 0.3), transparent)' }}
          />
        </div>
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="px-3 py-2 rounded-medium text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            fontFamily: '"Source Sans 3", system-ui, sans-serif',
            background: 'linear-gradient(135deg, #b8860b 0%, #d4a012 100%)',
            color: '#fffef9',
            boxShadow: input.trim() ? '0 2px 8px rgba(184, 134, 11, 0.25)' : 'none',
          }}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>
    </form>
  )
}

// 主组件 - 学术科技感浮框
export default function ResearchAgentBubble() {
  const {
    isOpen,
    position,
    messages,
    isLoading,
    contextSummary,
    setOpen,
    setPosition,
    addMessage,
    setLoading,
    updateContext,
    setCurrentAgent,
  } = useAgentStore()

  const [dragging, setDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [isExpanded, setIsExpanded] = useState(false)
  const dialogRef = useRef<HTMLDivElement>(null)

  // 初始化位置
  useEffect(() => {
    if (!position.x && !position.y) {
      setPosition({
        x: window.innerWidth / 2 - 200,
        y: window.innerHeight - 380,
      })
    }
  }, [])

  // Handle drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    if (dialogRef.current) {
      const rect = dialogRef.current.getBoundingClientRect()
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      })
      setDragging(true)
    }
  }, [])

  useEffect(() => {
    if (!dragging) return

    const handleMouseMove = (e: MouseEvent) => {
      setPosition({
        x: Math.max(0, Math.min(e.clientX - dragOffset.x, window.innerWidth - 350)),
        y: Math.max(0, Math.min(e.clientY - dragOffset.y, window.innerHeight - 200)),
      })
    }

    const handleMouseUp = () => setDragging(false)

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [dragging, dragOffset, setPosition])

  // Send message
  const handleSend = async (message: string) => {
    addMessage({ role: 'user', content: message })
    setLoading(true)

    try {
      const response = await agentApi.chat(message, contextSummary)
      if (response.agent) setCurrentAgent(response.agent as any)

      if (response.researchSessionId) {
        addMessage({
          role: 'assistant',
          content: response.message,
          agent: 'deep_research',
          researchSessionId: response.researchSessionId,
        })
      } else {
        addMessage({
          role: 'assistant',
          content: response.message,
          agent: response.agent as any,
        })
      }

      if (response.contextUpdate) updateContext(response.contextUpdate)
    } catch {
      addMessage({ role: 'assistant', content: '抱歉，处理请求时遇到问题，请稍后重试。' })
    } finally {
      setLoading(false)
    }
  }

  const handleResearchComplete = useCallback((_sessionId: string, report: string) => {
    addMessage({ role: 'assistant', content: report, agent: 'deep_research' })
  }, [addMessage])

  if (!isOpen) return null

  const dialogWidth = isExpanded ? 520 : 400
  const dialogHeight = isExpanded ? 580 : 340

  return (
    <div
      ref={dialogRef}
      className="fixed rounded-large flex flex-col z-50 overflow-hidden animate-fade-in"
      style={{
        width: dialogWidth,
        height: dialogHeight,
        left: position.x || window.innerWidth / 2 - 200,
        top: position.y || window.innerHeight - 380,
        background: 'rgba(250, 248, 245, 0.92)',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 32px rgba(44, 24, 16, 0.12), 0 2px 8px rgba(44, 24, 16, 0.08)',
        border: '1px solid rgba(184, 134, 11, 0.12)',
      }}
    >
      {/* 装饰性角标 */}
      <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-academic-amber/30 rounded-tl-large pointer-events-none" />
      <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-academic-amber/30 rounded-tr-large pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-academic-amber/30 rounded-bl-large pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-academic-amber/30 rounded-br-large pointer-events-none" />

      {/* 发光边缘效果 */}
      <div
        className="absolute inset-0 rounded-large pointer-events-none"
        style={{
          background: 'linear-gradient(135deg, rgba(184, 134, 11, 0.05) 0%, transparent 50%, rgba(212, 160, 18, 0.03) 100%)',
        }}
      />

      <DialogHeader
        onMouseDown={handleMouseDown}
        isExpanded={isExpanded}
        onToggleExpand={() => setIsExpanded(!isExpanded)}
        onClose={() => setOpen(false)}
      />
      <MessageList messages={messages} onResearchComplete={handleResearchComplete} />
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}