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

export default api