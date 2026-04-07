# Chat History Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add conversation history persistence to Chat page with sidebar list, backend storage, and AI-generated titles.

**Architecture:** SQLite tables for conversations/messages, FastAPI routes for CRUD, Zustand store for frontend state, new sidebar component for history list.

**Tech Stack:** FastAPI, SQLite, Zustand, React, TypeScript

---

## Task 1: Database Schema

**Files:**
- Modify: `mkg/database.py:65-150` (add to _init_tables)

- [ ] **Step 1: Add conversations table to _init_tables**

在 `_init_tables` 方法中添加两张新表。找到 `concept_extractions` 表定义之后的位置插入：

```python
# 对话历史表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,  -- UUID
        device_id TEXT NOT NULL,  -- 设备标识
        title TEXT,  -- AI 生成的标题
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# 对话消息表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_messages (
        id TEXT PRIMARY KEY,  -- UUID
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,  -- 'user' | 'assistant'
        content TEXT NOT NULL,
        agent TEXT,  -- optional, for assistant messages
        attachments TEXT,  -- JSON format
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    )
""")

# 创建索引加速查询
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_conversations_device 
    ON conversations(device_id, updated_at DESC)
""")
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_messages_conversation 
    ON conversation_messages(conversation_id, created_at)
""")
```

- [ ] **Step 2: Run backend to verify tables created**

Run: `cd D:\meta-knowledge-graph-main && python -c "from mkg.database import Database; db = Database('mkg.db'); db.connect(); print('Tables created')"`
Expected: "Tables created"

- [ ] **Step 3: Commit**

```bash
git add mkg/database.py
git commit -m "feat(db): add conversations and messages tables"
```

---

## Task 2: Database Methods for Conversations

**Files:**
- Modify: `mkg/database.py` (add new methods after existing methods)

- [ ] **Step 1: Add conversation CRUD methods to Database class**

在 Database 类末尾添加以下方法：

```python
# ========== Conversation Methods ==========

def create_conversation(self, device_id: str) -> str:
    """创建新对话，返回对话 ID"""
    import uuid
    conv_id = str(uuid.uuid4())
    self.execute_write(
        "INSERT INTO conversations (id, device_id) VALUES (?, ?)",
        (conv_id, device_id)
    )
    return conv_id

def get_conversations(self, device_id: str, limit: int = 50) -> List[Dict]:
    """获取设备的对话列表（按更新时间倒序）"""
    cursor = self.execute_read(
        """SELECT id, title, created_at, updated_at 
           FROM conversations 
           WHERE device_id = ? 
           ORDER BY updated_at DESC 
           LIMIT ?""",
        (device_id, limit)
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

def get_conversation(self, conv_id: str) -> Optional[Dict]:
    """获取单个对话信息"""
    cursor = self.execute_read(
        "SELECT id, device_id, title, created_at, updated_at FROM conversations WHERE id = ?",
        (conv_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None

def update_conversation_title(self, conv_id: str, title: str):
    """更新对话标题"""
    self.execute_write(
        "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, conv_id)
    )

def update_conversation_timestamp(self, conv_id: str):
    """更新对话的 updated_at 时间"""
    self.execute_write(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conv_id,)
    )

def delete_conversation(self, conv_id: str):
    """删除对话（消息会通过 CASCADE 自动删除）"""
    self.execute_write(
        "DELETE FROM conversations WHERE id = ?",
        (conv_id,)
    )

# ========== Message Methods ==========

def add_message(self, conv_id: str, role: str, content: str, agent: Optional[str] = None, attachments: Optional[List] = None):
    """添加消息到对话"""
    import uuid
    msg_id = str(uuid.uuid4())
    attachments_json = json.dumps(attachments) if attachments else None
    self.execute_write(
        """INSERT INTO conversation_messages 
           (id, conversation_id, role, content, agent, attachments) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (msg_id, conv_id, role, content, agent, attachments_json)
    )
    # 更新对话时间戳
    self.update_conversation_timestamp(conv_id)

def get_messages(self, conv_id: str) -> List[Dict]:
    """获取对话的所有消息"""
    cursor = self.execute_read(
        """SELECT id, role, content, agent, attachments, created_at 
           FROM conversation_messages 
           WHERE conversation_id = ? 
           ORDER BY created_at ASC""",
        (conv_id,)
    )
    rows = cursor.fetchall()
    messages = []
    for row in rows:
        msg = dict(row)
        if msg['attachments']:
            msg['attachments'] = json.loads(msg['attachments'])
        else:
            msg['attachments'] = None
        messages.append(msg)
    return messages
```

