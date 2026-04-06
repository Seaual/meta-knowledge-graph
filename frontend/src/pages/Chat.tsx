// Chat.tsx - LLM Conversation Page
import { useState, useRef, useEffect, useCallback } from 'react'
import { useAgentStore } from '../stores/agentStore'
import { agentApi } from '../lib/api'
import { Send, X, Loader2, FileText } from 'lucide-react'
import DragUploadZone from '../components/DragUploadZone'
import ConceptGraphInChat from '../components/ConceptGraphInChat'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Agent badge colors
const AGENT_COLORS: Record<string, string> = {
  lead: '#6b4423',
  citation: '#4a6b8a',
  research: '#2d5a27',
  deep_research: '#9a6b3c',
  merge: '#c2410c',
  paper_qa: '#8b5a2b',
}

const AGENT_LABELS: Record<string, string> = {
  lead: '助手',
  citation: '引用分析',
  research: '研究点分析',
  deep_research: '深入研究',
  merge: '概念合并',
  paper_qa: '论文问答',
}

export default function Chat() {
  const {
    messages,
    isLoading,
    contextSummary,
    addMessage,
    setLoading,
    setCurrentAgent,
    updateContext,
    addUploadedPapers,
  } = useAgentStore()

  const [input, setInput] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 200) + 'px'
    }
  }, [input])

  // Handle send message
  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    addMessage({ role: 'user', content: userMessage })
    setLoading(true)

    try {
      // Build history from messages (exclude the current message we just added)
      const history = messages.map(m => ({
        role: m.role,
        content: m.content,
        agent: m.agent,
      }))

      const response = await agentApi.chat(userMessage, contextSummary, history)

      if (response.agent) {
        setCurrentAgent(response.agent as any)
      }

      addMessage({
        role: 'assistant',
        content: response.message,
        agent: response.agent as any,
        conceptData: response.conceptData,  // 传递概念图谱数据
      })
    } catch (error) {
      console.error('Chat error:', error)
      addMessage({
        role: 'assistant',
        content: '抱歉，处理请求时遇到问题，请重试。',
      })
    } finally {
      setLoading(false)
    }
  }, [input, isLoading, contextSummary, messages, addMessage, setLoading, setCurrentAgent])

  // Handle key press
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Handle upload success
  const handleUploadSuccess = useCallback((papers: Array<{ doi: string; title: string }>) => {
    addUploadedPapers(papers)

    // Set the last uploaded paper as current target
    const lastPaper = papers[papers.length - 1]
    updateContext({
      currentTarget: {
        type: 'paper',
        id: lastPaper.doi,
        name: lastPaper.title,
      },
    })

    // Generate AI message
    const titles = papers.map(p => `《${p.title}》`).join('、')
    const message = papers.length === 1
      ? `已上传论文${titles}，你可以问我关于这篇论文的问题。`
      : `已上传 ${papers.length} 篇论文：${titles}。你可以问我关于这些论文的问题。`

    addMessage({
      role: 'assistant',
      content: message + '\n\n默认存放在"全部论文"文件夹，如需移动到其他文件夹请告诉我。',
    })
  }, [addUploadedPapers, updateContext, addMessage])

  // Handle upload error
  const handleUploadError = useCallback((error: string) => {
    setIsUploading(false)
    addMessage({
      role: 'assistant',
      content: `上传失败：${error}`,
    })
  }, [addMessage])

  // Handle file button upload
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []).filter(
      file => file.type === 'application/pdf'
    )

    if (files.length === 0) {
      addMessage({
        role: 'assistant',
        content: '请选择 PDF 文件',
      })
      return
    }

    // Clear input for next selection
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }

    setIsUploading(true)

    // Import papersApi
    const { papersApi } = await import('../lib/api')
    const uploadedPapers: Array<{ doi: string; title: string }> = []

    for (const file of files) {
      try {
        const res = await papersApi.upload(file)
        if (res.data?.success && res.data?.doi) {
          uploadedPapers.push({
            doi: res.data.doi,
            title: res.data.title || file.name,
          })
        }
      } catch (err: any) {
        console.error(`Upload failed for ${file.name}:`, err)
      }
    }

    setIsUploading(false)

    if (uploadedPapers.length > 0) {
      handleUploadSuccess(uploadedPapers)
    } else {
      handleUploadError('上传失败，请重试')
    }
  }, [addMessage, handleUploadSuccess, handleUploadError])

  // Context indicator
  const currentTarget = contextSummary.currentTarget

  return (
    <div className="h-full flex flex-col relative" style={{ background: 'var(--color-cream)' }}>
      {/* Drag upload zone */}
      <DragUploadZone
        onUploadSuccess={handleUploadSuccess}
        onUploadError={handleUploadError}
      />

      {/* Header */}
      <div
        className="flex-shrink-0 px-6 py-4 border-b"
        style={{
          borderColor: 'rgba(184, 134, 11, 0.08)',
          background: 'linear-gradient(180deg, rgba(255,254,249,0.9) 0%, rgba(250,248,245,0.9) 100%)',
        }}
      >
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="font-display text-xl font-medium" style={{ color: 'var(--color-sepia)' }}>
              AI 研究助手
            </h1>
            <p className="font-body text-sm mt-0.5" style={{ color: 'var(--color-muted)' }}>
              分析论文引用、发现研究点、深入研究主题
            </p>
          </div>

          {/* Current context indicator */}
          {currentTarget && (
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
              style={{
                background: 'rgba(184, 134, 11, 0.06)',
                border: '1px solid rgba(184, 134, 11, 0.1)',
              }}
            >
              <span className="text-sm">
                {currentTarget.type === 'paper' ? '📄' : '💡'}
              </span>
              <span className="font-body text-sm" style={{ color: 'var(--color-sepia)' }}>
                {currentTarget.name}
              </span>
              <button
                onClick={() => useAgentStore.getState().updateContext({ currentTarget: undefined })}
                className="ml-1 p-0.5 rounded hover:bg-amber/10 transition-colors"
                style={{ color: 'var(--color-muted)' }}
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 ? (
            // Welcome message
            <div className="text-center py-20">
              <div
                className="w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, var(--color-sepia) 0%, var(--color-copper) 100%)',
                }}
              >
                <span className="text-3xl">🔮</span>
              </div>
              <h2 className="font-display text-2xl font-medium mb-3" style={{ color: 'var(--color-sepia)' }}>
                欢迎使用 AI 研究助手
              </h2>
              <p className="font-body text-base mb-8" style={{ color: 'var(--color-muted)' }}>
                我可以帮你分析论文引用、发现概念研究点、深入研究主题
              </p>

              {/* Quick actions */}
              <div className="flex flex-wrap justify-center gap-3">
                {[
                  { label: '分析论文引用', prompt: '分析 AgentScope 这篇论文的引用关系' },
                  { label: '发现研究点', prompt: '帮我分析多智能体系统这个概念的研究点' },
                  { label: '深入研究', prompt: '深入研究 AgentScope 平台架构' },
                ].map((action, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(action.prompt)}
                    className="px-4 py-2.5 rounded-xl font-body text-sm transition-all"
                    style={{
                      background: 'var(--color-paper)',
                      border: '1px solid rgba(184, 134, 11, 0.12)',
                      color: 'var(--color-sepia)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(184, 134, 11, 0.25)'
                      e.currentTarget.style.background = 'rgba(184, 134, 11, 0.04)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(184, 134, 11, 0.12)'
                      e.currentTarget.style.background = 'var(--color-paper)'
                    }}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            // Messages
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-${msg.role === 'user' ? 'right' : 'left'}`}
              >
                <div
                  className={`max-w-[80%] ${msg.role === 'user' ? 'order-1' : ''}`}
                >
                  {msg.role === 'assistant' && msg.agent && (
                    <div className="flex items-center gap-2 mb-1.5 animate-fade-in">
                      <span
                        className="px-2 py-0.5 rounded-md text-xs font-mono"
                        style={{
                          backgroundColor: AGENT_COLORS[msg.agent] + '15',
                          color: AGENT_COLORS[msg.agent],
                        }}
                      >
                        {AGENT_LABELS[msg.agent] || msg.agent}
                      </span>
                    </div>
                  )}
                  {/* 概念图谱 - 放在消息气泡外面以避免 CSS 干扰 */}
                  {msg.role === 'assistant' && msg.conceptData && (
                    <ConceptGraphInChat
                      data={msg.conceptData}
                    />
                  )}
                  <div
                    className="px-4 py-3 rounded-2xl transition-colors-smooth"
                    style={{
                      backgroundColor: msg.role === 'user'
                        ? 'var(--color-accent)'
                        : 'var(--color-surface)',
                      color: msg.role === 'user'
                        ? 'white'
                        : 'var(--color-ink)',
                      border: msg.role === 'assistant'
                        ? '1px solid var(--color-border-subtle)'
                        : 'none',
                      borderRadius: msg.role === 'user'
                        ? '18px 18px 4px 18px'
                        : '18px 18px 18px 4px',
                    }}
                  >
                    <div className="font-body text-sm leading-relaxed prose prose-sm max-w-none prose-headings:text-sepia prose-headings:font-display prose-p:text-ink prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-code:text-sepia prose-code:bg-paper prose-code:px-1 prose-code:rounded prose-pre:bg-paper prose-pre:border prose-pre:border-academic-border">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start animate-fade-in">
              <div
                className="px-4 py-3 rounded-2xl"
                style={{
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div
        className="flex-shrink-0 px-4 py-4 border-t"
        style={{
          borderColor: 'rgba(184, 134, 11, 0.08)',
          background: 'linear-gradient(180deg, rgba(250,248,245,0.95) 0%, rgba(255,254,249,0.95) 100%)',
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
            style={{ display: 'none' }}
          />
          <div
            className="flex items-end gap-3 px-4 py-3 rounded-2xl"
            style={{
              background: 'var(--color-vellum)',
              border: '1px solid rgba(184, 134, 11, 0.12)',
              boxShadow: '0 2px 8px rgba(44, 24, 16, 0.04)',
            }}
          >
            {/* Upload button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all"
              style={{
                background: 'rgba(184, 134, 11, 0.08)',
                color: 'var(--color-sepia)',
                cursor: isUploading ? 'not-allowed' : 'pointer',
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
              className="flex-1 bg-transparent font-body text-sm resize-none outline-none"
              style={{ color: '#1a1a1a', maxHeight: '200px' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all"
              style={{
                background: input.trim() && !isLoading
                  ? 'linear-gradient(135deg, var(--color-sepia) 0%, var(--color-copper) 100%)'
                  : 'rgba(184, 134, 11, 0.1)',
                color: input.trim() && !isLoading
                  ? 'var(--color-vellum)'
                  : 'var(--color-faint)',
                cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
              }}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>

          <div className="mt-2 text-center">
            <span className="font-mono text-[10px]" style={{ color: 'var(--color-faint)' }}>
              Shift + Enter 换行 · Enter 发送
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}