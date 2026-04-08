# Frontend API 模块化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `lib/api.ts` (675行) 拆分为 14 个按领域组织的小模块。

**Architecture:** 每个 API 领域一个文件，类型定义与 API 方法在同一文件，`index.ts` 重新导出保持向后兼容。

**Tech Stack:** TypeScript, Axios, React

---

## 文件结构

```
frontend/src/lib/api/
├── index.ts          # 重新导出所有模块
├── client.ts         # axios 实例 + 拦截器 + deviceId
├── papers.ts         # papersApi + 类型
├── concepts.ts       # conceptsApi + 类型
├── graph.ts          # graphApi + 类型
├── dedup.ts          # dedupApi + 类型
├── batch.ts          # batchApi + 类型
├── export.ts         # exportApi + 类型
├── llm.ts            # llmApi + 类型
├── s2.ts             # s2Api + recommendationApi + s2PaperApi + 类型
├── citation.ts       # citationApi + 类型
├── folders.ts        # foldersApi + 类型
├── agent.ts          # agentApi + 类型
└── conversations.ts  # conversationsApi + 类型
```

---

## Task 1: 创建目录和 client.ts

**Files:**
- Create: `frontend/src/lib/api/client.ts`

- [ ] **Step 1: 创建 api 目录和 client.ts**

```typescript
// frontend/src/lib/api/client.ts
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

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

export default api
export { getOrCreateDeviceId }
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/lib/api/client.ts
git commit -m "feat(frontend): add api client module with axios instance"
```

---

## Task 2: 创建 papers.ts

**Files:**
- Create: `frontend/src/lib/api/papers.ts`

- [ ] **Step 1: 创建 papers.ts**

```typescript
// frontend/src/lib/api/papers.ts
import api from './client'

export interface PaperContribution {
  node_count: number
  root_concept?: string
}

export interface ProcessSingleResponse {
  success: boolean
  message: string
  concept_tree: any | null
  duration: number
  concepts_count: number
}

export const papersApi = {
  list: (status?: string, folder?: string) => api.get('/papers/', { params: { status, folder } }),
  get: (doi: string) => api.get(`/papers/${encodeURIComponent(doi)}`),
  upload: (file: File, folder?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (folder) formData.append('folder', folder)
    return api.post('/papers/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  process: (doi: string) => api.post('/papers/process', { doi }),
  delete: (doi: string) => api.delete(`/papers/${encodeURIComponent(doi)}`),
  move: (doi: string, folderId: string) => api.patch(`/papers/${encodeURIComponent(doi)}/folder`, { folder_id: folderId }),
  contribution: (doi: string) => api.get(`/papers/${encodeURIComponent(doi)}/contribution`),
  processSingle: (doi: string) => api.post<ProcessSingleResponse>('/papers/process-single', { doi }),
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/lib/api/papers.ts
git commit -m "feat(frontend): add papers API module"
```

---

## Task 3: 创建 concepts.ts 和 graph.ts

**Files:**
- Create: `frontend/src/lib/api/concepts.ts`
- Create: `frontend/src/lib/api/graph.ts`

- [ ] **Step 1: 创建 concepts.ts**

```typescript
// frontend/src/lib/api/concepts.ts
import api from './client'

export const conceptsApi = {
  list: () => api.get('/concepts/'),
  roots: () => api.get('/concepts/roots'),
  tree: (rootId?: string) => api.get('/concepts/tree', { params: { root_id: rootId } }),
  search: (q: string) => api.get('/concepts/search', { params: { q } }),
  get: (id: string) => api.get(`/concepts/${id}`),
  papers: (id: string) => api.get(`/concepts/${id}/papers`),
  researchPoints: (id: string) => api.get(`/concepts/${id}/research-points`),
}
```

- [ ] **Step 2: 创建 graph.ts**

```typescript
// frontend/src/lib/api/graph.ts
import api from './client'

export const graphApi = {
  stats: () => api.get('/graph/stats'),
  data: (folder?: string) => api.get('/graph/data', { params: { folder } }),
  treeData: () => api.get('/graph/tree-data'),
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/lib/api/concepts.ts frontend/src/lib/api/graph.ts
git commit -m "feat(frontend): add concepts and graph API modules"
```

---

## Task 4: 创建 dedup.ts 和 batch.ts

**Files:**
- Create: `frontend/src/lib/api/dedup.ts`
- Create: `frontend/src/lib/api/batch.ts`

