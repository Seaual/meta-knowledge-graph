// frontend/src/stores/agentStore.ts
import { create } from "zustand";
import type { SSEStatus } from "../lib/sse/types";

export interface ContextSummary {
  currentTarget?: {
    type: "concept" | "paper";
    id: string;
    name: string;
  };
  uploadedPapers?: Array<{
    doi: string;
    title: string;
  }>;
  contextTags: string[];
  keyFindings: string[];
  intentHistory: string[];
  lastActiveAgent:
    | "lead"
    | "citation"
    | "research"
    | "deep_research"
    | "paper_qa";
}

export interface ConceptNode {
  id: string;
  name: string;
  text_en?: string;
  category?: string;
  paper_count: number;
  children?: ConceptNode[];
  parents?: ConceptNode[];
}

export interface ChatAttachment {
  type:
    | "research_points"
    | "paper_detail"
    | "paper_list"
    | "concept_graph"
    | "recommendation"
    | "citation_analysis";
  data: any;
}

export interface TodoItem {
  id: string;
  title: string;
  status: "pending" | "running" | "completed" | "failed";
  detail?: string;
  toolName?: string;
  timestamp: number;
}

export interface ExecutionStep {
  id: string;
  type: "tool_call" | "tool_result" | "subagent_start" | "subagent_end";
  name: string;
  args?: Record<string, any>;
  result?: string;
  duration?: number;
  subagentName?: string;
}

export interface VirtualFile {
  path: string;
  content?: string;
  modifiedAt: number;
}

export interface ActiveSubagent {
  name: string;
  task: string;
  status: "running" | "completed";
}

export interface ApprovalRequest {
  id: string;
  action: string;
  message: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?:
    | "lead"
    | "citation"
    | "research"
    | "deep_research"
    | "merge"
    | "paper_qa";
  researchSessionId?: string;
  conceptData?: ConceptNode;
  attachments?: ChatAttachment[];
  timestamp: number;
}

export interface ToolStatus {
  tool: string;
  label: string;
  status: "idle" | "running" | "completed";
  step?: number;
  maxSteps?: number;
}

interface AgentState {
  isOpen: boolean;
  isMinimized: boolean;
  position: { x: number; y: number };

  messages: Message[];
  currentAgent:
    | "lead"
    | "citation"
    | "research"
    | "deep_research"
    | "merge"
    | "paper_qa";
  contextSummary: ContextSummary;
  isLoading: boolean;

  toolStatus: ToolStatus | null;
  sseStatus: SSEStatus;

  researchSessionId?: string;
  researchProgress: number;
  researchDimensions: string[];

  // DeepAgent state
  todos: TodoItem[];
  executionSteps: ExecutionStep[];
  virtualFiles: VirtualFile[];
  activeSubagents: ActiveSubagent[];
  pendingApproval: ApprovalRequest | null;

  toggleOpen: () => void;
  setOpen: (open: boolean) => void;
  minimize: () => void;
  setPosition: (pos: { x: number; y: number }) => void;

  addMessage: (msg: Omit<Message, "id" | "timestamp">) => void;
  clearMessages: () => void;

  setCurrentAgent: (agent: AgentState["currentAgent"]) => void;
  updateContext: (ctx: Partial<ContextSummary>) => void;
  setLoading: (loading: boolean) => void;

  setToolStatus: (status: ToolStatus | null) => void;
  setSSEStatus: (status: SSEStatus) => void;

  addUploadedPapers: (papers: Array<{ doi: string; title: string }>) => void;
  clearUploadedPapers: () => void;

  setResearchSession: (sessionId: string) => void;
  setResearchProgress: (progress: number, dimensions: string[]) => void;
  resetResearch: () => void;

  // DeepAgent actions
  setTodos: (todos: TodoItem[]) => void;
  addExecutionStep: (step: ExecutionStep) => void;
  updateVirtualFiles: (files: VirtualFile[]) => void;
  setActiveSubagents: (subagents: ActiveSubagent[]) => void;
  setPendingApproval: (req: ApprovalRequest | null) => void;
}

const generateId = () => Math.random().toString(36).substring(2, 9);

export const useAgentStore = create<AgentState>((set) => ({
  isOpen: true,
  isMinimized: false,
  position: { x: 0, y: 0 },

  messages: [],
  currentAgent: "lead",
  contextSummary: {
    contextTags: [],
    keyFindings: [],
    intentHistory: [],
    lastActiveAgent: "lead",
  },
  isLoading: false,

  toolStatus: null,
  sseStatus: "idle",

  researchSessionId: undefined,
  researchProgress: 0,
  researchDimensions: [],

  todos: [],
  executionSteps: [],
  virtualFiles: [],
  activeSubagents: [],
  pendingApproval: null,

  toggleOpen: () =>
    set((state) => ({ isOpen: !state.isOpen, isMinimized: false })),
  setOpen: (open) => set({ isOpen: open }),
  minimize: () => set({ isMinimized: true, isOpen: false }),

  setPosition: (pos) => set({ position: pos }),

  addMessage: (msg) =>
    set((state) => ({
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

  updateContext: (ctx) =>
    set((state) => ({
      contextSummary: { ...state.contextSummary, ...ctx },
    })),

  setLoading: (loading) => set({ isLoading: loading }),

  setToolStatus: (status) => set({ toolStatus: status }),

  setSSEStatus: (status) => set({ sseStatus: status }),

  addUploadedPapers: (papers) =>
    set((state) => ({
      contextSummary: {
        ...state.contextSummary,
        uploadedPapers: [
          ...(state.contextSummary.uploadedPapers || []),
          ...papers,
        ],
      },
    })),

  clearUploadedPapers: () =>
    set((state) => ({
      contextSummary: {
        ...state.contextSummary,
        uploadedPapers: [],
      },
    })),

  setResearchSession: (sessionId) => set({ researchSessionId: sessionId }),

  setResearchProgress: (progress, dimensions) =>
    set({
      researchProgress: progress,
      researchDimensions: dimensions,
    }),

  resetResearch: () =>
    set({
      researchSessionId: undefined,
      researchProgress: 0,
      researchDimensions: [],
    }),

  setTodos: (todos) => set({ todos }),
  addExecutionStep: (step) =>
    set((state) => ({ executionSteps: [...state.executionSteps, step] })),
  updateVirtualFiles: (files) => set({ virtualFiles: files }),
  setActiveSubagents: (activeSubagents) => set({ activeSubagents }),
  setPendingApproval: (pendingApproval) => set({ pendingApproval }),
}));