- [ ] **Step 2: Test database methods**

Run: `cd D:\meta-knowledge-graph-main && python -c "
from mkg.database import Database
db = Database('mkg.db')
db.connect()
# Test create
conv_id = db.create_conversation('test-device')
print(f'Created conversation: {conv_id}')
# Test get
convs = db.get_conversations('test-device')
print(f'Conversations: {convs}')
# Test add message
db.add_message(conv_id, 'user', 'Hello')
db.add_message(conv_id, 'assistant', 'Hi there', agent='lead')
msgs = db.get_messages(conv_id)
print(f'Messages: {msgs}')
# Cleanup
db.delete_conversation(conv_id)
print('Test passed!')
"`
Expected: "Test passed!"

- [ ] **Step 3: Commit**

```bash
git add mkg/database.py
git commit -m "feat(db): add conversation and message CRUD methods"
```

---

## Task 3: Backend Schemas

**Files:**
- Modify: `backend/schemas.py` (append at end)

- [ ] **Step 1: Add conversation schemas**

在文件末尾添加：

```python
# Conversation schemas
class ConversationBase(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationCreate(BaseModel):
    device_id: str


class ConversationUpdate(BaseModel):
    title: str


class MessageBase(BaseModel):
    id: str
    role: str  # 'user' | 'assistant'
    content: str
    agent: Optional[str] = None
    attachments: Optional[List[dict]] = None
    created_at: Optional[str] = None


class ConversationDetail(ConversationBase):
    messages: List[MessageBase] = []


class MessageCreate(BaseModel):
    role: str
    content: str
    agent: Optional[str] = None
    attachments: Optional[List[dict]] = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/schemas.py
git commit -m "feat(schemas): add conversation and message schemas"
```

---

## Task 4: Backend API Routes

**Files:**
- Create: `backend/routes/conversations.py`
- Modify: `backend/main.py:16,34` (import and include router)

- [ ] **Step 1: Create conversations route file**

```python
"""
Conversation API routes
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import (
    ConversationBase, ConversationCreate, ConversationUpdate,
    ConversationDetail, MessageBase, MessageCreate
)
from mkg.database import Database

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# Singleton database instance
_db = None


def get_db():
    global _db
    if _db is None:
        db_path = Path(__file__).parent.parent.parent / "mkg.db"
        _db = Database(str(db_path))
        _db.connect()
    return _db


def get_device_id(x_device_id: Optional[str] = Header(None)) -> str:
    """从 Header 获取设备 ID，如果不存在则生成临时 ID"""
    if not x_device_id:
        # 允许无设备 ID 的请求（用于测试）
        return "anonymous"
    return x_device_id


@router.post("", response_model=ConversationBase)
def create_conversation(device_id: str = Header(None, alias="X-Device-ID")):
    """创建新对话"""
    db = get_db()
    if not device_id:
        raise HTTPException(status_code=400, detail="X-Device-ID header required")
    
    conv_id = db.create_conversation(device_id)
    return ConversationBase(id=conv_id, title=None)


@router.get("", response_model=List[ConversationBase])
def list_conversations(device_id: str = Header(None, alias="X-Device-ID")):
    """获取对话列表"""
    db = get_db()
    if not device_id:
        raise HTTPException(status_code=400, detail="X-Device-ID header required")
    
    conversations = db.get_conversations(device_id)
    return [ConversationBase(**c) for c in conversations]


@router.get("/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: str):
    """获取单个对话及其消息"""
    db = get_db()
    
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.get_messages(conv_id)
    return ConversationDetail(
        id=conv['id'],
        title=conv['title'],
        created_at=conv['created_at'],
        updated_at=conv['updated_at'],
        messages=[MessageBase(**m) for m in messages]
    )


@router.put("/{conv_id}/title")
def update_title(conv_id: str, request: ConversationUpdate):
    """更新对话标题"""
    db = get_db()
    
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db.update_conversation_title(conv_id, request.title)
    return {"success": True}


@router.delete("/{conv_id}")
def delete_conversation(conv_id: str):
    """删除对话"""
    db = get_db()
    
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db.delete_conversation(conv_id)
    return {"success": True}


@router.post("/{conv_id}/messages")
def add_message(conv_id: str, request: MessageCreate):
    """添加消息到对话"""
    db = get_db()
    
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db.add_message(
        conv_id,
        request.role,
        request.content,
        request.agent,
        request.attachments
    )
    return {"success": True}
```

