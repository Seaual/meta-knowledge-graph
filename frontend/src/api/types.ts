// Types shared between API modules

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

export interface ScanStatusResponse {
  scan_id: string
  status: string
  total_concepts: number
  concepts_scanned: number
  progress: number
  estimated_time: number
  suggestions: MergeSuggestion[] | null
  error?: string
}

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

export interface ExportResponse {
  content: string
  stats: {
    papers: number
    concepts: number
    generated_at: string
  }
}

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