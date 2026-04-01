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
  researchSessionId?: string
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