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
    history: AgentMessage[],
    conversationId?: string | null
  ): Promise<AgentChatResponse> => {
    const response = await api.post<AgentChatResponse>("/agent/chat", {
      message,
      context,
      history,
      conversationId,
    });
    return response.data;
  },

  chatStream: (
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[],
    conversationId?: string | null
  ): string => {
    const params = new URLSearchParams({
      message,
      context: JSON.stringify(context),
      history: JSON.stringify(history),
    });
    if (conversationId) {
      params.set("conversationId", conversationId);
    }
    return `/api/agent/chat/stream?${params.toString()}`;
  },

  chatStreamFetch: async (
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[],
    conversationId: string | null | undefined,
    onEvent: (event: { type: string; [key: string]: any }) => void
  ): Promise<void> => {
    const response = await fetch("/api/agent/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, context, history, conversationId }),
    });

    if (!response.ok) {
      throw new Error(`SSE request failed: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
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
};
