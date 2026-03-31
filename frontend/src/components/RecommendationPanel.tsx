import { useState, useCallback, useEffect } from 'react'
import { X, ExternalLink, Plus, Search, Loader2, Download, Database, CheckCircle, AlertCircle } from 'lucide-react'
import { recommendationApi, s2PaperApi } from '../lib/api'
import { useTranslation } from '../i18n'

interface Concept {
  id: string
  text: string  // 中文名称
  text_en?: string  // 英文名称
  category: string | null | undefined
  paper_count: number
}

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

interface RecommendationPanelProps {
  isOpen: boolean
  onClose: () => void
  selectedConcepts: Concept[]
  onAddConcept: (concept: Concept) => void
  onRemoveConcept: (conceptId: string) => void
  concepts: Concept[] // all concepts for selection
}

// Category colors
const CATEGORY_COLORS: Record<string, string> = {
  field: '#6b4423',
  direction: '#b8860b',
  subdirection: '#9a6b3c',
  task: '#4a6b8a',
  method: '#c2410c',
  technique: '#2d5a27',
}

// 根据语言获取概念显示名称
function getConceptDisplayText(concept: Concept, language: 'zh' | 'en'): string {
  if (language === 'en' && concept.text_en) {
    return concept.text_en
  }
  return concept.text
}

