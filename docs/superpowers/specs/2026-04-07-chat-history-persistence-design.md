---
name: chat-history-persistence
description: Chat page content persistence with sidebar conversation history
type: project
---

# Chat History Persistence Design

**Date:** 2026-04-07
**Status:** Approved

## Overview

Add conversation history persistence to the Chat page. When user clicks "New Conversation", current conversation is automatically saved and collapsed into a sidebar list.

## Requirements Summary

| Decision | Choice |
|----------|--------|
| Layout | Built into existing Sidebar |
| Title Generation | AI auto-generate after first message |
| Storage | Backend persistence (database) |
| User Identity | Device ID (no login required) |
| Display | Flat list, sorted by last active time descending |
| Item Info | Minimal - only title shown |
| Architecture | Standalone service (search added later) |

## UI Design

### Sidebar Layout

The conversation history section is added to the existing Sidebar, positioned:
- Below the "New Conversation" button
- Above the bottom navigation icons

### Visual Style

- Current/active conversation: highlighted with accent color border-left
- Other conversations: white background with reduced opacity
- Only title displayed (no timestamp, no message count)

### Interaction Flow

1. User clicks "New Conversation" → current conversation saved to history list
2. First message sent → AI generates title automatically
3. User clicks history item → load that conversation's messages
4. Conversations sorted by `updated_at` descending

## Data Architecture

### Database Schema

```sql
-- conversations table
CREATE TABLE conversations (
  id TEXT PRIMARY KEY,           -- UUID
  device_id TEXT NOT NULL,       -- device identifier
  title TEXT,                    -- AI-generated title
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- messages table (mirrors existing Message interface)
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL,            -- 'user' | 'assistant'
  content TEXT NOT NULL,
  agent TEXT,                    -- optional, for assistant messages
  attachments TEXT,              -- JSON format (ChatAttachment[])
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

### Device Identity

- First visit: generate UUID, store in `localStorage` as `device_id`
- Every API request: include `X-Device-ID` header
- Backend filters conversations by `device_id`

## API Design

### Endpoints

```
POST   /api/conversations              -- Create new conversation
GET    /api/conversations              -- List conversations (ordered by updated_at DESC)
GET    /api/conversations/:id          -- Get conversation with all messages
PUT    /api/conversations/:id/title    -- Update title (called by AI auto-generation)
DELETE /api/conversations/:id          -- Delete conversation

POST   /api/conversations/:id/messages -- Add message (integrate with existing chat flow)
```

### Title Generation

The existing `/api/chat` endpoint will:
1. Check if current conversation has no title
2. After first response, generate title using LLM (short summary of conversation intent)
3. Call `PUT /api/conversations/:id/title` internally

## Frontend Architecture

### New Components

- `ConversationHistory.tsx` — sidebar conversation list component
- `useConversationStore.ts` — Zustand store for conversation state

### Store State

```typescript
interface ConversationState {
  conversations: Conversation[]       // history list
  currentConversationId: string | null
  currentMessages: Message[]
  isLoadingHistory: boolean

  // Actions
  loadConversations: () => Promise<void>
  createConversation: () => Promise<string>
  switchConversation: (id: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
}
```

### Integration Points

1. **Sidebar.tsx** — add ConversationHistory component
2. **Chat.tsx** — use ConversationState instead of agentStore for messages
3. **agentStore.ts** — migrate message handling to ConversationState

## Implementation Phases

### Phase 1: Core Persistence
- Database tables creation
- API endpoints implementation
- Device ID generation
- ConversationHistory component
- Basic sidebar integration

### Phase 2: Title Generation
- Integrate title generation into chat flow
- Handle edge cases (empty messages, failed generation)

### Phase 3: UX Polish
- Loading states
- Error handling
- Delete confirmation
- Empty state when no history

## Out of Scope (Future)

- Search functionality
- Multi-device sync
- User authentication
- Conversation sharing