- [ ] **Step 2: Register router in main.py**

在 `backend/main.py` 第 16 行添加导入：
```python
from backend.routes import papers, concepts, graph, llm, folders, semantic_scholar, s2, agent, conversations
```

在第 41 行后添加：
```python
app.include_router(conversations.router)
```

- [ ] **Step 3: Test API endpoints**

Run: `cd D:\meta-knowledge-graph-main && python -c "
import requests
# Assuming backend is running, or test via import
from backend.main import app
print('Router registered:', any(r.path.startswith('/api/conversations') for r in app.routes))
"`
Expected: "Router registered: True"

- [ ] **Step 4: Commit**

```bash
git add backend/routes/conversations.py backend/main.py
git commit -m "feat(api): add conversations CRUD endpoints"
```

---

## Task 5: Frontend API Layer

**Files:**
- Modify: `frontend/src/lib/api.ts` (append at end)

- [ ] **Step 1: Add conversation API functions**

在文件末尾添加（在 `export default api` 之前）：

```typescript
// Conversation types
interface Conversation {
  id: string
  title?: string
  created_at?: string
  updated_at?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: string
  attachments?: ChatAttachment[]
  created_at?: string
}

interface ConversationDetail extends Conversation {
  messages: Message[]
}

// Device ID management
const DEVICE_ID_KEY = 'mkg_device_id'

function getOrCreateDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_ID_KEY)
  if (!deviceId) {
    deviceId = crypto.randomUUID()
    localStorage.setItem(DEVICE_ID_KEY, deviceId)
  }
  return deviceId
}

// Add device ID header to all requests
api.interceptors.request.use((config) => {
  const deviceId = getOrCreateDeviceId()
  config.headers['X-Device-ID'] = deviceId
  return config
})

// Conversation API
export const conversationsApi = {
  // Create new conversation
  create: async (): Promise<Conversation> => {
    const response = await api.post<Conversation>('/conversations')
    return response.data
  },

  // List conversations
  list: async (): Promise<Conversation[]> => {
    const response = await api.get<Conversation[]>('/conversations')
    return response.data
  },

  // Get conversation with messages
  get: async (id: string): Promise<ConversationDetail> => {
    const response = await api.get<ConversationDetail>(`/conversations/${id}`)
    return response.data
  },

  // Update title
  updateTitle: async (id: string, title: string): Promise<void> => {
    await api.put(`/conversations/${id}/title`, { title })
  },

  // Delete conversation
  delete: async (id: string): Promise<void> => {
    await api.delete(`/conversations/${id}`)
  },

  // Add message
  addMessage: async (convId: string, message: {
    role: 'user' | 'assistant'
    content: string
    agent?: string
    attachments?: ChatAttachment[]
  }): Promise<void> => {
    await api.post(`/conversations/${convId}/messages`, message)
  },

  // Get device ID
  getDeviceId: getOrCreateDeviceId,
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(api): add frontend conversation API with device ID"
```

---

## Task 6: Frontend Conversation Store

**Files:**
- Create: `frontend/src/stores/conversationStore.ts`

- [ ] **Step 1: Create Zustand store for conversations**

