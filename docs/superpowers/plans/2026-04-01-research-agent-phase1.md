# Research Agent Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundational UI and backend for the research agent, including floating dialog component, Zustand state management, Lead Agent intent recognition, and basic chat API.

**Architecture:** Floating dialog as a global App-level component with Zustand for state management. Backend uses FastAPI SSE for streaming responses. Lead Agent uses LLM to classify user intent and dispatch to appropriate handlers.

**Tech Stack:** React 18, Zustand, TailwindCSS, FastAPI, LiteLLM, Server-Sent Events

---

## File Structure

```
frontend/src/
├── stores/
│   └── agentStore.ts          # Zustand store for agent state
├── components/
│   └── ResearchAgentBubble.tsx  # Floating dialog component
├── lib/
│   └── api.ts                 # Add agentApi (modify existing)

backend/
├── routes/
│   └── agent.py               # New agent API routes
└── schemas.py                 # Add agent schemas (modify existing)

mkg/
└── agent/
    ├── __init__.py
    ├── lead_agent.py          # Lead Agent intent recognition
    └── prompts.py             # Agent prompts
```

---

### Task 1: Add Zustand Dependency

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install Zustand**

```bash
cd frontend && npm install zustand
```

- [ ] **Step 2: Verify installation**

Run: `cd frontend && npm list zustand`
Expected: `zustand@x.x.x`

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add zustand dependency for agent state management"
```

---

### Task 2: Create Agent Zustand Store

**Files:**
- Create: `frontend/src/stores/agentStore.ts`

- [ ] **Step 1: Create the store file**

```typescript
// frontend/src/stores/agentStore.ts
import { create } from 'zustand'

export interface ContextSummary {
  currentTarget?: {
    type: 'concept' | 'paper'
    id: string
    name: string
  }
  contextTags: string[]
  keyFindings: string[]
  intentHistory: string[]
  lastActiveAgent: 'lead' | 'citation' | 'research' | 'deep_research'
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: 'lead' | 'citation' | 'research' | 'deep_research'
  timestamp: number
}

interface AgentState {
  // UI State
  isOpen: boolean
  isMinimized: boolean
  position: { x: number; y: number }

  // Conversation State
  messages: Message[]
  currentAgent: 'lead' | 'citation' | 'research' | 'deep_research'
  contextSummary: ContextSummary
  isLoading: boolean

  // Deep Research State
  researchSessionId?: string
  researchProgress: number
  researchDimensions: string[]

  // Actions
  toggleOpen: () => void
  setOpen: (open: boolean) => void
  minimize: () => void
  setPosition: (pos: { x: number; y: number }) => void

  addMessage: (msg: Omit<Message, 'id' | 'timestamp'>) => void
  clearMessages: () => void

  setCurrentAgent: (agent: AgentState['currentAgent']) => void
  updateContext: (ctx: Partial<ContextSummary>) => void
  setLoading: (loading: boolean) => void

  setResearchSession: (sessionId: string) => void
  setResearchProgress: (progress: number, dimensions: string[]) => void
  resetResearch: () => void
}

const generateId = () => Math.random().toString(36).substring(2, 9)