export default function RecommendationPanel({
  isOpen,
  onClose,
  selectedConcepts,
  onAddConcept,
  onRemoveConcept,
  concepts,
}: RecommendationPanelProps) {
  const { t, language } = useTranslation()
  const [recommendations, setRecommendations] = useState<RecommendedPaper[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchMode, setSearchMode] = useState<'combined' | 'single'>('combined')
  const [yearFilter, setYearFilter] = useState('2023-2026')
  const [minCitations, setMinCitations] = useState(0)
  const [showConceptPicker, setShowConceptPicker] = useState(false)
  const [addingPapers, setAddingPapers] = useState<Set<string>>(new Set()) // 正在添加的论文
  const [addedPapers, setAddedPapers] = useState<Set<string>>(new Set()) // 已成功添加的论文
  const [addErrors, setAddErrors] = useState<Map<string, string>>(new Map()) // 添加失败的错误

  // Search papers when concepts change
  const searchPapers = useCallback(async () => {
    if (selectedConcepts.length === 0) {
      setRecommendations([])
      setError(null)
      return
    }

    setLoading(true)
    setError(null)
    try {
      if (searchMode === 'combined') {
        // Combined search - use all concepts as one query
        const res = await recommendationApi.searchPapersByConcept(selectedConcepts[0].id, yearFilter, minCitations, 20)
        setRecommendations(res.data.papers)
        // If no papers and we had a concept, might be rate limited
        if (res.data.papers.length === 0) {
          setError('rateLimited')
        }
      } else {
        // Single search - search each concept separately and combine results
        const allPapers: RecommendedPaper[] = []
        const seenIds = new Set<string>()

        for (const concept of selectedConcepts) {
          const res = await recommendationApi.searchPapersByConcept(concept.id, yearFilter, minCitations, 10)
          for (const paper of res.data.papers) {
            if (!seenIds.has(paper.paperId)) {
              seenIds.add(paper.paperId)
              allPapers.push(paper)
            }
          }
        }

        // Sort by citation count
        allPapers.sort((a, b) => (b.citationCount || 0) - (a.citationCount || 0))
        setRecommendations(allPapers.slice(0, 20))
        if (allPapers.length === 0) {
          setError('rateLimited')
        }
      }
    } catch (err: any) {
      console.error('Failed to search papers:', err)
      // Check for rate limit error
      if (err?.response?.status === 429) {
        setError('rateLimited')
      } else {
        setError('error')
      }
      setRecommendations([])
    } finally {
      setLoading(false)
    }
  }, [selectedConcepts, searchMode, yearFilter, minCitations])

  // Auto search when concepts change
  useEffect(() => {
    if (isOpen && selectedConcepts.length > 0) {
      searchPapers()
    }
  }, [isOpen, selectedConcepts, searchPapers])

  // Handle adding paper metadata only
  const handleAddMetadata = useCallback(async (paper: RecommendedPaper) => {
    setAddingPapers(prev => new Set(prev).add(paper.paperId))
    setAddErrors(prev => {
      const next = new Map(prev)
      next.delete(paper.paperId)
      return next
    })

    try {
      const res = await s2PaperApi.addMetadata({
        s2_paper_id: paper.paperId,
        title: paper.title,
        year: paper.year,
        abstract: paper.abstract,
        authors: paper.authors,
        venue: paper.venue,
        citation_count: paper.citationCount,
        tldr: paper.tldr,
        open_access_pdf_url: paper.openAccessPdf?.url,
      })

      if (res.data.success) {
        setAddedPapers(prev => new Set(prev).add(paper.paperId))
      } else {
        setAddErrors(prev => new Map(prev).set(paper.paperId, res.data.message))
      }
    } catch (err: any) {
      console.error('Failed to add metadata:', err)
      setAddErrors(prev => new Map(prev).set(paper.paperId, err.response?.data?.detail || '添加失败'))
    } finally {
      setAddingPapers(prev => {
        const next = new Set(prev)
        next.delete(paper.paperId)
        return next
      })
    }
  }, [])

  // Handle downloading and processing paper
  const handleDownloadAndProcess = useCallback(async (paper: RecommendedPaper) => {
    if (!paper.openAccessPdf?.url) return

    setAddingPapers(prev => new Set(prev).add(paper.paperId))
    setAddErrors(prev => {
      const next = new Map(prev)
      next.delete(paper.paperId)
      return next
    })

    try {
      const res = await s2PaperApi.downloadAndProcess({
        s2_paper_id: paper.paperId,
        title: paper.title,
        year: paper.year,
        abstract: paper.abstract,
        authors: paper.authors,
        venue: paper.venue,
        citation_count: paper.citationCount,
        tldr: paper.tldr,
        open_access_pdf_url: paper.openAccessPdf.url,
      })

      if (res.data.success) {
        setAddedPapers(prev => new Set(prev).add(paper.paperId))
      } else {
        setAddErrors(prev => new Map(prev).set(paper.paperId, res.data.message))
      }
    } catch (err: any) {
      console.error('Failed to download and process:', err)
      setAddErrors(prev => new Map(prev).set(paper.paperId, err.response?.data?.detail || '处理失败'))
    } finally {
      setAddingPapers(prev => {
        const next = new Set(prev)
        next.delete(paper.paperId)
        return next
      })
    }
  }, [])

  // Available concepts for adding (exclude already selected)
  const availableConcepts = concepts.filter(
    c => !selectedConcepts.some(s => s.id === c.id)
  )

  if (!isOpen) return null

  return (
    <div className="absolute top-20 left-4 w-[420px] card-academic z-20 max-h-[80vh] overflow-hidden animate-slide-up">
      {/* Header */}
      <div className="p-4 border-b border-academic bg-vellum">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-display font-medium text-sepia text-base">
              📚 {t.concepts.recommendation.title}
            </h3>
            <p className="font-body text-xs text-muted mt-1">
              {t.concepts.recommendation.basedOn} {selectedConcepts.length} {t.concepts.recommendation.concepts}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-6 h-6 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Selected Concepts */}
      <div className="px-4 py-3 border-b border-academic bg-paper">
        <div className="flex items-center gap-2 mb-2">
          <span className="font-mono text-xs text-sepia uppercase tracking-wider">
            {t.concepts.recommendation.selectedConcepts}
          </span>
          <button
            onClick={() => setShowConceptPicker(!showConceptPicker)}
            className="btn-secondary-xs flex items-center gap-1"
          >
            <Plus className="w-3 h-3" />
            {t.concepts.recommendation.addConcept}
          </button>
        </div>

        {/* Concept Tags */}
        <div className="flex flex-wrap gap-2">
          {selectedConcepts.map(concept => (
            <button
              key={concept.id}
              onClick={() => onRemoveConcept(concept.id)}
              className="badge-academic cursor-pointer hover:opacity-70 transition-opacity flex items-center gap-1"
              style={{
                backgroundColor: CATEGORY_COLORS[concept.category || 'method'] + '15',
                color: CATEGORY_COLORS[concept.category || 'method'],
                borderColor: CATEGORY_COLORS[concept.category || 'method'] + '30',
              }}
            >
              {getConceptDisplayText(concept, language)}
              <X className="w-3 h-3" />
            </button>
          ))}
        </div>

        {/* Concept Picker Dropdown */}
        {showConceptPicker && (
          <div className="mt-2 border border-academic rounded-large bg-vellum p-2 max-h-[150px] overflow-y-auto animate-slide-down">
            {availableConcepts.length === 0 ? (
              <div className="font-body text-xs text-muted text-center py-2">
                所有概念已选择
              </div>
            ) : (
              availableConcepts.slice(0, 20).map(concept => (
                <button
                  key={concept.id}
                  onClick={() => {
                    onAddConcept(concept)
                    setShowConceptPicker(false)
                  }}
                  className="w-full text-left px-2 py-1.5 font-body text-sm text-sepia hover:bg-paper rounded-soft transition-colors flex items-center gap-2"
                >
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: CATEGORY_COLORS[concept.category || 'method'] }}
                  />
                  <span className="truncate">{getConceptDisplayText(concept, language)}</span>
                  <span className="font-mono text-xs text-faint ml-auto">{concept.paper_count || 0}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="px-4 py-3 border-b border-academic bg-paper flex items-center gap-3">
        {/* Search Mode Toggle */}
        <div className="flex gap-1">
          <button
            onClick={() => setSearchMode('combined')}
            className={`btn-secondary-xs ${searchMode === 'combined' ? 'border-sepia text-sepia' : ''}`}
          >
            {t.concepts.recommendation.combinedSearch}
          </button>
          <button
            onClick={() => setSearchMode('single')}
            className={`btn-secondary-xs ${searchMode === 'single' ? 'border-sepia text-sepia' : ''}`}
          >
            {t.concepts.recommendation.singleSearch}
          </button>
        </div>

        {/* Year Filter */}
        <select
          value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}
          className="btn-secondary-xs bg-paper"
        >
          <option value="">{t.concepts.recommendation.allYears}</option>
          <option value="2025-2026">2025-2026</option>
          <option value="2023-2026">2023-2026</option>
          <option value="2020-2026">2020-2026</option>
          <option value="2015-2026">2015+</option>
        </select>

        {/* Min Citations */}
        <input
          type="number"
          value={minCitations}
          onChange={(e) => setMinCitations(Number(e.target.value))}
          placeholder={t.concepts.recommendation.minCitations}
          className="btn-secondary-xs w-20 bg-paper"
          min="0"
        />

        {/* Search Button */}
        <button
          onClick={searchPapers}
          disabled={loading || selectedConcepts.length === 0}
          className="btn-primary-xs flex items-center gap-1"
        >
          <Search className="w-3 h-3" />
          {t.concepts.recommendation.searchPapers}
        </button>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ maxHeight: '400px' }}>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-sepia" />
            <span className="font-body text-sm text-muted ml-2">
              {t.concepts.recommendation.loading}
            </span>
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <div className="font-body text-sm text-status-error">
              {error === 'rateLimited' ? t.concepts.recommendation.rateLimited : t.concepts.recommendation.error}
            </div>
            <button
              onClick={searchPapers}
              className="btn-secondary mt-3 text-sm"
            >
              重试
            </button>
          </div>
        ) : recommendations.length === 0 ? (
          <div className="text-center py-8">
            <div className="font-body text-sm text-muted">
              {selectedConcepts.length === 0
                ? t.concepts.recommendation.addConcept
                : t.concepts.recommendation.noResults}
            </div>
          </div>
        ) : (
          recommendations.map((paper) => (
            <div
              key={paper.paperId}
              className="border border-academic rounded-large p-3 hover:border-sepia hover:bg-vellum/50 transition-colors"
            >
              {/* Title */}
              <h4 className="font-display font-medium text-sepia text-sm leading-tight">
                {paper.title}
              </h4>

              {/* Meta */}
              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                {paper.year && (
                  <span className="font-mono text-xs text-muted">{paper.year}</span>
                )}
                {paper.venue && (
                  <span
                    className="badge-academic-xs truncate max-w-[150px]"
                    style={{ backgroundColor: '#f5f0e8', color: '#6b4423', borderColor: '#e8dfd0' }}
                    title={paper.venue}
                  >
                    {paper.venue.length > 20 ? paper.venue.slice(0, 20) + '...' : paper.venue}
                  </span>
                )}
                {paper.citationCount !== undefined && (
                  <span className="font-mono text-xs text-sepia font-medium">
                    {paper.citationCount} citations
                  </span>
                )}
              </div>

              {/* TLDR */}
              {paper.tldr?.text && (
                <div className="mt-2 p-2 bg-status-success/5 rounded-soft">
                  <p className="font-quote text-xs text-status-success italic">
                    💡 {paper.tldr.text}
                  </p>
                </div>
              )}

              {/* Abstract snippet */}
              {paper.abstract && (
                <p className="font-body text-xs text-muted mt-2 line-clamp-2">
                  {paper.abstract.slice(0, 200)}...
                </p>
              )}

              {/* Authors */}
              {paper.authors && paper.authors.length > 0 && (
                <div className="font-body text-xs text-faint mt-1.5">
                  {paper.authors.slice(0, 3).map(a => a.name).join(', ')}
                  {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center flex-wrap gap-2 mt-3">
                {/* Already added indicator */}
                {addedPapers.has(paper.paperId) && (
                  <span className="btn-secondary-xs flex items-center gap-1 text-status-success border-status-success">
                    <CheckCircle className="w-3 h-3" />
                    已添加
                  </span>
                )}

                {/* Error indicator */}
                {addErrors.has(paper.paperId) && (
                  <span className="text-xs text-status-error flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {addErrors.get(paper.paperId)}
                  </span>
                )}

                {/* Download and process button */}
                {paper.openAccessPdf?.url && !addedPapers.has(paper.paperId) && (
                  <button
                    onClick={() => handleDownloadAndProcess(paper)}
                    disabled={addingPapers.has(paper.paperId)}
                    className="btn-primary-xs flex items-center gap-1"
                  >
                    {addingPapers.has(paper.paperId) ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        处理中...
                      </>
                    ) : (
                      <>
                        <Download className="w-3 h-3" />
                        下载并处理
                      </>
                    )}
                  </button>
                )}

                {/* Add metadata only button */}
                {!addedPapers.has(paper.paperId) && (
                  <button
                    onClick={() => handleAddMetadata(paper)}
                    disabled={addingPapers.has(paper.paperId)}
                    className="btn-secondary-xs flex items-center gap-1"
                  >
                    {addingPapers.has(paper.paperId) ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        添加中...
                      </>
                    ) : (
                      <>
                        <Database className="w-3 h-3" />
                        仅添加元数据
                      </>
                    )}
                  </button>
                )}

                {/* View on S2 */}
                <a
                  href={`https://www.semanticscholar.org/paper/${paper.paperId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary-xs flex items-center gap-1"
                >
                  <ExternalLink className="w-3 h-3" />
                  {t.concepts.recommendation.viewOnS2}
                </a>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}