// frontend/src/components/ResearchAgentBubble.tsx
import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageCircle, X, Minus, Send, Loader2 } from 'lucide-react'
import { useAgentStore } from '../stores/agentStore'
import { agentApi } from '../lib/api'

// Bubble button (minimized state)
function BubbleButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-br from-amber-600 to-amber-700 rounded-full shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center text-white hover:scale-105 z-50"
      title="打开研究助手"
    >
      <MessageCircle className="w-6 h-6" />
    </button>
  )
}

// Draggable header
function DialogHeader({
  onMinimize,
  onClose,
  onMouseDown,
}: {
  onMinimize: () => void
  onClose: () => void
  onMouseDown: (e: React.MouseEvent) => void
}) {
  return (
    <div
      className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-100 cursor-move rounded-t-2xl"
      onMouseDown={onMouseDown}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">🧠</span>
        <span className="font-medium text-amber-900">研究助手</span>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onMinimize}
          className="w-7 h-7 rounded-full hover:bg-amber-100 flex items-center justify-center text-amber-600 transition-colors"
          title="最小化"
        >
          <Minus className="w-4 h-4" />
        </button>
        <button
          onClick={onClose}
          className="w-7 h-7 rounded-full hover:bg-amber-100 flex items-center justify-center text-amber-600 transition-colors"
          title="关闭"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// Message list
function MessageList({ messages }: { messages: ReturnType<typeof useAgentStore>['messages'] }) {
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div ref={listRef} className="flex-1 overflow-y-auto p-4 space-y-3">
      {messages.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          <p className="text-sm">你好！我是研究助手。</p>
          <p className="text-sm mt-1">你可以问我：</p>
          <ul className="text-sm mt-2 space-y-1 text-gray-600">
            <li>• 分析某篇论文的引用关系</li>
            <li>• 分析某个概念的研究点</li>
            <li>• 深入研究某个主题</li>
          </ul>
        </div>
      )}
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[85%] px-3 py-2 rounded-xl text-sm ${
              msg.role === 'user'
                ? 'bg-amber-500 text-white'
                : 'bg-gray-100 text-gray-800'
            }`}
          >
            {msg.content}
          </div>
        </div>
      ))}
    </div>
  )
}

// Input area
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
    <form onSubmit={handleSubmit} className="p-3 border-t border-gray-100">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入问题..."
          className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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

// Main dialog component
export default function ResearchAgentBubble() {
  const {
    isOpen,
    isMinimized,
    position,
    messages,
    isLoading,
    contextSummary,
    toggleOpen,
    minimize,
    setPosition,
    addMessage,
    setLoading,
    updateContext,
    setCurrentAgent,
  } = useAgentStore()

  const [dragging, setDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const dialogRef = useRef<HTMLDivElement>(null)

  // Handle drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
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
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y,
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

      // Handle streaming or regular response
      if (response.agent) {
        setCurrentAgent(response.agent as any)
      }

      addMessage({
        role: 'assistant',
        content: response.message,
        agent: response.agent as any,
      })

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

  // Show bubble button when minimized
  if (isMinimized || !isOpen) {
    return <BubbleButton onClick={toggleOpen} />
  }

  // Show dialog
  return (
    <div
      ref={dialogRef}
      className="fixed bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl border border-gray-100 flex flex-col z-50"
      style={{
        width: '380px',
        height: '520px',
        left: position.x || undefined,
        top: position.y || undefined,
        right: position.x ? undefined : '24px',
        bottom: position.y ? undefined : '24px',
      }}
    >
      <DialogHeader
        onMinimize={minimize}
        onClose={() => useAgentStore.setState({ isOpen: false })}
        onMouseDown={handleMouseDown}
      />
      <MessageList messages={messages} />
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}