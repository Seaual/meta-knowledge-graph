import axios from 'axios'
import type { ChatAttachment } from '../stores/agentStore'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Papers API
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

// Concepts API
export const conceptsApi = {
  list: () => api.get('/concepts/'),
  roots: () => api.get('/concepts/roots'),
  tree: (rootId?: string) => api.get('/concepts/tree', { params: { root_id: rootId } }),
  search: (q: string) => api.get('/concepts/search', { params: { q } }),
  get: (id: string) => api.get(`/concepts/${id}`),
  papers: (id: string) => api.get(`/concepts/${id}/papers`),
  researchPoints: (id: string) => api.get(`/concepts/${id}/research-points`),
}

// Graph API
export const graphApi = {
  stats: () => api.get('/graph/stats'),
  data: (folder?: string) => api.get('/graph/data', { params: { folder } }),
  treeData: () => api.get('/graph/tree-data'),
}

// Dedup API types
interface MergeSuggestion {
  id: string
  source: { id: string; text: string; paper_count: number }
  target: { id: string; text: string; paper_count: number }
  confidence: number
  rationale: string
}

interface ExecuteDetail {
  source: string
  target: string
  status: 'success' | 'failed'
  message?: string
}

interface FloatingConceptDetail {
  concept: string
  parent?: string
  status: 'fixed' | 'skipped' | 'failed'
  reason?: string
}

interface DedupExecuteResponse {
  executed: number
  details: ExecuteDetail[]
  floating_fixed?: number
  floating_details?: FloatingConceptDetail[]
}

