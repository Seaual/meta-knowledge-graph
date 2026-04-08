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