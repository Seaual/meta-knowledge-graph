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