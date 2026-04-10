// frontend/src/lib/api/conversations.ts
import api from "./client";
import { getOrCreateDeviceId } from "./client";
import type { ChatAttachment } from "../../stores/agentStore";

export interface Conversation {
  id: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  attachments?: ChatAttachment[];
  conceptData?: any;
  created_at?: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export const conversationsApi = {
  create: async (): Promise<Conversation> => {
    const response = await api.post<Conversation>("/conversations");
    return response.data;
  },

  list: async (): Promise<Conversation[]> => {
    const response = await api.get<Conversation[]>("/conversations");
    return response.data;
  },

  get: async (id: string): Promise<ConversationDetail> => {
    const response = await api.get<ConversationDetail>(`/conversations/${id}`);
    return response.data;
  },

  updateTitle: async (id: string, title: string): Promise<void> => {
    await api.put(`/conversations/${id}/title`, { title });
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/conversations/${id}`);
  },

  addMessage: async (
    convId: string,
    message: {
      role: "user" | "assistant";
      content: string;
      agent?: string;
      attachments?: ChatAttachment[];
    }
  ): Promise<void> => {
    await api.post(`/conversations/${convId}/messages`, message);
  },

  getDeviceId: getOrCreateDeviceId,
};
