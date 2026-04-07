// frontend/src/components/ConversationHistory.tsx
import { useConversationStore } from '../stores/conversationStore'
import { MessageSquare, Trash2 } from 'lucide-react'

interface ConversationHistoryProps {
  onSelect?: () => void
}

export default function ConversationHistory({ onSelect }: ConversationHistoryProps) {
  const {
    conversations,
    currentConversationId,
    isLoadingHistory,
    switchConversation,
    deleteConversation,
  } = useConversationStore()

  const handleSelect = async (id: string) => {
    await switchConversation(id)
    onSelect?.()
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm('确定删除此对话？')) {
      await deleteConversation(id)
    }
  }

  if (isLoadingHistory) {
    return (
      <div className="px-3 py-2">
        <div className="text-xs text-center" style={{ color: 'var(--color-ink-muted)' }}>
          加载中...
        </div>
      </div>
    )
  }

  if (conversations.length === 0) {
    return (
      <div className="px-3 py-2">
        <div className="text-xs text-center" style={{ color: 'var(--color-ink-muted)' }}>
          暂无对话历史
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-2 py-2">
      <div className="text-xs px-2 py-1 mb-2" style={{ color: 'var(--color-ink-muted)' }}>
        对话历史
      </div>
      {conversations.map((conv) => (
        <div
          key={conv.id}
          onClick={() => handleSelect(conv.id)}
          className="flex items-center justify-between rounded-lg px-3 py-2 mb-1 cursor-pointer transition-colors group"
          style={{
            background: conv.id === currentConversationId
              ? 'rgba(139, 69, 19, 0.1)'
              : '#fff',
            borderLeft: conv.id === currentConversationId
              ? '2px solid var(--color-accent)'
              : '1px solid var(--color-border-subtle)',
            opacity: conv.id === currentConversationId ? 1 : 0.85,
          }}
        >
          <div className="flex items-center gap-2 overflow-hidden">
            <MessageSquare className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-ink-muted)' }} />
            <span
              className="font-body text-sm truncate"
              style={{ color: conv.id === currentConversationId ? 'var(--color-ink)' : 'var(--color-ink-secondary)' }}
            >
              {conv.title || '新对话'}
            </span>
          </div>
          <button
            onClick={(e) => handleDelete(conv.id, e)}
            className="p-1 rounded hover:bg-overlay transition-colors opacity-0 group-hover:opacity-100"
            style={{ color: 'var(--color-ink-muted)' }}
            title="删除"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  )
}