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