export const useAgentStore = create<AgentState>((set) => ({
  // UI State
  isOpen: false,
  isMinimized: true,
  position: { x: 0, y: 0 },

  // Conversation State
  messages: [],
  currentAgent: 'lead',
  contextSummary: {
    contextTags: [],
    keyFindings: [],
    intentHistory: [],
    lastActiveAgent: 'lead',
  },
  isLoading: false,

  // Deep Research State
  researchSessionId: undefined,
  researchProgress: 0,
  researchDimensions: [],

  // Actions
  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen, isMinimized: false })),
  setOpen: (open) => set({ isOpen: open }),
  minimize: () => set({ isMinimized: true, isOpen: false }),

  setPosition: (pos) => set({ position: pos }),

  addMessage: (msg) => set((state) => ({
    messages: [
      ...state.messages,
      {
        ...msg,
        id: generateId(),
        timestamp: Date.now(),
      },
    ],
  })),

  clearMessages: () => set({ messages: [] }),

  setCurrentAgent: (agent) => set({ currentAgent: agent }),

  updateContext: (ctx) => set((state) => ({
    contextSummary: { ...state.contextSummary, ...ctx },
  })),

  setLoading: (loading) => set({ isLoading: loading }),

  setResearchSession: (sessionId) => set({ researchSessionId: sessionId }),

  setResearchProgress: (progress, dimensions) => set({
    researchProgress: progress,
    researchDimensions: dimensions,
  }),

  resetResearch: () => set({
    researchSessionId: undefined,
    researchProgress: 0,
    researchDimensions: [],
  }),
}))
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/agentStore.ts
git commit -m "feat: add Zustand store for research agent state"
```

---

### Task 3: Create Floating Dialog Component

**Files:**
- Create: `frontend/src/components/ResearchAgentBubble.tsx`

- [ ] **Step 1: Create the bubble button component**

```typescript
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
        right: position.x || '24px',
        bottom: position.y || '24px',
        left: position.x ? undefined : 'auto',
        top: position.y ? undefined : 'auto',
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ResearchAgentBubble.tsx
git commit -m "feat: add research agent floating dialog component"
```

---

### Task 4: Add Agent API to Frontend

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add agentApi to api.ts**

Add this to the end of `frontend/src/lib/api.ts`:

```typescript
// Agent API types
interface AgentContextSummary {
  currentTarget?: {
    type: 'concept' | 'paper'
    id: string
    name: string
  }
  contextTags: string[]
  keyFindings: string[]
  intentHistory: string[]
  lastActiveAgent: string
}

interface AgentChatResponse {
  message: string
  agent: string
  contextUpdate?: Partial<AgentContextSummary>
  researchSessionId?: string
}

// Agent API
export const agentApi = {
  chat: async (message: string, context: AgentContextSummary): Promise<AgentChatResponse> => {
    const response = await api.post<AgentChatResponse>('/agent/chat', {
      message,
      context,
    })
    return response.data
  },

  startDeepResearch: async (targetId: string, targetType: 'concept' | 'paper', query: string) => {
    const response = await api.post<{ sessionId: string }>('/agent/deep-research/start', {
      targetId,
      targetType,
      query,
    })
    return response.data
  },

  getResearchStatus: async (sessionId: string) => {
    const response = await api.get<{
      status: string
      progress: number
      dimensions: string[]
      completedDimensions: string[]
    }>(`/agent/deep-research/${sessionId}/status`)
    return response.data
  },

  getResearchReport: async (sessionId: string) => {
    const response = await api.get<{ report: string; format: string }>(
      `/agent/deep-research/${sessionId}/report`
    )
    return response.data
  },
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add agent API endpoints to frontend"
```

---

### Task 5: Integrate Component into App

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Import and add component**

Modify `frontend/src/App.tsx`:

```typescript
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Globe } from 'lucide-react'
import Home from './pages/Home'
import Papers from './pages/Papers'
import ConceptsGraph from './pages/ConceptsGraph'
import { useTranslation } from './i18n'
import ResearchAgentBubble from './components/ResearchAgentBubble'  // Add this import

// ... (keep existing NavLink and LanguageSwitcher components unchanged)

function App() {
  const { t } = useTranslation()

  return (
    <BrowserRouter>
      <div className="h-screen flex flex-col overflow-hidden bg-gradient-warm">
        {/* Header - Academic Style */}
        <header className="header-academic flex-shrink-0">
          {/* ... existing header code ... */}
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/papers" element={<Papers />} />
            <Route path="/concepts" element={<ConceptsGraph />} />
          </Routes>
        </main>

        {/* Global Research Agent Bubble */}
        <ResearchAgentBubble />
      </div>
    </BrowserRouter>
  )
}

export default App
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: integrate research agent bubble into app layout"
```

---

### Task 6: Create Agent Backend Schemas

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add agent schemas to backend/schemas.py**

Add these schemas to the end of `backend/schemas.py`:

```python
# Agent schemas
from typing import Optional, List
from pydantic import BaseModel