- [ ] **Step 1: 创建 dedup.ts**

```typescript
// frontend/src/lib/api/dedup.ts
import api from './client'

export interface MergeSuggestion {
  id: string
  source: { id: string; text: string; paper_count: number }
  target: { id: string; text: string; paper_count: number }
  confidence: number
  rationale: string
}

export interface ExecuteDetail {
  source: string
  target: string
  status: 'success' | 'failed'
  message?: string
}

export interface FloatingConceptDetail {
  concept: string
  parent?: string
  status: 'fixed' | 'skipped' | 'failed'
  reason?: string
}

export interface DedupExecuteResponse {
  executed: number
  details: ExecuteDetail[]
  floating_fixed?: number
  floating_details?: FloatingConceptDetail[]
}

export interface ScanStatusResponse {
  scan_id: string
  status: string
  phase?: 'prefiltering' | 'analyzing' | 'completed' | 'failed'
  total_concepts: number
  concepts_scanned: number
  batches_total?: number
  batches_completed?: number
  filtered_count?: number
  high_confidence_count?: number
  progress: number
  estimated_time: number
  suggestions: MergeSuggestion[] | null
  error?: string
}

export const dedupApi = {
  scan: (folderId?: string) => api.post<{ scan_id: string; total_concepts: number; status: string }>('/concepts/dedup/scan', { folder_id: folderId }),
  scanStatus: (scanId: string) => api.get<ScanStatusResponse>(`/concepts/dedup/scan-status/${scanId}`),
  execute: (scanId: string, mergeIds: string[]) =>
    api.post<DedupExecuteResponse>('/concepts/dedup/execute', {
      scan_id: scanId,
      merge_ids: mergeIds,
    }),
}
```

- [ ] **Step 2: 创建 batch.ts**

```typescript
// frontend/src/lib/api/batch.ts
import api from './client'

export interface BatchUploadResponse {
  job_id: string
  uploaded: Array<{
    doi?: string
    title?: string
    filename: string
    status?: string
    success: boolean
    error?: string
  }>
  total: number
}

export interface BatchProcessResponse {
  job_id: string
  status: string
  total: number
  completed: number
  successful: number
  failed: number
  results: Array<{
    doi: string
    status: string
    concepts?: number
    error?: string
  }>
}

export interface BatchJobStatus {
  id: string
  status: string
  total: number
  completed: number
  successful: number
  failed: number
  created_at?: string
}

export const batchApi = {
  upload: (files: File[]) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return api.post<BatchUploadResponse>('/papers/batch-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  process: (jobId: string, dois: string[]) =>
    api.post<BatchProcessResponse>('/papers/batch-process', { job_id: jobId, dois }),
  status: (jobId: string) =>
    api.get<BatchJobStatus>(`/papers/batch-status/${jobId}`),
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/lib/api/dedup.ts frontend/src/lib/api/batch.ts
git commit -m "feat(frontend): add dedup and batch API modules"
```

---

## Task 5: 创建 export.ts 和 llm.ts

**Files:**
- Create: `frontend/src/lib/api/export.ts`
- Create: `frontend/src/lib/api/llm.ts`

- [ ] **Step 1: 创建 export.ts**

```typescript
// frontend/src/lib/api/export.ts
import api from './client'

export interface ExportResponse {
  content: string
  stats: {
    papers: number
    concepts: number
    generated_at: string
  }
}

export const exportApi = {
  obsidian: (folderId?: string) => api.get<ExportResponse>('/graph/export/obsidian', { params: { folder_id: folderId } }),
  download: (folderId?: string) =>
    api.get('/graph/export/obsidian/download', { params: { folder_id: folderId }, responseType: 'blob' }),
  canvas: (folderId?: string) => api.get('/graph/export/obsidian/canvas', { params: { folder_id: folderId } }),
  downloadCanvas: (folderId?: string) =>
    api.get('/graph/export/obsidian/canvas/download', { params: { folder_id: folderId }, responseType: 'blob' }),
  html: (folderId?: string) => api.get('/graph/export/obsidian/html', { params: { folder_id: folderId } }),
  downloadHtml: (folderId?: string) =>
    api.get('/graph/export/obsidian/html/download', { params: { folder_id: folderId }, responseType: 'blob' }),
}
```

- [ ] **Step 2: 创建 llm.ts**

