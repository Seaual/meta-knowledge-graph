import axios from 'axios'

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
  obsidian: () => api.get<ExportResponse>('/graph/export/obsidian'),
  download: () =>
    api.get('/graph/export/obsidian/download', { responseType: 'blob' }),
  canvas: () => api.get('/graph/export/obsidian/canvas'),
  downloadCanvas: () =>
    api.get('/graph/export/obsidian/canvas/download', { responseType: 'blob' }),
  html: () => api.get('/graph/export/obsidian/html'),
  downloadHtml: () =>
    api.get('/graph/export/obsidian/html/download', { responseType: 'blob' }),
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

// LLM API
export const llmApi = {
  providers: () => api.get<{ providers: ProviderInfo[]; function_groups: FunctionGroup[] }>('/llm/providers'),
  getConfig: () => api.get<LLMConfigResponse>('/llm/config'),
  saveConfig: (config: LLMConfigResponse) => api.post<LLMConfigResponse>('/llm/config', config),
  test: (params: { provider: string; api_key?: string; base_url?: string; model?: string }) =>
    api.post<LLMTestResponse>('/llm/test', params),
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

export type { PaperContribution, ProcessSingleResponse, ScanStatusResponse }

// Folder API
export const foldersApi = {
  list: () => api.get<FolderResponse[]>('/folders/'),
  create: (data: CreateFolderRequest) => api.post<FolderResponse>('/folders/', data),
  update: (id: string, data: UpdateFolderRequest) => api.patch<FolderResponse>(`/folders/${id}`, data),
  delete: (id: string) => api.delete(`/folders/${id}`),
}

export default api