class ContextSummary(BaseModel):
    currentTarget: Optional[dict] = None
    contextTags: List[str] = []
    keyFindings: List[str] = []
    intentHistory: List[str] = []
    lastActiveAgent: str = 'lead'


class AgentChatRequest(BaseModel):
    message: str
    context: ContextSummary


class AgentChatResponse(BaseModel):
    message: str
    agent: str
    contextUpdate: Optional[dict] = None
    researchSessionId: Optional[str] = None


class DeepResearchStartRequest(BaseModel):
    targetId: str
    targetType: str  # 'concept' | 'paper'
    query: str


class DeepResearchStatusResponse(BaseModel):
    status: str
    progress: int
    dimensions: List[str]
    completedDimensions: List[str]
```

- [ ] **Step 2: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: add agent schemas to backend"
```

---

### Task 7: Create Lead Agent Module

**Files:**
- Create: `mkg/agent/__init__.py`
- Create: `mkg/agent/prompts.py`
- Create: `mkg/agent/lead_agent.py`

- [ ] **Step 1: Create __init__.py**

```python
# mkg/agent/__init__.py
from .lead_agent import LeadAgent

__all__ = ['LeadAgent']
```

- [ ] **Step 2: Create prompts.py**

```python
# mkg/agent/prompts.py

LEAD_AGENT_SYSTEM_PROMPT = """<s>
你是 Meta Knowledge Graph 的研究助手协调器。你的任务是理解用户的意图，并决定应该由哪个专业 Agent 来处理。

可用的 Agent：
1. **citation** - 引用分析 Agent
   - 分析论文的引用和被引用关系
   - 触发词：引用、被引、citation、谁引用了、引用了谁

2. **research** - 研究点分析 Agent
   - 分析概念的研究机会
   - 触发词：研究点、研究方向、研究机会、概念分析

3. **deep_research** - 深入研究 Agent
   - 系统化的深入研究，生成完整报告
   - 触发词：深入研究、系统分析、详细研究、全面分析

4. **lead** - 通用对话
   - 一般性问题、帮助说明、澄清问题
</s>

<task>
分析用户消息，识别意图，返回 JSON 格式的决策。
</task>

<output_format>
返回 JSON：
{
  "intent": "citation | research | deep_research | lead",
  "target_type": "paper | concept | null",
  "target_name": "用户提到的论文或概念名称，如果无法确定则为 null",
  "confidence": 0.0-1.0,
  "reasoning": "简要说明为什么选择这个意图"
}
</output_format>
"""

LEAD_AGENT_INTENT_PROMPT = """用户消息：{message}

当前上下文：
- 正在研究的对象：{current_target}
- 已知的关键发现：{key_findings}

请识别用户意图，返回 JSON。"""
```

- [ ] **Step 3: Create lead_agent.py**

