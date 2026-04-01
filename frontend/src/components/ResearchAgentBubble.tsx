// frontend/src/components/ResearchAgentBubble.tsx
import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, ChevronLeft, ChevronRight, Sparkles } from 'lucide-react'
import { useAgentStore, Message } from '../stores/agentStore'
import { agentApi } from '../lib/api'
import { DeepResearchProgress } from './DeepResearchProgress'

// 静默状态 - 窄条
function CollapsedBar({ onExpand, messageCount }: { onExpand: () => void; messageCount: number }) {
  return (
    <div
      onClick={onExpand}
      className="fixed z-50 cursor-pointer transition-all duration-300 hover:shadow-lg group"
      style={{
        left: '50%',
        transform: 'translateX(-50%)',
        bottom: '24px',
        width: '280px',
        height: '48px',
        background: 'rgba(250, 248, 245, 0.85)',
        backdropFilter: 'blur(12px)',
        borderRadius: '24px',
        border: '1px solid rgba(184, 134, 11, 0.12)',
        boxShadow: '0 4px 20px rgba(44, 24, 16, 0.08)',
      }}
    >
      {/* 渐变光效 */}
      <div
        className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{
          background: 'linear-gradient(135deg, rgba(184, 134, 11, 0.08) 0%, transparent 50%, rgba(212, 160, 18, 0.05) 100%)',
        }}
      />

      <div className="flex items-center justify-between h-full px-4">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #b8860b 0%, #d4a012 100%)',
              boxShadow: '0 2px 8px rgba(184, 134, 11, 0.25)',
            }}
          >
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="font-display text-sm font-medium text-academic-ink">研究助手</span>
        </div>

        <div className="flex items-center gap-2">
          {messageCount > 0 && (
            <span
              className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{
                background: 'rgba(184, 134, 11, 0.1)',
                color: '#b8860b',
              }}
            >
              {messageCount}
            </span>
          )}
          <ChevronLeft className="w-4 h-4 text-academic-muted group-hover:text-academic-amber transition-colors" />
        </div>
      </div>
    </div>
  )
}