```typescript
// frontend/src/lib/api/llm.ts
import api from './client'

export interface LLMProviderConfig {
  function_group?: string
  provider: string
  api_key?: string
  base_url?: string
  model?: string
  is_active: boolean
}

export interface LLMConfigResponse {
  mode: string
  providers: LLMProviderConfig[]
}

export interface LLMTestResponse {
  success: boolean
  message: string
  model?: string
}

export interface ProviderInfo {
  value: string
  label: string
  requires_api_key: boolean
  default_base_url?: string
}

export interface FunctionGroup {
  value: string
  label: string
}

export const llmApi = {
  providers: () => api.get<{ providers: ProviderInfo[]; function_groups: FunctionGroup[] }>('/llm/providers'),
  getConfig: () => api.get<LLMConfigResponse>('/llm/config'),
  saveConfig: (config: LLMConfigResponse) => api.post<LLMConfigResponse>('/llm/config', config),
  test: (params: { provider: string; api_key?: string; base_url?: string; model?: string }) =>
    api.post<LLMTestResponse>('/llm/test', params),
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/lib/api/export.ts frontend/src/lib/api/llm.ts
git commit -m "feat(frontend): add export and llm API modules"
```

---

## Task 6: 创建 s2.ts

**Files:**
- Create: `frontend/src/lib/api/s2.ts`

- [ ] **Step 1: 创建 s2.ts**

```typescript
// frontend/src/lib/api/s2.ts
import api from './client'

// S2 Configuration types
export interface S2ConfigResponse {
  has_api_key: boolean
  enabled: boolean
  masked_key?: string
}

export interface S2ConfigRequest {
  api_key: string
  enabled?: boolean
}

export interface S2TestResponse {
  success: boolean
  message: string
}

// S2 Recommendation types
export interface RecommendedPaper {
  paperId: string
  title: string
  abstract?: string
  year?: number
  citationCount?: number
  authors?: Array<{ name: string }>
  venue?: string
  openAccessPdf?: { url: string }
  tldr?: { text: string }
}

export interface RecommendationsResponse {
  recommendations: RecommendedPaper[]
  based_on: string[]
}

export interface ConceptSearchPapersResponse {
  concept_id: string
  concept_text: string
  concept_text_zh?: string
  concept_text_en?: string
  papers: RecommendedPaper[]
  total: number
}

// S2 Paper Add types
export interface AddFromS2Request {
  s2_paper_id: string
  title: string
  year?: number
  abstract?: string
  authors?: Array<{ name: string }>
  venue?: string
  citation_count?: number
  tldr?: { text: string }
  open_access_pdf_url?: string
}

export interface AddFromS2Response {
  success: boolean
  message: string
  doi?: string
  title?: string
  concepts_count?: number
}

// Semantic Scholar API
export const s2Api = {
  getConfig: () => api.get<S2ConfigResponse>('/s2/config'),
  saveConfig: (data: S2ConfigRequest) => api.post<S2ConfigResponse>('/s2/config', data),
  test: (apiKey: string) => api.post<S2TestResponse>('/s2/test', { api_key: apiKey }),
  enhance: (doi: string) => api.post(`/s2/papers/${encodeURIComponent(doi)}/enhance`),
}

// S2 Recommendation API
export const recommendationApi = {
  getGraphRecommendations: () => api.get<RecommendationsResponse>('/recommendations'),
  searchPapersByConcept: (conceptId: string, year?: string, minCitations?: number, limit?: number) =>
    api.get<ConceptSearchPapersResponse>(`/concepts/${conceptId}/search-papers`, {
      params: { year, min_citations: minCitations, limit }
    }),
  searchPapersByConcepts: async (_conceptIds: string[], conceptTexts: string[]) => {
    const query = conceptTexts.join(' ')
    const res = await api.get<{ papers: RecommendedPaper[], total: number }>('/s2/search', {
      params: { query, limit: 20 }
    })
    return res
  },
}

// S2 Paper Add API
export const s2PaperApi = {
  addMetadata: (data: AddFromS2Request) => api.post<AddFromS2Response>('/papers/add-from-s2', {
    ...data,
    authors: data.authors?.map(a => a.name),
    tldr: data.tldr?.text
  }),
  downloadAndProcess: (data: AddFromS2Request & { open_access_pdf_url: string }) =>
    api.post<AddFromS2Response>('/papers/download-and-process', {
      ...data,
      authors: data.authors?.map(a => a.name),
      tldr: data.tldr?.text
    }),
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/lib/api/s2.ts
git commit -m "feat(frontend): add s2 API module with recommendation and paper apis"
```

