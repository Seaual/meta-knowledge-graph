// frontend/src/stores/conversationStore.ts
import { create } from 'zustand'
import { conversationsApi, Conversation, Message } from '../lib/api'

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
      console.log('Loading conversations...')
      const conversations = await conversationsApi.list()
      console.log('Loaded conversations:', conversations)
      set({ conversations, isLoadingHistory: false })
    } catch (err: any) {
      console.error('Failed to load conversations:', err)
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