interface ScanStatusResponse {
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

// Dedup API
export const dedupApi = {
  scan: (folderId?: string) => api.post<{ scan_id: string; total_concepts: number; status: string }>('/concepts/dedup/scan', { folder_id: folderId }),
  scanStatus: (scanId: string) => api.get<ScanStatusResponse>(`/concepts/dedup/scan-status/${scanId}`),
  execute: (scanId: string, mergeIds: string[]) =>
    api.post<DedupExecuteResponse>('/concepts/dedup/execute', {
      scan_id: scanId,
      merge_ids: mergeIds,
    }),
}

// Batch types
interface BatchUploadResponse {
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

interface BatchProcessResponse {
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

interface BatchJobStatus {
  id: string
  status: string
  total: number
  completed: number
  successful: number
  failed: number
  created_at?: string
}

interface ExportResponse {
  content: string
  stats: {
    papers: number
    concepts: number
    generated_at: string
  }
}

// Batch API
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

// Export API
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

// LLM Configuration types
interface LLMProviderConfig {
  function_group?: string
  provider: string
  api_key?: string
  base_url?: string
  model?: string
  is_active: boolean
}

interface LLMConfigResponse {
  mode: string
  providers: LLMProviderConfig[]
}

interface LLMTestResponse {
  success: boolean
  message: string
  model?: string
}

interface ProviderInfo {
  value: string
  label: string
  requires_api_key: boolean
  default_base_url?: string
}

interface FunctionGroup {
  value: string
  label: string
}

// Semantic Scholar Configuration types
interface S2ConfigResponse {
  has_api_key: boolean
  enabled: boolean
  masked_key?: string
}

interface S2ConfigRequest {
  api_key: string
  enabled?: boolean
}

interface S2TestResponse {
  success: boolean
  message: string
}

// LLM API
export const llmApi = {
  providers: () => api.get<{ providers: ProviderInfo[]; function_groups: FunctionGroup[] }>('/llm/providers'),
  getConfig: () => api.get<LLMConfigResponse>('/llm/config'),
  saveConfig: (config: LLMConfigResponse) => api.post<LLMConfigResponse>('/llm/config', config),
  test: (params: { provider: string; api_key?: string; base_url?: string; model?: string }) =>
    api.post<LLMTestResponse>('/llm/test', params),
}

// Semantic Scholar API
export const s2Api = {
  getConfig: () => api.get<S2ConfigResponse>('/s2/config'),
  saveConfig: (data: S2ConfigRequest) => api.post<S2ConfigResponse>('/s2/config', data),
  test: (apiKey: string) => api.post<S2TestResponse>('/s2/test', { api_key: apiKey }),
  enhance: (doi: string) => api.post(`/s2/papers/${encodeURIComponent(doi)}/enhance`),
}

// S2 Recommendation types
interface RecommendedPaper {
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

interface RecommendationsResponse {
  recommendations: RecommendedPaper[]
  based_on: string[]
}

interface ConceptSearchPapersResponse {
  concept_id: string
  concept_text: string  // 用于搜索的文本
  concept_text_zh?: string  // 中文名称
  concept_text_en?: string  // 英文名称
  papers: RecommendedPaper[]
  total: number
}

// S2 Recommendation API
export const recommendationApi = {
  // Get recommendations based on top papers in graph
  getGraphRecommendations: () => api.get<RecommendationsResponse>('/recommendations'),
  // Search papers by concept
  searchPapersByConcept: (conceptId: string, year?: string, minCitations?: number, limit?: number) =>
    api.get<ConceptSearchPapersResponse>(`/concepts/${conceptId}/search-papers`, {
      params: { year, min_citations: minCitations, limit }
    }),
  // Search papers by multiple concepts (combines queries)
  searchPapersByConcepts: async (_conceptIds: string[], conceptTexts: string[]) => {
    // Combine concept texts as search query
    const query = conceptTexts.join(' ')
    const res = await api.get<{ papers: RecommendedPaper[], total: number }>('/s2/search', {
      params: { query, limit: 20 }
    })
    return res
  },
}

// S2 Paper Add API types
interface AddFromS2Request {
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

interface AddFromS2Response {
  success: boolean
  message: string
  doi?: string
  title?: string
  concepts_count?: number
}

export const s2PaperApi = {
  // Add paper metadata only (no PDF processing)
  addMetadata: (data: AddFromS2Request) => api.post<AddFromS2Response>('/papers/add-from-s2', {
    ...data,
    authors: data.authors?.map(a => a.name),
    tldr: data.tldr?.text
  }),
  // Download PDF and process
  downloadAndProcess: (data: AddFromS2Request & { open_access_pdf_url: string }) =>
    api.post<AddFromS2Response>('/papers/download-and-process', {
      ...data,
      authors: data.authors?.map(a => a.name),
      tldr: data.tldr?.text
    }),
}

// Citation Graph types
interface CitationRef {
  paper_id: string
  title?: string
  year?: number
  citation_count?: number
  is_internal?: boolean
}

interface CitationNode {
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

interface CitationEdge {
  source: string
  target: string
  source_title?: string
  target_title?: string
}

interface CitationGraphData {
  nodes: CitationNode[]
  edges: CitationEdge[]
}

interface CitationBuildResponse {
  total_papers: number
  processed: number
  total_citations: number
  internal_edges: number
  errors: string[]
}

interface CitationContext {
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

// Citation Graph API
export const citationApi = {
  // Get citation graph data
  getGraph: () => api.get<CitationGraphData>('/citations/graph'),
  // Build citation graph (trigger S2 data fetch)
  build: () => api.post<CitationBuildResponse>('/citations/build'),
  // Get citation context for a paper
  getContext: (paperId: string) => api.get<CitationContext>(`/papers/${encodeURIComponent(paperId)}/citations`),
}

// Folder types
interface FolderResponse {
  id: string
  name: string
  description?: string
  paper_count: number
  created_at?: string
}

interface CreateFolderRequest {
  name: string
  description?: string
}

interface UpdateFolderRequest {
  name?: string
  description?: string
}

interface PaperContribution {
  node_count: number
  root_concept?: string
}

interface ProcessSingleResponse {
  success: boolean
  message: string
  concept_tree: any | null
  duration: number
  concepts_count: number
}

export type { PaperContribution, ProcessSingleResponse, ScanStatusResponse, S2ConfigResponse, S2ConfigRequest, S2TestResponse }

// Folder API
export const foldersApi = {
  list: () => api.get<FolderResponse[]>('/folders/'),
  create: (data: CreateFolderRequest) => api.post<FolderResponse>('/folders/', data),
  update: (id: string, data: UpdateFolderRequest) => api.patch<FolderResponse>(`/folders/${id}`, data),
  delete: (id: string) => api.delete(`/folders/${id}`),
}

// Agent API types
type AgentType = 'lead' | 'citation' | 'research' | 'deep_research' | 'paper_qa' | 'merge'

interface AgentMessage {
  role: 'user' | 'assistant'
  content: string
  agent?: AgentType
}

interface AgentContextSummary {
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

// 概念图谱数据
interface ConceptGraphData {
  id: string
  name: string
  category?: string
  paper_count: number
  children?: ConceptGraphData[]
  parents?: ConceptGraphData[]
}

// 附件类型定义
type AttachmentType = 'research_points' | 'paper_detail' | 'paper_list' | 'concept_graph' | 'recommendation' | 'citation_analysis'

interface AgentChatResponse {
  message: string
  agent: string
  contextUpdate?: Partial<AgentContextSummary>
  researchSessionId?: string
  conceptData?: ConceptGraphData  // deprecated
  attachments?: Array<{ type: AttachmentType; data: any }>  // 新增
}

// Agent API
export const agentApi = {
  chat: async (message: string, context: AgentContextSummary, history: AgentMessage[]): Promise<AgentChatResponse> => {
    const response = await api.post<AgentChatResponse>('/agent/chat', {
      message,
      context,
      history,
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

// Conversation types
interface Conversation {
  id: string
  title?: string
  created_at?: string
  updated_at?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: string
  attachments?: ChatAttachment[]
  created_at?: string
}

interface ConversationDetail extends Conversation {
  messages: Message[]
}

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

// Conversation API
export const conversationsApi = {
  // Create new conversation
  create: async (): Promise<Conversation> => {
    const response = await api.post<Conversation>('/conversations')
    return response.data
  },

  // List conversations
  list: async (): Promise<Conversation[]> => {
    const response = await api.get<Conversation[]>('/conversations')
    return response.data
  },

  // Get conversation with messages
  get: async (id: string): Promise<ConversationDetail> => {
    const response = await api.get<ConversationDetail>(`/conversations/${id}`)
    return response.data
  },

  // Update title
  updateTitle: async (id: string, title: string): Promise<void> => {
    await api.put(`/conversations/${id}/title`, { title })
  },

  // Delete conversation
  delete: async (id: string): Promise<void> => {
    await api.delete(`/conversations/${id}`)
  },

  // Add message
  addMessage: async (convId: string, message: {
    role: 'user' | 'assistant'
    content: string
    agent?: string
    attachments?: ChatAttachment[]
  }): Promise<void> => {
    await api.post(`/conversations/${convId}/messages`, message)
  },

  // Get device ID
  getDeviceId: getOrCreateDeviceId,
}

export default api