---

## Task 7: 创建 citation.ts 和 folders.ts

**Files:**
- Create: `frontend/src/lib/api/citation.ts`
- Create: `frontend/src/lib/api/folders.ts`

- [ ] **Step 1: 创建 citation.ts**

```typescript
// frontend/src/lib/api/citation.ts
import api from './client'

export interface CitationRef {
  paper_id: string
  title?: string
  year?: number
  citation_count?: number
  is_internal?: boolean
}

export interface CitationNode {
  id: string
  title: string
  year?: number
  citation_count: number
  venue?: string
  references_count: number
  cited_by_count: number
  references: CitationRef[]
  cited_by: CitationRef[]
}

export interface CitationEdge {
  source: string
  target: string
  source_title?: string
  target_title?: string
}

export interface CitationGraphData {
  nodes: CitationNode[]
  edges: CitationEdge[]
}

export interface CitationBuildResponse {
  total_papers: number
  processed: number
  total_citations: number
  internal_edges: number
  errors: string[]
}

export interface CitationContext {
  paper_id: string
  title: string
  citation_count: number
  references: Array<{
    paper_id: string
    title?: string
    year?: number
    citation_count: number
    is_internal: boolean
  }>
  cited_by: Array<{
    paper_id: string
    title?: string
    year?: number
    citation_count: number
    is_internal: boolean
  }>
}

export const citationApi = {
  getGraph: () => api.get<CitationGraphData>('/citations/graph'),
  build: () => api.post<CitationBuildResponse>('/citations/build'),
  getContext: (paperId: string) => api.get<CitationContext>(`/papers/${encodeURIComponent(paperId)}/citations`),
}
```

- [ ] **Step 2: 创建 folders.ts**

```typescript
// frontend/src/lib/api/folders.ts
import api from './client'

export interface FolderResponse {
  id: string
  name: string
  description?: string
  paper_count: number
  created_at?: string
}

export interface CreateFolderRequest {
  name: string
  description?: string
}

export interface UpdateFolderRequest {
  name?: string
  description?: string
}

export const foldersApi = {
  list: () => api.get<FolderResponse[]>('/folders/'),
  create: (data: CreateFolderRequest) => api.post<FolderResponse>('/folders/', data),
  update: (id: string, data: UpdateFolderRequest) => api.patch<FolderResponse>(`/folders/${id}`, data),
  delete: (id: string) => api.delete(`/folders/${id}`),
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/lib/api/citation.ts frontend/src/lib/api/folders.ts
git commit -m "feat(frontend): add citation and folders API modules"
```

---

## Task 8: 创建 agent.ts

**Files:**
- Create: `frontend/src/lib/api/agent.ts`

- [ ] **Step 1: 创建 agent.ts**

```typescript
// frontend/src/lib/api/agent.ts
import api from './client'
import type { ChatAttachment } from '../../stores/agentStore'

export type AgentType = 'lead' | 'citation' | 'research' | 'deep_research' | 'paper_qa' | 'merge'

export interface AgentMessage {
  role: 'user' | 'assistant'
  content: string
  agent?: AgentType
}

export interface AgentContextSummary {
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
  lastActiveAgent: AgentType
}

export interface ConceptGraphData {
  id: string
  name: string
  category?: string
  paper_count: number
  children?: ConceptGraphData[]
  parents?: ConceptGraphData[]
}

export type AttachmentType = 'research_points' | 'paper_detail' | 'paper_list' | 'concept_graph' | 'recommendation' | 'citation_analysis'

export interface AgentChatResponse {
  message: string
  agent: string
  toolUsed?: string
  contextUpdate?: Partial<AgentContextSummary>
  researchSessionId?: string
  conceptData?: ConceptGraphData
  attachments?: Array<{ type: AttachmentType; data: any }>
}

export const agentApi = {
  chat: async (message: string, context: AgentContextSummary, history: AgentMessage[]): Promise<AgentChatResponse> => {
    const response = await api.post<AgentChatResponse>('/agent/chat', {
      message,
      context,
      history,
    })
    return response.data
  },

  chatStream: (message: string, context: AgentContextSummary, history: AgentMessage[]): string => {
    const params = new URLSearchParams({
      message,
      context: JSON.stringify(context),
      history: JSON.stringify(history),
    })
    return `/api/agent/chat/stream?${params.toString()}`
  },

  chatStreamFetch: async (
    message: string,
    context: AgentContextSummary,
    history: AgentMessage[],
    onEvent: (event: { type: string; [key: string]: any }) => void
  ): Promise<void> => {
    const response = await fetch('/api/agent/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, context, history }),
    })

    if (!response.ok) {
      throw new Error(`SSE request failed: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) return

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          try {
            const event = JSON.parse(data)
            onEvent(event)
          } catch (e) {
            console.warn('Failed to parse SSE event:', data)
          }
        }
      }
    }
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

