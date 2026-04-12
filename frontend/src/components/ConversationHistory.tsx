// frontend/src/components/ConversationHistory.tsx
import { useNavigate } from "react-router-dom";
import { useConversationStore } from "../stores/conversationStore";
import { MessageSquare, Trash2 } from "lucide-react";
import { useTranslation } from "../i18n";

interface ConversationHistoryProps {
  onSelect?: () => void;
}

export default function ConversationHistory({
  onSelect,
}: ConversationHistoryProps) {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const {
    conversations,
    currentConversationId,
    isLoadingHistory,
    switchConversation,
    deleteConversation,
  } = useConversationStore();

  const handleSelect = async (id: string) => {
    await switchConversation(id);
    navigate("/chat"); // 跳转到Chat页面
    onSelect?.();
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(t.common.delete)) {
      await deleteConversation(id);
    }
  };

  if (isLoadingHistory) {
    return (
      <div className="px-3 py-2">
        <div
          className="text-xs text-center"
          style={{ color: "var(--color-ink-muted)" }}
        >
          {t.common.loading}
        </div>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="px-3 py-2">
        <div
          className="text-xs text-center"
          style={{ color: "var(--color-ink-muted)" }}
        >
          {t.common.noConversationHistory}
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto px-1 py-1">
      {conversations.map((conv) => (
        <div
          key={conv.id}
          onClick={() => handleSelect(conv.id)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleSelect(conv.id);
            }
          }}
          tabIndex={0}
          role="button"
          aria-current={conv.id === currentConversationId ? "page" : undefined}
          className="flex items-center justify-between rounded-lg px-3 py-2 mb-1 cursor-pointer transition-colors group"
          style={{
            background:
              conv.id === currentConversationId
                ? "rgba(139, 69, 19, 0.1)"
                : "#fff",
            borderLeft:
              conv.id === currentConversationId
                ? "2px solid var(--color-accent)"
                : "1px solid var(--color-border-subtle)",
            opacity: conv.id === currentConversationId ? 1 : 0.85,
          }}
        >
          <div className="flex items-center gap-2 overflow-hidden">
            <MessageSquare
              className="w-4 h-4 flex-shrink-0"
              style={{ color: "var(--color-ink-muted)" }}
            />
            <span
              className="font-body text-sm truncate"
              style={{
                color:
                  conv.id === currentConversationId
                    ? "var(--color-ink)"
                    : "var(--color-ink-secondary)",
              }}
            >
              {conv.title || t.common.newChat}
            </span>
          </div>
          <button
            onClick={(e) => handleDelete(conv.id, e)}
            className="p-1 rounded hover:bg-overlay transition-colors"
            style={{ color: "var(--color-ink-muted)" }}
            title={t.common.delete}
            aria-label="删除此对话"
            type="button"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