```python
# mkg/agent/lead_agent.py
import json
from typing import Optional, Dict, Any
from .prompts import LEAD_AGENT_SYSTEM_PROMPT, LEAD_AGENT_INTENT_PROMPT


class IntentResult:
    """意图识别结果"""
    def __init__(self, intent: str, target_type: Optional[str], target_name: Optional[str],
                 confidence: float, reasoning: str):
        self.intent = intent
        self.target_type = target_type
        self.target_name = target_name
        self.confidence = confidence
        self.reasoning = reasoning

    @classmethod
    def from_dict(cls, data: dict) -> 'IntentResult':
        return cls(
            intent=data.get('intent', 'lead'),
            target_type=data.get('target_type'),
            target_name=data.get('target_name'),
            confidence=data.get('confidence', 0.5),
            reasoning=data.get('reasoning', '')
        )


class LeadAgent:
    """Lead Agent - 意图识别和任务分发"""

    def __init__(self, llm_client):
        """
        初始化 Lead Agent

        Args:
            llm_client: LLM 客户端（LiteLLMClient 实例）
        """
        self.llm_client = llm_client

    def recognize_intent(self, message: str, context: Dict[str, Any]) -> IntentResult:
        """
        识别用户意图

        Args:
            message: 用户消息
            context: 上下文摘要

        Returns:
            IntentResult: 意图识别结果
        """
        # 构建上下文信息
        current_target = "无"
        if context.get('currentTarget'):
            ct = context['currentTarget']
            current_target = f"{ct.get('type')}: {ct.get('name')}"

        key_findings = "无"
        if context.get('keyFindings'):
            key_findings = "; ".join(context['keyFindings'][:3])

        # 构建提示词
        prompt = LEAD_AGENT_INTENT_PROMPT.format(
            message=message,
            current_target=current_target,
            key_findings=key_findings
        )

        try:
            # 调用 LLM
            response = self.llm_client.generate(LEAD_AGENT_SYSTEM_PROMPT + "\n\n" + prompt)

            # 解析 JSON 响应
            # 处理可能的 markdown 代码块
            response_text = response.strip()
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                start_idx = 1
                end_idx = len(lines)
                if lines[-1].strip() == '```':
                    end_idx = len(lines) - 1
                response_text = '\n'.join(lines[start_idx:end_idx])

            result = json.loads(response_text)
            return IntentResult.from_dict(result)

        except Exception as e:
            # 解析失败，返回默认意图
            return IntentResult(
                intent='lead',
                target_type=None,
                target_name=None,
                confidence=0.0,
                reasoning=f"意图识别失败: {str(e)}"
            )

    def generate_response(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成响应（Lead Agent 的通用对话能力）

        Args:
            message: 用户消息
            context: 上下文摘要

        Returns:
            响应字典
        """
        intent = self.recognize_intent(message, context)

        # 如果是 lead 意图，生成通用响应
        if intent.intent == 'lead':
            response = self._generate_lead_response(message, context, intent)
            return {
                'message': response,
                'agent': 'lead',
                'contextUpdate': None
            }

        # 否则返回意图信息，由路由层分发
        return {
            'message': f"正在为您分析...",
            'agent': intent.intent,
            'intent_result': {
                'intent': intent.intent,
                'target_type': intent.target_type,
                'target_name': intent.target_name,
                'confidence': intent.confidence,
                'reasoning': intent.reasoning
            },
            'contextUpdate': None
        }

    def _generate_lead_response(self, message: str, context: Dict[str, Any],
                                 intent: IntentResult) -> str:
        """生成 Lead Agent 的通用响应"""
        prompt = f"""用户说：{message}

意图分析结果：
- 意图：{intent.intent}
- 目标：{intent.target_name or '未指定'}
- 置信度：{intent.confidence}

请以友好、简洁的方式回复用户（不超过100字）。如果用户想使用特定功能但表述不清，可以引导他们更清楚地说明。"""

        try:
            return self.llm_client.generate(prompt)
        except Exception:
            return "抱歉，我遇到了一些问题。请稍后重试。"
```

- [ ] **Step 4: Commit**

```bash
git add mkg/agent/
git commit -m "feat: add Lead Agent module for intent recognition"
```

---

### Task 8: Create Agent API Route

**Files:**
- Create: `backend/routes/agent.py`

- [ ] **Step 1: Create agent route**

```python
# backend/routes/agent.py
"""
Agent API routes
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import AgentChatRequest, AgentChatResponse
from mkg.database import Database
from mkg.agent.lead_agent import LeadAgent
from mkg.pdf_parser import LiteLLMClient

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Singleton instances
_db = None
_lead_agent = None


def get_db():
    global _db
    if _db is None:
        _db = Database("mkg.db")
        _db.connect()
    return _db


def get_lead_agent():
    global _lead_agent
    if _lead_agent is None:
        db = get_db()
        config = db.get_llm_config()

        llm_client = None
        if config and config.get('providers'):
            provider_config = db.get_active_llm_provider()
            if not provider_config:
                provider_config = config['providers'][0]

            if provider_config:
                llm_client = LiteLLMClient(
                    provider=provider_config.get('provider'),
                    api_key=provider_config.get('api_key'),
                    model=provider_config.get('model'),
                    base_url=provider_config.get('base_url')
                )

        if llm_client:
            _lead_agent = LeadAgent(llm_client)

    return _lead_agent


@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest):
    """
    处理用户对话

    1. Lead Agent 识别意图
    2. 根据意图分发到专业 Agent
    3. 返回响应
    """
    lead_agent = get_lead_agent()

    if not lead_agent:
        raise HTTPException(
            status_code=500,
            detail="LLM 未配置，请先在设置中配置 API Key"
        )

    # 识别意图并生成响应
    context_dict = request.context.model_dump()
    result = lead_agent.generate_response(request.message, context_dict)

    # 如果有意图结果，表示需要分发到专业 Agent
    if 'intent_result' in result:
        intent_result = result['intent_result']

        # TODO: Phase 2-4 实现各专业 Agent
        # 目前返回提示信息
        return AgentChatResponse(
            message=f"我理解您想要{intent_result['reasoning']}。该功能即将上线！",
            agent=intent_result['intent'],
            contextUpdate=None
        )

    return AgentChatResponse(
        message=result['message'],
        agent=result['agent'],
        contextUpdate=result.get('contextUpdate')
    )