```typescript
// frontend/src/stores/conversationStore.ts
import { create } from 'zustand'
import { conversationsApi, Conversation, ConversationDetail, Message } from '../lib/api'

interface ConversationState {
  // State
  conversations: Conversation[]
  currentConversationId: string | null
  currentMessages: Message[]
  isLoading: boolean
  isLoadingHistory: boolean
  error: string | null

  // Actions
  loadConversations: () => Promise<void>
  createConversation: () => Promise<string>
  switchConversation: (id: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  addMessage: (message: Omit<Message, 'id' | 'created_at'>) => Promise<void>
  updateTitle: (title: string) => Promise<void>
  clearCurrentConversation: () => void
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  // Initial state
  conversations: [],
  currentConversationId: null,
  currentMessages: [],
  isLoading: false,
  isLoadingHistory: false,
  error: null,

  // Load conversation list
  loadConversations: async () => {
    set({ isLoadingHistory: true, error: null })
    try {
      const conversations = await conversationsApi.list()
      set({ conversations, isLoadingHistory: false })
    } catch (err: any) {
      set({ error: err.message, isLoadingHistory: false })
    }
  },

  // Create new conversation
  createConversation: async () => {
    set({ isLoading: true, error: null })
    try {
      const conv = await conversationsApi.create()
      set({
        currentConversationId: conv.id,
        currentMessages: [],
        isLoading: false,
      })
      // Add to list
      const { conversations } = get()
      set({ conversations: [conv, ...conversations] })
      return conv.id
    } catch (err: any) {
      set({ error: err.message, isLoading: false })
      throw err
    }
  },

  // Switch to existing conversation
  switchConversation: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const detail = await conversationsApi.get(id)
      set({
        currentConversationId: id,
        currentMessages: detail.messages,
        isLoading: false,
      })
    } catch (err: any) {
      set({ error: err.message, isLoading: false })
    }
  },

  // Delete conversation
  deleteConversation: async (id: string) => {
    try {
      await conversationsApi.delete(id)
      const { conversations, currentConversationId } = get()
      set({
        conversations: conversations.filter(c => c.id !== id),
        // If deleted current conversation, clear it
        currentConversationId: currentConversationId === id ? null : currentConversationId,
        currentMessages: currentConversationId === id ? [] : get().currentMessages,
      })
    } catch (err: any) {
      set({ error: err.message })
    }
  },

  // Add message to current conversation
  addMessage: async (message) => {
    const { currentConversationId } = get()
    if (!currentConversationId) return

    // Optimistically add to local state
    const tempId = crypto.randomUUID()
    const tempMessage: Message = {
      id: tempId,
      ...message,
      created_at: new Date().toISOString(),
    }
    set({ currentMessages: [...get().currentMessages, tempMessage] })

    try {
      await conversationsApi.addMessage(currentConversationId, message)
    } catch (err: any) {
      // Remove optimistic message on failure
      set({
        currentMessages: get().currentMessages.filter(m => m.id !== tempId),
        error: err.message,
      })
    }
  },

  // Update current conversation title
  updateTitle: async (title: string) => {
    const { currentConversationId, conversations } = get()
    if (!currentConversationId) return

    try {
      await conversationsApi.updateTitle(currentConversationId, title)
      // Update local state
      set({
        conversations: conversations.map(c =>
          c.id === currentConversationId ? { ...c, title } : c
        ),
      })
    } catch (err: any) {
      set({ error: err.message })
    }
  },

  // Clear current conversation (go to new conversation state)
  clearCurrentConversation: () => {
    set({
      currentConversationId: null,
      currentMessages: [],
    })
  },
}))
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/conversationStore.ts
git commit -m "feat(store): add Zustand conversation store"
```

---

## Task 7: ConversationHistory Component

**Files:**
- Create: `frontend/src/components/ConversationHistory.tsx`

- [ ] **Step 1: Create sidebar conversation list component**

```tsx
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
          className="flex items-center justify-between rounded-lg px-3 py-2 mb-1 cursor-pointer transition-colors"
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ConversationHistory.tsx
git commit -m "feat(ui): add ConversationHistory sidebar component"
```

---

## Task 8: Integrate into Sidebar

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Import and add ConversationHistory**

修改 Sidebar.tsx：

1. 添加导入（约第 4-15 行之间）：
```tsx
import ConversationHistory from './ConversationHistory'
import { useConversationStore } from '../stores/conversationStore'
```

2. 在组件内添加 store hook（约第 32 行后）：
```tsx
const { loadConversations, createConversation } = useConversationStore()

// Load conversations on mount
useEffect(() => {
  loadConversations()
}, [loadConversations])
```

3. 替换「新对话」按钮区域（约第 85-99 行），改为：
```tsx
{/* New Chat Button */}
{!isCollapsed && (
  <div className="px-3 pb-3">
    <button
      onClick={async () => {
        await createConversation()
      }}
      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-body text-sm font-medium transition-all"
      style={{
        background: 'var(--color-accent)',
        color: 'white',
      }}
    >
      <Plus className="w-4 h-4" />
      <span>新对话</span>
    </button>
  </div>
)}

{/* Conversation History */}
{!isCollapsed && (
  <ConversationHistory onSelect={() => {
    // Could close mobile sidebar here if needed
  }} />
)}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "feat(ui): integrate ConversationHistory into Sidebar"
```