- [ ] **Step 2: 提交**

```bash
git add frontend/src/lib/api/agent.ts
git commit -m "feat(frontend): add agent API module with SSE streaming"
```

---

## Task 9: 创建 conversations.ts

**Files:**
- Create: `frontend/src/lib/api/conversations.ts`

- [ ] **Step 1: 创建 conversations.ts**

```typescript
// frontend/src/lib/api/conversations.ts
import api from './client'
import { getOrCreateDeviceId } from './client'
import type { ChatAttachment } from '../../stores/agentStore'

export interface Conversation {
  id: string
  title?: string
  created_at?: string
  updated_at?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: string
  attachments?: ChatAttachment[]
  conceptData?: any
  created_at?: string
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export const conversationsApi = {
  create: async (): Promise<Conversation> => {
    const response = await api.post<Conversation>('/conversations')
    return response.data
  },

  list: async (): Promise<Conversation[]> => {
    const response = await api.get<Conversation[]>('/conversations')
    return response.data
  },

  get: async (id: string): Promise<ConversationDetail> => {
    const response = await api.get<ConversationDetail>(`/conversations/${id}`)
    return response.data
  },

  updateTitle: async (id: string, title: string): Promise<void> => {
    await api.put(`/conversations/${id}/title`, { title })
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/conversations/${id}`)
  },

  addMessage: async (convId: string, message: {
    role: 'user' | 'assistant'
    content: string
    agent?: string
    attachments?: ChatAttachment[]
  }): Promise<void> => {
    await api.post(`/conversations/${convId}/messages`, message)
  },

  getDeviceId: getOrCreateDeviceId,
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/lib/api/conversations.ts
git commit -m "feat(frontend): add conversations API module"
```

---

## Task 10: 创建 index.ts 并删除旧文件

**Files:**
- Create: `frontend/src/lib/api/index.ts`
- Delete: `frontend/src/lib/api.ts`

- [ ] **Step 1: 创建 index.ts**

```typescript
// frontend/src/lib/api/index.ts
// Re-export everything for backward compatibility

export { default as api } from './client'
export { getOrCreateDeviceId } from './client'

export { papersApi } from './papers'
export type { PaperContribution, ProcessSingleResponse } from './papers'

export { conceptsApi } from './concepts'

export { graphApi } from './graph'

export { dedupApi } from './dedup'
export type { ScanStatusResponse } from './dedup'

export { batchApi } from './batch'

export { exportApi } from './export'

export { llmApi } from './llm'

export { s2Api, recommendationApi, s2PaperApi } from './s2'
export type { S2ConfigResponse, S2ConfigRequest, S2TestResponse } from './s2'

export { citationApi } from './citation'

export { foldersApi } from './folders'

export { agentApi } from './agent'

export { conversationsApi } from './conversations'
export type { Conversation, Message, ConversationDetail } from './conversations'
```

- [ ] **Step 2: 删除旧文件**

```bash
rm frontend/src/lib/api.ts
```

- [ ] **Step 3: 验证导入**

```bash
cd D:/meta-knowledge-graph-main/frontend
npx tsc --noEmit
```

Expected: No type errors

- [ ] **Step 4: 提交**

```bash
git add frontend/src/lib/api/ frontend/src/lib/api.ts
git commit -m "refactor(frontend): modularize API into domain-specific files

- Split 675-line api.ts into 14 modules
- Each module contains its API object and types
- index.ts re-exports everything for backward compatibility
- Max file size reduced from 675 to ~100 lines"
```

---

## 预期结果

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 最大文件行数 | 675 | ~100 |
| 文件数 | 1 | 14 |
| 类型可测试 | ❌ | ✅ |
| 向后兼容 | N/A | ✅ |