@router.post("/deep-research/start")
def start_deep_research(request: BaseModel):
    """启动深入研究任务 - Phase 4 实现"""
    return {"sessionId": "pending", "status": "not_implemented"}


@router.get("/deep-research/{session_id}/status")
def get_research_status(session_id: str):
    """获取研究进度 - Phase 4 实现"""
    return {
        "status": "not_implemented",
        "progress": 0,
        "dimensions": [],
        "completedDimensions": []
    }


@router.get("/deep-research/{session_id}/report")
def get_research_report(session_id: str):
    """获取研究报告 - Phase 4 实现"""
    return {"report": "", "format": "html"}
```

- [ ] **Step 2: Register router in main.py**

Add import and include router in `backend/main.py`:

```python
# Add to imports
from backend.routes import papers, concepts, graph, llm, folders, semantic_scholar, s2, agent

# Add after other include_router calls
app.include_router(agent.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/routes/agent.py backend/main.py
git commit -m "feat: add agent API route with Lead Agent integration"
```

---

### Task 9: Add Database Tables

**Files:**
- Modify: `mkg/database.py`

- [ ] **Step 1: Add agent-related tables in _init_tables method**

Add these table creations to `mkg/database.py` in the `_init_tables` method:

```python
        # Research sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_sessions (
                id TEXT PRIMARY KEY,
                user_query TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                status TEXT DEFAULT 'running',
                dimensions TEXT,
                progress INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                report_path TEXT
            )
        """)

        # Research findings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                dimension TEXT,
                finding TEXT,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES research_sessions(id)
            )
        """)

        # Agent context table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                context_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
```

- [ ] **Step 2: Commit**

```bash
git add mkg/database.py
git commit -m "feat: add database tables for research sessions and agent context"
```

---

### Task 10: Test Integration

**Files:**
- No new files

- [ ] **Step 1: Start backend server**

```bash
cd D:/meta-knowledge-graph-main
python -m uvicorn backend.main:app --port 8088 --reload
```

- [ ] **Step 2: Start frontend dev server**

```bash
cd D:/meta-knowledge-graph-main/frontend
npm run dev
```

- [ ] **Step 3: Verify in browser**

1. Open http://localhost:5173
2. Verify bubble button appears in bottom-right corner
3. Click to open dialog
4. Send a message like "你好"
5. Verify response appears
6. Verify dialog can be dragged by header
7. Verify minimize button works

- [ ] **Step 4: Verify API endpoint**

```bash
curl -X POST http://localhost:8088/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "分析 Transformer 的引用", "context": {"contextTags": [], "keyFindings": [], "intentHistory": [], "lastActiveAgent": "lead"}}'
```

Expected: JSON response with `message`, `agent`, `contextUpdate` fields

---

## Summary

Phase 1 delivers:
- ✅ Floating dialog UI (bubble button → expandable dialog)
- ✅ Zustand state management for agent
- ✅ Lead Agent with intent recognition
- ✅ Basic chat API endpoint
- ✅ Database tables for future phases

Next phases will add:
- Phase 2: Citation Agent
- Phase 3: Research Point Agent
- Phase 4: Deep Research Agent