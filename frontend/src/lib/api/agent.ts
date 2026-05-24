// frontend/src/lib/api/agent.ts
import api from "./client";

export type AgentType =
  | "lead"
  | "citation"
  | "research"
  | "deep_research"
  | "paper_qa"
  | "merge";

export interface AgentMessage {
  role: "user" | "assistant";
  content: string;
  agent?: AgentType;
}

export interface AgentContextSummary {
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
  lastActiveAgent: AgentType;
}

export interface ConceptGraphData {
  id: string;
  name: string;
  category?: string;
  paper_count: number;
  children?: ConceptGraphData[];
  parents?: ConceptGraphData[];
}

export type AttachmentType =
  | "research_points"
  | "paper_detail"
  | "paper_list"
  | "concept_graph"
  | "recommendation"
  | "citation_analysis";

export interface SSEEvent {
  type:
    | "status"
    | "todo"
    | "tool_call"
    | "tool_result"
    | "file_op"
    | "subagent_start"
    | "subagent_end"
    | "token"
    | "progress"
    | "approval_request"
    | "error";
  [key: string]: any;
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

export interface AgentChatResponse {
  message: string;
  agent: string;
  toolUsed?: string;
  contextUpdate?: Partial<AgentContextSummary>;
  researchSessionId?: string;
  conceptData?: ConceptGraphData;
  attachments?: Array<{ type: AttachmentType; data: any }>;
}

export const agentApi = {
  chat: async (
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[]
  ): Promise<AgentChatResponse> => {
    const response = await api.post<AgentChatResponse>("/agent/chat", {
      message,
      context,
      history,
    });
    return response.data;
  },

  chatStream: (
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[]
  ): string => {
    const params = new URLSearchParams({
      message,
      context: JSON.stringify(context),
      history: JSON.stringify(history),
    });
    return `/api/agent/chat/stream?${params.toString()}`;
  },

  chatStreamFetch: async (
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[],
    conversationId: string | null,
    onEvent: (event: SSEEvent) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const response = await fetch("/api/agent/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, context, history, conversationId }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`SSE request failed: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        if (signal?.aborted) break;
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            try {
              const event = JSON.parse(data);
              onEvent(event);
            } catch (e) {
              console.warn("Failed to parse SSE event:", data);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  startDeepResearch: async (
    targetId: string,
    targetType: "concept" | "paper",
    query: string
  ) => {
    const response = await api.post<{
      sessionId: string;
      status: string;
      report: string;
      dimensions: string[];
    }>("/agent/deep-research/start", {
      targetId,
      targetType,
      query,
    });
    return response.data;
  },

  getResearchStatus: async (sessionId: string) => {
    const response = await api.get<{
      status: string;
      progress: number;
      dimensions: string[];
      completedDimensions: string[];
    }>(`/agent/deep-research/${sessionId}/status`);
    return response.data;
  },

  getResearchReport: async (sessionId: string) => {
    const response = await api.get<{ report: string; format: string }>(
      `/agent/deep-research/${sessionId}/report`
    );
    return response.data;
  },

  approveAction: async (approvalId: string, approved: boolean) => {
    const response = await api.post<{ status: string }>("/agent/approve", {
      approvalId,
      approved,
    });
    return response.data;
  },
};
