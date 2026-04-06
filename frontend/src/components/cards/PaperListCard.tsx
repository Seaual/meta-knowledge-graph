// frontend/src/components/cards/PaperListCard.tsx
interface PaperItem {
  title: string
  authors?: string[]
  year?: number
  citation_count?: number
  doi?: string
}

interface Props {
  data: {
    query?: string
    papers: PaperItem[]
    count: number
  }
  onAction: (text: string) => void
}

// Truncate authors list with "et al." for overflow
function formatAuthors(authors?: string[]): string {
  if (!authors || authors.length === 0) return ''
  if (authors.length <= 3) {
    return authors.join(', ')
  }
  return `${authors.slice(0, 3).join(', ')} et al.`
}

export default function PaperListCard({ data, onAction }: Props) {
  const { query, papers, count } = data

  // Header title based on whether there's a search query
  const headerTitle = query ? `搜索结果：${query}` : '论文列表'

  return (
    <div className="my-2 rounded-xlarge animate-slide-up overflow-hidden"
      style={{
        background: 'rgba(250, 248, 245, 0.01)',
        backdropFilter: 'blur(2px)',
        WebkitBackdropFilter: 'blur(2px)',
        border: '1px solid rgba(184, 134, 11, 0.08)',
        boxShadow: '0 2px 8px rgba(44, 24, 16, 0.06)',
      }}
    >
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between"
        style={{
          background: 'rgba(245, 240, 232, 0.04)',
          borderBottom: '1px solid rgba(184, 134, 11, 0.06)',
        }}
      >
        <h3 className="font-display text-sm font-medium"
          style={{ color: 'var(--color-sepia)' }}
        >
          {headerTitle}
        </h3>
        {/* Count badge */}
        <span className="font-mono text-xs px-2 py-1 rounded-soft"
          style={{
            background: 'rgba(184, 134, 11, 0.08)',
            color: 'var(--color-amber)',
          }}
        >
          {count} 篇
        </span>
      </div>

      {/* Paper list */}
      <div className="max-h-[320px] overflow-y-auto">
        {papers.length === 0 ? (
          <div className="py-8 text-center"
            style={{ color: 'var(--color-muted)' }}
          >
            <p className="font-body text-sm">暂无论文结果</p>
          </div>
        ) : (
          papers.map((paper, index) => (
            <div
              key={`${paper.title}-${index}`}
              className="px-4 py-3 flex items-start gap-3 cursor-pointer transition-all group"
              style={{
                borderBottom: index < papers.length - 1
                  ? '1px solid rgba(184, 134, 11, 0.04)'
                  : 'none',
              }}
              onClick={() => onAction(`详细介绍《${paper.title}》`)}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(184, 134, 11, 0.02)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
              }}
            >
              {/* Title - clickable */}
              <div className="flex-1 min-w-0">
                <p className="font-body text-sm leading-snug truncate group-hover:underline"
                  style={{ color: 'var(--color-ink)' }}
                  title={paper.title}
                >
                  {paper.title}
                </p>

                {/* Authors */}
                {paper.authors && paper.authors.length > 0 && (
                  <p className="font-body text-xs mt-1 truncate"
                    style={{ color: 'var(--color-muted)' }}
                    title={formatAuthors(paper.authors)}
                  >
                    {formatAuthors(paper.authors)}
                  </p>
                )}
              </div>

              {/* Year and citation count */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {paper.year && (
                  <span className="font-mono text-xs"
                    style={{ color: 'var(--color-muted)' }}
                  >
                    {paper.year}
                  </span>
                )}
                {paper.citation_count !== undefined && (
                  <span className="font-mono text-xs px-1.5 py-0.5 rounded-soft"
                    style={{
                      background: 'rgba(184, 134, 11, 0.06)',
                      color: 'var(--color-sepia)',
                    }}
                  >
                    {paper.citation_count} 引用
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}