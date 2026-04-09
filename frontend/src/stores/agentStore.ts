// frontend/src/stores/agentStore.ts
import { create } from 'zustand'
import type { SSEStatus } from '../lib/sse/types'

export interface ContextSummary {
  currentTarget?: {
    type: 'concept' | 'paper'
    id: string
    name: string
  }
  uploadedPapers?: Array<{
    doi: string
    title: string
  }>
  contextTags: string[]
  keyFindings: string[]
  intentHistory: string[]
  lastActiveAgent: 'lead' | 'citation' | 'research' | 'deep_research' | 'paper_qa'
}

// 概念图谱节点数据
export interface ConceptNode {
  id: string
  name: string
  category?: string
  paper_count: number
  children?: ConceptNode[]
  parents?: ConceptNode[]
}

// 统一附件类型
export interface ChatAttachment {
  type: 'research_points' | 'paper_detail' | 'paper_list' | 'concept_graph' | 'recommendation' | 'citation_analysis'
  data: any
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: 'lead' | 'citation' | 'research' | 'deep_research' | 'merge' | 'paper_qa'
  researchSessionId?: string
  conceptData?: ConceptNode  // deprecated，向后兼容
  attachments?: ChatAttachment[]  // 新增：结构化附件
  timestamp: number
}

// Tool Status for SSE streaming
export interface ToolStatus {
  tool: string       // 工具名称 (英文)
  label: string      // 工具名称 (中文)
  status: 'idle' | 'running' | 'completed'
  step?: number      // 当前是第几步
  maxSteps?: number  // 最大步数
}

interface AgentState {
  // UI State
  isOpen: boolean
  isMinimized: boolean
  position: { x: number; y: number }

  // Conversation State
  messages: Message[]
  currentAgent: 'lead' | 'citation' | 'research' | 'deep_research' | 'merge' | 'paper_qa'
  contextSummary: ContextSummary
  isLoading: boolean

  // Tool Status (SSE streaming)
  toolStatus: ToolStatus | null

  // SSE Status (background execution)
  sseStatus: SSEStatus

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

  // Tool Status Actions
  setToolStatus: (status: ToolStatus | null) => void

  // SSE Status Action
  setSSEStatus: (status: SSEStatus) => void

  addUploadedPapers: (papers: Array<{ doi: string; title: string }>) => void
  clearUploadedPapers: () => void

  setResearchSession: (sessionId: string) => void
  setResearchProgress: (progress: number, dimensions: string[]) => void
  resetResearch: () => void
}

const generateId = () => Math.random().toString(36).substring(2, 9)

export const useAgentStore = create<AgentState>((set) => ({
  // UI State
  isOpen: true,  // 默认显示透明浮框
  isMinimized: false,
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

  // Tool Status
  toolStatus: null,

  // SSE Status
  sseStatus: 'idle',

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

  // Tool Status
  setToolStatus: (status) => set({ toolStatus: status }),

  // SSE Status
  setSSEStatus: (status) => set({ sseStatus: status }),

  addUploadedPapers: (papers) => set((state) => ({
    contextSummary: {
      ...state.contextSummary,
      uploadedPapers: [...(state.contextSummary.uploadedPapers || []), ...papers],
    },
  })),

  clearUploadedPapers: () => set((state) => ({
    contextSummary: {
      ...state.contextSummary,
      uploadedPapers: [],
    },
  })),

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