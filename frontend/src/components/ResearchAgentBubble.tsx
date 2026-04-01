// frontend/src/components/ResearchAgentBubble.tsx
import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, ChevronUp, ChevronDown, Sparkles } from 'lucide-react'
import { useAgentStore, Message } from '../stores/agentStore'
import { agentApi } from '../lib/api'
import { DeepResearchProgress } from './DeepResearchProgress'

// 静默状态 - 底部长条
function CollapsedBar({ onExpand, messageCount }: { onExpand: () => void; messageCount: number }) {
  return (
    <div
      onClick={onExpand}
      className="fixed z-50 cursor-pointer group"
      style={{
        left: '50%',
        transform: 'translateX(-50%)',
        bottom: '16px',
        width: '600px',
        height: '48px',
        background: 'rgba(250, 248, 245, 0.75)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(184, 134, 11, 0.15)',
        borderRadius: '24px',
        boxShadow: '0 4px 24px rgba(44, 24, 16, 0.06)',
        transition: 'all var(--transition-normal)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 8px 32px rgba(44, 24, 16, 0.1)'
        e.currentTarget.style.borderColor = 'rgba(184, 134, 11, 0.3)'
        e.currentTarget.style.background = 'rgba(250, 248, 245, 0.85)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '0 4px 24px rgba(44, 24, 16, 0.06)'
        e.currentTarget.style.borderColor = 'rgba(184, 134, 11, 0.15)'
        e.currentTarget.style.background = 'rgba(250, 248, 245, 0.75)'
      }}
    >
      <div className="flex items-center justify-between h-full px-5">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, var(--color-amber) 0%, var(--color-gold) 100%)',
            }}
          >
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div className="flex items-baseline gap-3">
            <span className="font-display text-base font-medium" style={{ color: 'var(--color-sepia)' }}>
              Research Assistant
            </span>
            <span className="text-sm" style={{ color: 'var(--color-muted)' }}>
              点击展开对话
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {messageCount > 0 && (
            <span
              className="px-2.5 py-1 rounded-full text-xs font-mono"
              style={{
                background: 'rgba(184, 134, 11, 0.1)',
                color: 'var(--color-amber)',
              }}
            >
              {messageCount} 条消息
            </span>
          )}
          <ChevronUp className="w-5 h-5 group-hover:translate-y-[-2px] transition-transform" style={{ color: 'var(--color-muted)' }} />
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
      className="flex items-center justify-between px-5 py-3 cursor-move select-none"
      style={{
        background: 'rgba(250, 248, 245, 0.6)',
        borderBottom: '1px solid rgba(184, 134, 11, 0.1)',
      }}
      onMouseDown={onMouseDown}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center"
          style={{
            background: 'linear-gradient(135deg, var(--color-amber) 0%, var(--color-gold) 100%)',
          }}
        >
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <span className="font-display text-base font-medium" style={{ color: 'var(--color-sepia)' }}>
          Research Assistant
        </span>
      </div>

      <button
        onClick={onCollapse}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-medium transition-all"
        style={{
          color: 'var(--color-muted)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'rgba(184, 134, 11, 0.08)'
          e.currentTarget.style.color = 'var(--color-sepia)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent'
          e.currentTarget.style.color = 'var(--color-muted)'
        }}
      >
        <span className="text-sm">收起</span>
        <ChevronDown className="w-4 h-4" />
      </button>
    </div>
  )
}

// 消息气泡
function MessageBubble({ msg, isUser }: { msg: Message; isUser: boolean }) {
  return (
    <div
      className={`max-w-[80%] px-4 py-2.5 rounded-medium text-sm ${
        isUser ? 'ml-auto' : 'mr-auto'
      }`}
      style={{
        fontFamily: 'var(--font-body)',
        ...(isUser ? {
          background: 'linear-gradient(135deg, var(--color-amber) 0%, var(--color-gold) 100%)',
          color: 'var(--color-vellum)',
          boxShadow: '0 2px 12px rgba(184, 134, 11, 0.2)',
        } : {
          background: 'rgba(245, 240, 232, 0.8)',
          border: '1px solid rgba(184, 134, 11, 0.12)',
          color: 'var(--color-ink)',
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
      className="flex-1 overflow-y-auto p-4 space-y-3"
      style={{
        background: 'transparent',
        minHeight: '200px',
      }}
    >
      {messages.length === 0 && (
        <div className="text-center py-8">
          <p className="text-base font-medium" style={{ color: 'var(--color-sepia)' }}>研究助手已就绪</p>
          <div className="flex flex-col gap-2 text-sm mt-5" style={{ color: 'var(--color-muted)' }}>
            {['分析论文引用关系', '发现概念研究点', '深入研究主题'].map((item, i) => (
              <div key={i} className="py-1.5 hover:text-sepia transition-colors cursor-pointer">
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
      className="p-4 flex-shrink-0"
      style={{
        background: 'rgba(250, 248, 245, 0.6)',
        borderTop: '1px solid rgba(184, 134, 11, 0.1)',
      }}
    >
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入研究问题..."
          className="input-academic flex-1"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="btn-primary px-5 py-2.5"
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
        x: window.innerWidth / 2 - 300,
        y: 80,
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
        x: Math.max(0, Math.min(e.clientX - dragOffset.x, window.innerWidth - 600)),
        y: Math.max(0, Math.min(e.clientY - dragOffset.y, window.innerHeight - 550)),
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

  // 静默状态 - 长条
  if (!isExpanded) {
    return <CollapsedBar onExpand={() => setIsExpanded(true)} messageCount={messages.length} />
  }

  // 展开状态 - 对话框
  return (
    <div
      ref={dialogRef}
      className="fixed z-50 flex flex-col overflow-hidden animate-slide-up"
      style={{
        width: '600px',
        height: '550px',
        left: position.x || window.innerWidth / 2 - 300,
        top: position.y || 80,
        background: 'rgba(250, 248, 245, 0.75)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(184, 134, 11, 0.15)',
        borderRadius: '20px',
        boxShadow: '0 8px 40px rgba(44, 24, 16, 0.08)',
      }}
    >
      <DialogHeader
        onMouseDown={handleMouseDown}
        onCollapse={() => setIsExpanded(false)}
      />
      <MessageList messages={messages} onResearchComplete={handleResearchComplete} />
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}