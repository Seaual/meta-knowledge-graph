// frontend/src/components/ResearchAgentBubble.tsx
import { useState, useRef, useEffect, useCallback } from 'react'
import { X, Send, Loader2, Maximize2, Minimize2 } from 'lucide-react'
import { useAgentStore, Message } from '../stores/agentStore'
import { agentApi } from '../lib/api'
import { DeepResearchProgress } from './DeepResearchProgress'

// 可拖动的头部
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
      className="flex items-center justify-between px-4 py-2 bg-white/40 backdrop-blur-md border-b border-white/30 cursor-move rounded-t-2xl select-none"
      onMouseDown={onMouseDown}
    >
      <div className="flex items-center gap-2">
        <span className="text-base">🧠</span>
        <span className="font-medium text-gray-600 text-sm">研究助手</span>
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={onToggleExpand}
          className="w-6 h-6 rounded-full hover:bg-white/50 flex items-center justify-center text-gray-500 transition-colors"
          title={isExpanded ? "缩小" : "放大"}
        >
          {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
        </button>
        <button
          onClick={onClose}
          className="w-6 h-6 rounded-full hover:bg-white/50 flex items-center justify-center text-gray-500 transition-colors"
          title="关闭"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
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
    <div ref={listRef} className="flex-1 overflow-y-auto p-3 space-y-2">
      {messages.length === 0 && (
        <div className="text-center text-gray-400 py-6">
          <p className="text-xs">你好！我是研究助手。</p>
          <p className="text-xs mt-1">你可以问我：</p>
          <ul className="text-xs mt-2 space-y-0.5 text-gray-400">
            <li>• 分析论文引用关系</li>
            <li>• 分析概念研究点</li>
            <li>• 深入研究主题</li>
          </ul>
        </div>
      )}
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
        >
          <div
            className={`max-w-[85%] px-2.5 py-1.5 rounded-xl text-xs ${
              msg.role === 'user'
                ? 'bg-amber-500/80 text-white'
                : 'bg-white/60 text-gray-700'
            }`}
          >
            <div className="whitespace-pre-wrap">{msg.content}</div>
          </div>
          {msg.role === 'assistant' && msg.agent === 'deep_research' && msg.researchSessionId && (
            <div className="w-full max-w-[85%] mt-2">
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
    <form onSubmit={handleSubmit} className="p-2 border-t border-white/30">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入问题..."
          className="flex-1 px-3 py-1.5 bg-white/40 border border-white/30 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-amber-400/50 backdrop-blur-sm"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="px-3 py-1.5 bg-amber-500/80 text-white rounded-lg text-xs font-medium hover:bg-amber-600/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Send className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
    </form>
  )
}

// 主组件 - 透明对话浮框
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

  // 初始化位置 - 中下方
  useEffect(() => {
    if (!position.x && !position.y) {
      setPosition({
        x: window.innerWidth / 2 - 175,
        y: window.innerHeight - 280,
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

    const handleMouseUp = () => {
      setDragging(false)
    }

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

      if (response.agent) {
        setCurrentAgent(response.agent as any)
      }

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

      if (response.contextUpdate) {
        updateContext(response.contextUpdate)
      }
    } catch (error) {
      addMessage({
        role: 'assistant',
        content: '抱歉，发生了错误，请稍后重试。',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleResearchComplete = useCallback((_sessionId: string, report: string) => {
    addMessage({
      role: 'assistant',
      content: report,
      agent: 'deep_research',
    })
  }, [addMessage])

  // 默认关闭，用户可以从某个入口打开
  if (!isOpen) {
    return null
  }

  // Dialog size
  const dialogWidth = isExpanded ? 500 : 350
  const dialogHeight = isExpanded ? 550 : 300

  return (
    <div
      ref={dialogRef}
      className="fixed bg-white/30 backdrop-blur-xl rounded-2xl shadow-xl border border-white/40 flex flex-col z-50 overflow-hidden"
      style={{
        width: dialogWidth,
        height: dialogHeight,
        left: position.x || window.innerWidth / 2 - 175,
        top: position.y || window.innerHeight - 280,
      }}
    >
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