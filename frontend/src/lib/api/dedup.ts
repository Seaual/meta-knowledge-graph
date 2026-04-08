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