---

## Task 9: Integrate into Chat Page

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`

- [ ] **Step 1: Replace agentStore with conversationStore for messages**

这是较大的改动，主要变更：

1. 导入新 store（添加到现有导入）：
```tsx
import { useConversationStore } from '../stores/conversationStore'
```

2. 在组件内获取 conversation store 状态（约第 35-44 行附近）：
```tsx
const {
  currentConversationId,
  currentMessages: messages,
  isLoading: isConvLoading,
  addMessage: addMessageToStore,
  updateTitle,
  loadConversations,
  createConversation,
} = useConversationStore()

// Create conversation if none exists
useEffect(() => {
  if (!currentConversationId) {
    createConversation()
  }
}, [currentConversationId, createConversation])
```

3. 修改 handleSend 方法（约第 65-103 行），保存消息到数据库：
```tsx
const handleSend = useCallback(async () => {
  if (!input.trim() || isLoading) return

  const userMessage = input.trim()
  setInput('')
  
  // Add user message to store (and backend)
  await addMessageToStore({ role: 'user', content: userMessage })
  setLoading(true)

  try {
    // Build history from currentMessages (excluding the message we just added)
    const history = messages.map(m => ({
      role: m.role,
      content: m.content,
      agent: m.agent,
    }))

    const response = await agentApi.chat(userMessage, contextSummary, history)

    if (response.agent) {
      setCurrentAgent(response.agent as any)
    }

    // Add assistant message
    await addMessageToStore({
      role: 'assistant',
      content: response.message,
      agent: response.agent as any,
      attachments: response.attachments,
    })

    // Generate title if first message and no title exists
    const { conversations, currentConversationId } = useConversationStore.getState()
    const currentConv = conversations.find(c => c.id === currentConversationId)
    if (messages.length === 0 && !currentConv?.title) {
      // Generate title from first user message (simple: first 20 chars or until first punctuation)
      const title = userMessage.slice(0, 20).replace(/[？。！？.!?]/, '') || '新对话'
      await updateTitle(title)
      await loadConversations()
    }
  } catch (error) {
    console.error('Chat error:', error)
    await addMessageToStore({
      role: 'assistant',
      content: '抱歉，处理请求时遇到问题，请重试。',
    })
  } finally {
    setLoading(false)
  }
}, [input, isLoading, contextSummary, messages, addMessageToStore, updateTitle, loadConversations, setCurrentAgent])
```

4. 更新消息渲染部分（约第 254-344 行），使用 `messages` 来自 conversationStore：
现有代码使用 `messages` 变量名，已通过 `currentMessages: messages` alias 映射，所以渲染代码无需改动。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Chat.tsx
git commit -m "feat(chat): integrate conversation store for message persistence"
```

---

## Task 10: End-to-End Test

**Files:**
- No file changes, verification only

- [ ] **Step 1: Start backend server**

Run: `cd D:\meta-knowledge-graph-main && python -m uvicorn backend.main:app --reload --port 8088`
Expected: Server starts without errors

- [ ] **Step 2: Start frontend**

Run: `cd D:\meta-knowledge-graph-main\frontend && npm run dev`
Expected: Frontend starts, opens in browser

- [ ] **Step 3: Test conversation creation**

Manual test steps:
1. Open Chat page
2. Verify a new conversation is created automatically
3. Send a message
4. Check sidebar shows conversation with auto-generated title
5. Click "新对话" - verify current conversation saved to list
6. Click previous conversation - verify messages load correctly
7. Delete a conversation - verify it's removed

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git status
# If any fixes made:
git add -A
git commit -m "fix: conversation history integration fixes"
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Database tables (conversations, messages) | Task 1 |
| Backend CRUD methods | Task 2 |
| Backend API schemas | Task 3 |
| Backend API endpoints | Task 4 |
| Frontend API with device ID | Task 5 |
| Zustand conversation store | Task 6 |
| ConversationHistory component | Task 7 |
| Sidebar integration | Task 8 |
| Chat page integration | Task 9 |
| Title generation after first message | Task 9 (handleSend) |
| Device identity (localStorage UUID) | Task 5 |
| Flat list display | Task 7 |
| Minimal title-only style | Task 7 |
| End-to-end verification | Task 10 |

All requirements covered.