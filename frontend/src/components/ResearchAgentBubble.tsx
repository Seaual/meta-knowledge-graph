// frontend/src/components/ResearchAgentBubble.tsx
import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, ChevronLeft, ChevronRight, Sparkles } from 'lucide-react'
import { useAgentStore, Message } from '../stores/agentStore'
import { agentApi } from '../lib/api'
import { DeepResearchProgress } from './DeepResearchProgress'

// 静默状态 - 右侧垂直窄条
function CollapsedBar({ onExpand, messageCount }: { onExpand: () => void; messageCount: number }) {
  return (
    <div
      onClick={onExpand}
      className="fixed z-50 cursor-pointer group"
      style={{
        right: 0,
        top: '50%',
        transform: 'translateY(-50%)',
        width: '48px',
        height: '200px',
        background: 'rgba(250, 248, 245, 0.01)',
        backdropFilter: 'blur(2px)',
        WebkitBackdropFilter: 'blur(2px)',
        border: '1px solid rgba(184, 134, 11, 0.08)',
        borderRight: 'none',
        borderRadius: '20px 0 0 20px',
        boxShadow: '-2px 0 16px rgba(44, 24, 16, 0.02)',
        transition: 'all 0.3s ease-out',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'rgba(250, 248, 245, 0.03)'
        e.currentTarget.style.width = '56px'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'rgba(250, 248, 245, 0.01)'
        e.currentTarget.style.width = '48px'
      }}
    >
      {/* 图标 */}
      <div
        className="w-9 h-9 rounded-full flex items-center justify-center"
        style={{
          background: 'linear-gradient(135deg, var(--color-amber) 0%, var(--color-gold) 100%)',
        }}
      >
        <Sparkles className="w-4 h-4 text-white" />
      </div>

      {/* 垂直文字 */}
      <div
        className="font-display text-xs font-medium writing-vertical"
        style={{
          color: 'var(--color-sepia)',
          writingMode: 'vertical-rl',
          textOrientation: 'mixed',
        }}
      >
        Research
      </div>

      {/* 消息数 */}
      {messageCount > 0 && (
        <span
          className="px-1.5 py-0.5 rounded-full text-[10px] font-mono"
          style={{
            background: 'rgba(184, 134, 11, 0.1)',
            color: 'var(--color-amber)',
          }}
        >
          {messageCount}
        </span>
      )}

      {/* 展开箭头 */}
      <ChevronLeft className="w-4 h-4 group-hover:translate-x-[-2px] transition-transform" style={{ color: 'var(--color-muted)' }} />
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
        background: 'transparent',
        borderBottom: '1px solid rgba(184, 134, 11, 0.06)',
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
        style={{ color: 'var(--color-muted)' }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'rgba(184, 134, 11, 0.06)'
          e.currentTarget.style.color = 'var(--color-sepia)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent'
          e.currentTarget.style.color = 'var(--color-muted)'
        }}
      >
        <span className="text-sm">收起</span>
        <ChevronRight className="w-4 h-4" />
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
          boxShadow: '0 2px 8px rgba(184, 134, 11, 0.1)',
        } : {
          background: 'rgba(245, 240, 232, 0.02)',
          border: '1px solid rgba(184, 134, 11, 0.04)',
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
      style={{ background: 'transparent', minHeight: '200px' }}
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
        background: 'transparent',
        borderTop: '1px solid rgba(184, 134, 11, 0.06)',
      }}
    >
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入研究问题..."
          style={{
            flex: 1,
            padding: '0.75rem 1rem',
            background: 'rgba(245, 240, 232, 0.02)',
            border: '1px solid rgba(184, 134, 11, 0.08)',
            borderRadius: '8px',
            color: 'var(--color-ink)',
            fontFamily: 'var(--font-body)',
            fontSize: '0.9rem',
            outline: 'none',
          }}
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="btn-primary px-5 py-3"
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
  const [dialogPosition, setDialogPosition] = useState({ y: 0 })
  const dragging = useRef(false)
  const dragOffset = useRef({ y: 0 })
  const dialogRef = useRef<HTMLDivElement>(null)

  // 初始化位置 - 垂直居中
  useEffect(() => {
    const y = (window.innerHeight - 550) / 2
    setDialogPosition({ y })
    setPosition({ x: window.innerWidth - 400, y })
  }, [setPosition])

  // Handle drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    if (dialogRef.current && isExpanded) {
      const rect = dialogRef.current.getBoundingClientRect()
      dragOffset.current = {
        y: e.clientY - rect.top,
      }
      dragging.current = true
    }
  }, [isExpanded])

  useEffect(() => {
    if (!dragging.current) return

    const handleMouseMove = (e: MouseEvent) => {
      const newY = Math.max(20, Math.min(e.clientY - dragOffset.current.y, window.innerHeight - 580))
      setDialogPosition({ y: newY })
      setPosition({ x: window.innerWidth - 400, y: newY })
    }

    const handleMouseUp = () => {
      dragging.current = false
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [setPosition])

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

  // 静默状态 - 右侧窄条
  if (!isExpanded) {
    return <CollapsedBar onExpand={() => setIsExpanded(true)} messageCount={messages.length} />
  }

  // 展开状态 - 从右侧滑出
  return (
    <div
      ref={dialogRef}
      className="fixed z-50 flex flex-col overflow-hidden"
      style={{
        width: '380px',
        height: '550px',
        right: 0,
        top: dialogPosition.y,
        background: 'rgba(250, 248, 245, 0.01)',
        backdropFilter: 'blur(2px)',
        WebkitBackdropFilter: 'blur(2px)',
        border: '1px solid rgba(184, 134, 11, 0.08)',
        borderRight: 'none',
        borderRadius: '20px 0 0 20px',
        boxShadow: '-4px 0 32px rgba(44, 24, 16, 0.03)',
        animation: 'slideInRight 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
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
      />
      <MessageList messages={messages} onResearchComplete={handleResearchComplete} />
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}