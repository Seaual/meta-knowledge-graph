import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Papers API
export const papersApi = {
  list: (status?: string) => api.get('/papers/', { params: { status } }),
  get: (doi: string) => api.get(`/papers/${encodeURIComponent(doi)}`),
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/papers/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  process: (doi: string) => api.post('/papers/process', { doi }),
  delete: (doi: string) => api.delete(`/papers/${encodeURIComponent(doi)}`),
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
  data: () => api.get('/graph/data'),
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

interface DedupScanResponse {
  scan_id: string
  status: string
  candidates_found: number
  merge_suggestions: MergeSuggestion[]
}

interface ExecuteDetail {
  source: string
  target: string
  status: 'success' | 'failed'
  message?: string
}

interface DedupExecuteResponse {
  executed: number
  details: ExecuteDetail[]
}

// Dedup API
export const dedupApi = {
  scan: () => api.post<DedupScanResponse>('/concepts/dedup/scan'),
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
  id: string  // Database column is 'id', not 'job_id'
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
}

export default api