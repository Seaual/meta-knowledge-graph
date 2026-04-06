import { useState } from 'react'
import { Plus, Check, Loader2 } from 'lucide-react'
import { s2PaperApi } from '../lib/api'

interface RecommendedPaper {
  title: string
  authors?: string[]
  year?: number
  abstract?: string
  citation_count?: number
  venue?: string
  paper_id?: string
  open_access_url?: string | null
  tldr?: string | null
}

interface Props {
  data: {
    concept_name: string
    papers: RecommendedPaper[]
    count?: number
  }
  onAction: (text: string) => void
}

export default function RecommendationCard({ data, onAction }: Props) {
  const { concept_name, papers, count } = data
  const [addingPaperId, setAddingPaperId] = useState<string | null>(null)
  const [addedPaperIds, setAddedPaperIds] = useState<Set<string>>(new Set())

  const handleAddToLibrary = async (paper: RecommendedPaper) => {
    if (!paper.paper_id || addingPaperId === paper.paper_id || addedPaperIds.has(paper.paper_id)) {
      return
    }

    setAddingPaperId(paper.paper_id)
    try {
      await s2PaperApi.addMetadata({
        s2_paper_id: paper.paper_id,
        title: paper.title,
        year: paper.year,
        abstract: paper.abstract,
        authors: paper.authors?.map(name => ({ name })),
        venue: paper.venue,
        citation_count: paper.citation_count,
        tldr: paper.tldr ? { text: paper.tldr } : undefined,
        open_access_pdf_url: paper.open_access_url || undefined,
      })
      setAddedPaperIds(prev => new Set(prev).add(paper.paper_id!))
    } catch (error) {
      console.error('Failed to add paper:', error)
    } finally {
      setAddingPaperId(null)
    }
  }

  const handleTitleClick = (paper: RecommendedPaper) => {
    onAction(`查看论文详情: ${paper.title}`)
  }

  return (
    <div
      className="my-2 rounded-xl overflow-hidden"
      style={{
        background: 'rgba(184, 134, 11, 0.04)',
        border: '1px solid rgba(184, 134, 11, 0.1)',
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3"
        style={{
          borderBottom: '1px solid rgba(184, 134, 11, 0.08)',
          background: 'rgba(245, 240, 232, 0.3)',
        }}
      >
        <h3
          className="font-display font-medium text-base"
          style={{ color: 'var(--color-sepia)' }}
        >
          推荐论文
        </h3>
        <p
          className="font-body text-xs mt-0.5"
          style={{ color: 'var(--color-muted)' }}
        >
          {concept_name}
          {count !== undefined && (
            <span className="ml-2 opacity-70">
              共 {count} 篇
            </span>
          )}
        </p>
      </div>

      {/* Paper List */}
      <div className="divide-y divide-academic/10">
        {papers.map((paper, index) => {
          const isAdding = addingPaperId === paper.paper_id
          const isAdded = paper.paper_id && addedPaperIds.has(paper.paper_id)

          return (
            <div
              key={paper.paper_id || index}
              className="p-4 hover:bg-vellum/30 transition-colors"
            >
              {/* Title - Clickable */}
              <button
                onClick={() => handleTitleClick(paper)}
                className="text-left w-full group"
              >
                <h4
                  className="font-display font-medium text-sm leading-tight group-hover:underline"
                  style={{ color: 'var(--color-sepia)' }}
                >
                  {paper.title}
                </h4>
              </button>

              {/* Meta: Authors, Year, Citation, Venue */}
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                {paper.authors && paper.authors.length > 0 && (
                  <span
                    className="font-body text-xs"
                    style={{ color: 'var(--color-faint)' }}
                  >
                    {paper.authors.slice(0, 3).join(', ')}
                    {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
                  </span>
                )}

                {paper.year && (
                  <span
                    className="font-mono text-xs px-1.5 py-0.5 rounded"
                    style={{
                      background: 'rgba(184, 134, 11, 0.08)',
                      color: 'var(--color-muted)',
                    }}
                  >
                    {paper.year}
                  </span>
                )}

                {paper.citation_count !== undefined && (
                  <span
                    className="font-mono text-xs"
                    style={{ color: 'var(--color-muted)' }}
                  >
                    {paper.citation_count.toLocaleString()} citations
                  </span>
                )}

                {paper.venue && (
                  <span
                    className="font-body text-xs truncate max-w-[150px]"
                    style={{ color: 'var(--color-faint)' }}
                    title={paper.venue}
                  >
                    {paper.venue}
                  </span>
                )}
              </div>

              {/* TL;DR */}
              {paper.tldr && (
                <div
                  className="mt-2 p-2 rounded"
                  style={{ background: 'rgba(45, 90, 39, 0.06)' }}
                >
                  <p
                    className="font-quote text-xs italic"
                    style={{ color: 'var(--color-status-success)' }}
                  >
                    TL;DR: {paper.tldr}
                  </p>
                </div>
              )}

              {/* Add to Library Button */}
              <div className="mt-3 flex justify-end">
                <button
                  onClick={() => handleAddToLibrary(paper)}
                  disabled={isAdding || !!isAdded}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-medium text-xs font-medium transition-all"
                  style={{
                    background: isAdded
                      ? 'rgba(45, 90, 39, 0.1)'
                      : 'rgba(184, 134, 11, 0.08)',
                    color: isAdded
                      ? 'var(--color-status-success)'
                      : 'var(--color-amber)',
                    border: `1px solid ${isAdded ? 'rgba(45, 90, 39, 0.2)' : 'rgba(184, 134, 11, 0.15)'}`,
                  }}
                >
                  {isAdding ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      添加中...
                    </>
                  ) : isAdded ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      已添加
                    </>
                  ) : (
                    <>
                      <Plus className="w-3.5 h-3.5" />
                      加入文库
                    </>
                  )}
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}