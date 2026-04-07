// Chat.tsx - LLM Conversation Page
// 墨迹书房风格 - Ink & Study Design

import { useState, useRef, useEffect, useCallback } from 'react'
import { useAgentStore } from '../stores/agentStore'
import { agentApi } from '../lib/api'
import { Send, X, Loader2, FileText, Sparkles } from 'lucide-react'
import DragUploadZone from '../components/DragUploadZone'
import ConceptGraphInChat from '../components/ConceptGraphInChat'
import ChatAttachments from '../components/ChatAttachments'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Agent 徽章配色 - 朱砂印章风格
const AGENT_COLORS: Record<string, string> = {
  lead: '#8b4513',
  citation: '#4a6b8a',
  research: '#2d5a4a',
  deep_research: '#6b4423',
  merge: '#a65d2e',
  paper_qa: '#5c4a3a',
}

const AGENT_LABELS: Record<string, string> = {
  lead: '助手',
  citation: '引用分析',
  research: '研究点',
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
        conceptData: response.conceptData,  // 保留向后兼容
        attachments: response.attachments,  // 新增
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

  // Handle programmatic send from card actions
  const handleCardAction = useCallback((text: string) => {
    setInput(text)
    // Use setTimeout to let state update, then trigger send
    setTimeout(() => {
      const textarea = inputRef.current
      if (textarea) {
        textarea.focus()
      }
    }, 100)
  }, [])

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
    <div className="chat-container h-full flex flex-col relative">
      {/* Drag upload zone */}
      <DragUploadZone
        onUploadSuccess={handleUploadSuccess}
        onUploadError={handleUploadError}
      />

      {/* Header - 书卷气息 */}
      <div className="chat-header flex-shrink-0 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="font-display text-xl font-medium" style={{ color: 'var(--color-ink)' }}>
              AI 研究助手
            </h1>
            <p className="font-body text-sm mt-0.5" style={{ color: 'var(--color-ink-tertiary)' }}>
              分析论文引用 · 发现研究点 · 深入研究主题
            </p>
          </div>

          {/* Current context indicator - 书签角标 */}
          {currentTarget && (
            <div className="chat-context-badge flex items-center gap-2">
              <span className="text-sm">
                {currentTarget.type === 'paper' ? '📄' : '💡'}
              </span>
              <span className="font-body text-sm" style={{ color: 'var(--color-ink-secondary)' }}>
                {currentTarget.name.length > 25 ? currentTarget.name.slice(0, 25) + '...' : currentTarget.name}
              </span>
              <button
                onClick={() => useAgentStore.getState().updateContext({ currentTarget: undefined })}
                className="ml-1 p-0.5 rounded hover:bg-overlay transition-colors"
                style={{ color: 'var(--color-ink-muted)' }}
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
                  background: 'linear-gradient(135deg, var(--color-accent) 0%, var(--color-amber) 50%, var(--color-copper) 100%)',
                  boxShadow: '0 8px 32px rgba(139, 69, 19, 0.2)',
                }}
              >
                <Sparkles className="w-10 h-10" style={{ color: 'var(--color-cream)' }} />
              </div>
              <h2 className="font-display text-3xl font-medium mb-4" style={{ color: 'var(--color-ink)' }}>
                欢迎使用 AI 研究助手
              </h2>
              <p className="font-body text-base mb-10 max-w-md mx-auto" style={{ color: 'var(--color-ink-tertiary)' }}>
                我可以帮你分析论文引用、发现概念研究点、深入研究主题
              </p>

              {/* Quick actions - 书签标签风格 */}
              <div className="flex flex-wrap justify-center gap-3">
                {[
                  { label: '📄 分析论文引用', prompt: '分析 AgentScope 这篇论文的引用关系' },
                  { label: '💡 发现研究点', prompt: '帮我分析多智能体系统这个概念的研究点' },
                  { label: '🔬 深入研究', prompt: '深入研究 AgentScope 平台架构' },
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
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-1' : ''}`}>
                  {msg.role === 'assistant' && msg.agent && (
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className="agent-badge"
                        style={{
                          backgroundColor: AGENT_COLORS[msg.agent] + '12',
                          color: AGENT_COLORS[msg.agent],
                        }}
                      >
                        {AGENT_LABELS[msg.agent] || msg.agent}
                      </span>
                    </div>
                  )}
                  {/* 附件卡片 — 统一渲染 */}
                  {msg.role === 'assistant' && msg.attachments && msg.attachments.length > 0 && (
                    <ChatAttachments
                      attachments={msg.attachments}
                      onSendMessage={handleCardAction}
                    />
                  )}
                  {/* 向后兼容：旧消息的 conceptData */}
                  {msg.role === 'assistant' && msg.conceptData && (!msg.attachments || msg.attachments.length === 0) && (
                    <ConceptGraphInChat data={msg.conceptData} />
                  )}
                  {/* 统一消息样式 */}
                  <div
                    className="px-4 py-3"
                    style={{
                      background: '#f5f0e8',
                      color: '#2c1810',
                      borderRadius: '16px',
                      border: '1px solid #d4c4b0',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
                    }}
                  >
                    <div style={{ color: '#2c1810' }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}

          {/* Loading indicator - 墨水滴落动画 */}
          {isLoading && (
            <div className="flex justify-start">
              <div
                className="chat-bubble-assistant px-4 py-3"
                style={{ background: 'var(--color-surface)' }}
              >
                <div className="typing-indicator-ink">
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

      {/* Input Area - 印章风格输入框 */}
      <div
        className="flex-shrink-0 px-4 py-4"
        style={{ background: 'linear-gradient(180deg, var(--color-base) 0%, var(--color-surface) 100%)' }}
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
            className="flex items-end gap-3"
            style={{
              background: '#FFFFFF',
              border: '1px solid var(--color-border)',
              borderRadius: '24px',
              boxShadow: '0 2px 12px rgba(139, 69, 19, 0.1)',
              padding: '20px 24px',
              minHeight: '80px',
            }}
          >
            {/* Upload button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all"
              style={{
                background: 'rgba(139, 69, 19, 0.08)',
                color: 'var(--color-ink-secondary)',
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
              style={{ color: 'var(--color-ink)', background: 'transparent', maxHeight: '200px', minHeight: '52px', lineHeight: '1.6' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all"
              style={{
                background: input.trim() && !isLoading
                  ? 'linear-gradient(135deg, #8B4513 0%, #A0522D 100%)'
                  : 'rgba(139, 69, 19, 0.1)',
                color: input.trim() && !isLoading ? '#FFFFFF' : 'var(--color-ink-muted)',
              }}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>

          <div className="mt-2 text-center">
            <span className="font-mono text-xs" style={{ color: 'var(--color-ink-muted)' }}>
              Shift + Enter 换行 · Enter 发送
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}