// 展开状态头部
function DialogHeader({
  onMouseDown,
  onCollapse,
}: {
  onMouseDown: (e: React.MouseEvent) => void
  onCollapse: () => void
}) {
  return (
    <div
      className="flex items-center justify-between px-4 py-2.5 cursor-move select-none relative"
      style={{
        background: 'linear-gradient(135deg, rgba(184, 134, 11, 0.06) 0%, rgba(212, 160, 18, 0.03) 100%)',
        borderBottom: '1px solid rgba(184, 134, 11, 0.1)',
      }}
      onMouseDown={onMouseDown}
    >
      <div className="flex items-center gap-2.5">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center"
          style={{
            background: 'linear-gradient(135deg, #b8860b 0%, #d4a012 100%)',
          }}
        >
          <Sparkles className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="font-display text-sm font-semibold text-academic-ink">Research Assistant</span>
        <span className="w-1.5 h-1.5 rounded-full bg-academic-amber animate-pulse" />
      </div>

      <button
        onClick={onCollapse}
        className="flex items-center gap-1 px-2 py-1 rounded-soft text-xs text-academic-muted hover:text-academic-sepia hover:bg-academic-amber/10 transition-all"
      >
        <span>收起</span>
        <ChevronRight className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

// 消息气泡
function MessageBubble({ msg, isUser }: { msg: Message; isUser: boolean }) {
  return (
    <div
      className={`max-w-[80%] px-3 py-2 rounded-medium text-sm transition-all duration-200 ${
        isUser ? 'ml-auto' : 'mr-auto'
      }`}
      style={{
        fontFamily: '"Source Sans 3", system-ui, sans-serif',
        ...(isUser ? {
          background: 'linear-gradient(135deg, #b8860b 0%, #d4a012 100%)',
          color: '#fffef9',
          boxShadow: '0 2px 8px rgba(184, 134, 11, 0.15)',
        } : {
          background: 'rgba(245, 240, 232, 0.9)',
          border: '1px solid rgba(184, 134, 11, 0.1)',
          color: '#2c1810',
        })
      }}
    >
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
      className="flex-1 overflow-y-auto p-3 space-y-2.5"
      style={{
        background: 'linear-gradient(180deg, rgba(250, 248, 245, 0.95) 0%, rgba(245, 240, 232, 0.98) 100%)',
      }}
    >
      {messages.length === 0 && (
        <div className="text-center py-6 animate-fade-in">
          <p className="text-sm text-academic-ink font-medium mb-3">研究助手已就绪</p>
          <div className="flex flex-col gap-1.5 text-xs text-academic-muted">
            {['分析论文引用', '发现研究点', '深入研究主题'].map((item, i) => (
              <div key={i} className="py-1 hover:text-academic-sepia transition-colors">
                → {item}
              </div>
            ))}
          </div>
        </div>
      )}

      {messages.map((msg) => (
        <div key={msg.id} className="animate-slide-up">
          <MessageBubble msg={msg} isUser={msg.role === 'user'} />
          {msg.role === 'assistant' && msg.agent === 'deep_research' && msg.researchSessionId && (
            <div className="mt-2 max-w-[80%]">
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
function ChatInput({ onSend, isLoading }: { onSend: (message: string) => void; isLoading: boolean }) {
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
      className="p-3"
      style={{
        background: 'rgba(250, 248, 245, 0.98)',
        borderTop: '1px solid rgba(184, 134, 11, 0.08)',
      }}
    >
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入问题..."
          className="flex-1 px-3 py-2 rounded-medium text-sm outline-none transition-all focus:ring-2 focus:ring-academic-amber/20"
          style={{
            background: 'rgba(245, 240, 232, 0.8)',
            border: '1px solid rgba(184, 134, 11, 0.12)',
            color: '#2c1810',
          }}
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="px-3 py-2 rounded-medium text-sm transition-all disabled:opacity-40"
          style={{
            background: 'linear-gradient(135deg, #b8860b 0%, #d4a012 100%)',
            color: '#fffef9',
          }}
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
    </form>
  )
}

// 主组件
export default function ResearchAgentBubble() {
  const {
    isOpen,
    position,
    messages,
    isLoading,
    contextSummary,
    setPosition,
    addMessage,
    setLoading,
    updateContext,
    setCurrentAgent,
  } = useAgentStore()

  const [isExpanded, setIsExpanded] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const dialogRef = useRef<HTMLDivElement>(null)

  // 初始化位置
  useEffect(() => {
    if (!position.x && !position.y) {
      setPosition({
        x: window.innerWidth / 2 - 180,
        y: window.innerHeight - 480,
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
        x: Math.max(0, Math.min(e.clientX - dragOffset.x, window.innerWidth - 360)),
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
      addMessage({ role: 'assistant', content: '处理请求时遇到问题，请重试。' })
    } finally {
      setLoading(false)
    }
  }

  const handleResearchComplete = useCallback((_sessionId: string, report: string) => {
    addMessage({ role: 'assistant', content: report, agent: 'deep_research' })
  }, [addMessage])

  if (!isOpen) return null

  // 静默状态 - 窄条
  if (!isExpanded) {
    return <CollapsedBar onExpand={() => setIsExpanded(true)} messageCount={messages.length} />
  }

  // 展开状态 - 宽对话框
  return (
    <div
      ref={dialogRef}
      className="fixed z-50 flex flex-col overflow-hidden animate-fade-in"
      style={{
        width: '360px',
        height: '520px',
        left: position.x || window.innerWidth / 2 - 180,
        top: position.y || window.innerHeight - 560,
        background: 'rgba(250, 248, 245, 0.88)',
        backdropFilter: 'blur(16px)',
        borderRadius: '16px',
        border: '1px solid rgba(184, 134, 11, 0.1)',
        boxShadow: '0 8px 32px rgba(44, 24, 16, 0.1)',
        // 边缘透明渐变
        maskImage: 'linear-gradient(white, white)',
        WebkitMaskImage: 'linear-gradient(white, white)',
      }}
    >
      {/* 边缘透明效果 */}
      <div
        className="absolute inset-0 rounded-2xl pointer-events-none"
        style={{
          background: `
            linear-gradient(180deg, rgba(184, 134, 11, 0.03) 0%, transparent 20%, transparent 80%, rgba(184, 134, 11, 0.02) 100%),
            linear-gradient(90deg, rgba(184, 134, 11, 0.02) 0%, transparent 15%, transparent 85%, rgba(184, 134, 11, 0.02) 100%)
          `,
        }}
      />

      <DialogHeader
        onMouseDown={handleMouseDown}
        onCollapse={() => setIsExpanded(false)}
      />
      <MessageList messages={messages} onResearchComplete={handleResearchComplete} />
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}