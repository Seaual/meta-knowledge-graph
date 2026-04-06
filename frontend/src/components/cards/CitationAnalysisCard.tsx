// frontend/src/components/cards/CitationAnalysisCard.tsx
import { BookOpen, ExternalLink, Quote } from 'lucide-react'
import { cn } from '../../lib/utils'

interface CitationItem {
  title?: string
  year?: number
  citation_count?: number
  is_internal?: boolean
  paper_id?: string
}

interface Props {
  data: {
    paper?: {
      title: string
      doi?: string
      citation_count?: number
    }
    paper_title?: string
    citations: CitationItem[]
    citation_count: number
  }
}

function CitationItemRow({ citation }: { citation: CitationItem }) {
  const isInternal = citation.is_internal

  return (
    <div
      className={cn(
        'flex items-start gap-3 py-3 px-3 rounded-medium transition-colors',
        isInternal
          ? 'bg-green-50/50 border border-green-100/50 hover:bg-green-50/80'
          : 'hover:bg-gray-50/50'
      )}
    >
      {/* Indicator dot */}
      <div
        className={cn(
          'w-2 h-2 rounded-full mt-1.5 flex-shrink-0',
          isInternal ? 'bg-green-500' : 'bg-gray-300'
        )}
      />

      {/* Citation content */}
      <div className="flex-1 min-w-0">
        {/* Title */}
        <p
          className={cn(
            'text-sm font-medium truncate',
            isInternal ? 'text-green-800' : 'text-gray-800'
          )}
          title={citation.title}
        >
          {citation.title || 'Unknown Title'}
        </p>

        {/* Metadata row */}
        <div className="flex items-center gap-3 mt-1">
          {citation.year && (
            <span className="text-xs text-gray-500">{citation.year}</span>
          )}
          {citation.citation_count !== undefined && citation.citation_count > 0 && (
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Quote className="w-3 h-3" />
              {citation.citation_count}
            </span>
          )}
          {isInternal && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700">
              库内
            </span>
          )}
        </div>
      </div>

      {/* External link for internal papers */}
      {isInternal && citation.paper_id && (
        <ExternalLink className="w-4 h-4 text-green-600 flex-shrink-0 opacity-50 hover:opacity-100 transition-opacity cursor-pointer" />
      )}
    </div>
  )
}

export default function CitationAnalysisCard({ data }: Props) {
  const paperTitle = data.paper?.title || data.paper_title || 'Unknown Paper'
  const totalCitations = data.citation_count

  // Separate citations into internal and external
  const internalCitations = data.citations.filter((c) => c.is_internal === true)
  const externalCitations = data.citations.filter((c) => c.is_internal !== true)

  // Limit external citations to 10
  const displayedExternalCitations = externalCitations.slice(0, 10)
  const hiddenExternalCount = externalCitations.length - displayedExternalCitations.length

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border-subtle)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3"
        style={{
          borderBottom: '1px solid var(--color-border-subtle)',
          background: 'var(--color-overlay)',
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" style={{ color: 'var(--color-accent)' }} />
            <span
              className="font-medium text-sm"
              style={{ color: 'var(--color-ink)' }}
            >
              引用分析
            </span>
          </div>
          <span
            className="text-xs px-2 py-0.5 rounded"
            style={{
              background: 'var(--color-highlight-soft)',
              color: '#8a6d1b',
            }}
          >
            {totalCitations} 条引用
          </span>
        </div>
        {/* Paper title */}
        <p
          className="mt-2 text-sm truncate"
          style={{ color: 'var(--color-ink-secondary)' }}
          title={paperTitle}
        >
          {paperTitle}
        </p>
      </div>

      {/* Citations list */}
      <div className="max-h-80 overflow-y-auto">
        {/* Internal citations section */}
        {internalCitations.length > 0 && (
          <div>
            <div
              className="px-4 py-2 flex items-center gap-2"
              style={{
                background: 'rgba(34, 197, 94, 0.05)',
                borderBottom: '1px solid rgba(34, 197, 94, 0.1)',
              }}
            >
              <span className="text-xs font-medium text-green-700">
                库内论文
              </span>
              <span className="text-xs text-green-600">
                ({internalCitations.length})
              </span>
            </div>
            <div className="px-2 py-1">
              {internalCitations.map((citation, index) => (
                <CitationItemRow key={`internal-${index}`} citation={citation} />
              ))}
            </div>
          </div>
        )}

        {/* External citations section */}
        {displayedExternalCitations.length > 0 && (
          <div>
            <div
              className="px-4 py-2 flex items-center gap-2"
              style={{
                background: 'var(--color-overlay)',
                borderBottom: '1px solid var(--color-border-subtle)',
              }}
            >
              <span
                className="text-xs font-medium"
                style={{ color: 'var(--color-ink-tertiary)' }}
              >
                外部论文
              </span>
              <span
                className="text-xs"
                style={{ color: 'var(--color-ink-muted)' }}
              >
                ({externalCitations.length})
              </span>
            </div>
            <div className="px-2 py-1">
              {displayedExternalCitations.map((citation, index) => (
                <CitationItemRow key={`external-${index}`} citation={citation} />
              ))}
            </div>

            {/* Hidden citations message */}
            {hiddenExternalCount > 0 && (
              <div
                className="px-4 py-2 text-center"
                style={{
                  background: 'var(--color-overlay)',
                  borderTop: '1px solid var(--color-border-subtle)',
                }}
              >
                <span
                  className="text-xs"
                  style={{ color: 'var(--color-ink-tertiary)' }}
                >
                  还有 {hiddenExternalCount} 条引用未显示
                </span>
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {data.citations.length === 0 && (
          <div
            className="px-4 py-8 text-center"
            style={{ color: 'var(--color-ink-muted)' }}
          >
            <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">暂无引用数据</p>
          </div>
        )}
      </div>
    </div>
  )
}