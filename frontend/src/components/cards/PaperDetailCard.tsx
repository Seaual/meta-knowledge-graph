import { useState } from 'react'
import { ChevronDown, ChevronUp, ExternalLink, BookOpen, Quote, Users } from 'lucide-react'
import { cn } from '../../lib/utils'

interface Props {
  data: {
    title: string
    authors?: string[]
    year?: number
    venue?: string
    abstract?: string | null
    tldr?: string | null
    keywords?: string[]
    contributions?: string[]
    citation_count?: number
    doi?: string
    s2_doi?: string
  }
}

// Sepia/amber tones for keyword tags
const KEYWORD_COLORS = [
  { bg: 'rgba(184, 134, 11, 0.12)', text: '#8b6914', border: 'rgba(184, 134, 11, 0.25)' },
  { bg: 'rgba(139, 90, 43, 0.12)', text: '#6b4423', border: 'rgba(139, 90, 43, 0.25)' },
  { bg: 'rgba(154, 107, 60, 0.12)', text: '#7a5530', border: 'rgba(154, 107, 60, 0.25)' },
  { bg: 'rgba(194, 120, 3, 0.12)', text: '#9a7203', border: 'rgba(194, 120, 3, 0.25)' },
  { bg: 'rgba(160, 82, 45, 0.12)', text: '#8b4513', border: 'rgba(160, 82, 45, 0.25)' },
]

export default function PaperDetailCard({ data }: Props) {
  const [isExpanded, setIsExpanded] = useState(false)

  const {
    title,
    authors,
    year,
    venue,
    abstract,
    tldr,
    keywords,
    contributions,
    citation_count,
    doi,
    s2_doi,
  } = data

  // Get the actual DOI to display/use
  const displayDoi = doi || s2_doi

  // Format authors with overflow
  const maxVisibleAuthors = 4
  const visibleAuthors = authors?.slice(0, maxVisibleAuthors) || []
  const overflowCount = authors ? authors.length - maxVisibleAuthors : 0

  const hasExpandableContent = abstract || (contributions && contributions.length > 0)

  return (
    <div
      className="rounded-xl overflow-hidden transition-all duration-200"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border-subtle)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b" style={{ borderColor: 'var(--color-border-subtle)' }}>
        {/* Title */}
        <h3
          className="font-display text-lg font-medium leading-tight mb-2"
          style={{ color: 'var(--color-ink)' }}
        >
          {title}
        </h3>

        {/* Meta row: year, venue, citations */}
        <div className="flex items-center gap-3 flex-wrap text-sm">
          {year && (
            <span
              className="font-mono text-xs px-2 py-0.5 rounded"
              style={{
                background: 'var(--color-overlay)',
                color: 'var(--color-ink-secondary)',
              }}
            >
              {year}
            </span>
          )}

          {venue && (
            <span
              className="flex items-center gap-1 text-xs"
              style={{ color: 'var(--color-ink-tertiary)' }}
            >
              <BookOpen className="w-3 h-3" />
              <span className="truncate max-w-[200px]" title={venue}>
                {venue}
              </span>
            </span>
          )}

          {citation_count !== undefined && citation_count > 0 && (
            <span
              className="flex items-center gap-1 text-xs font-medium"
              style={{ color: 'var(--color-accent)' }}
            >
              <Quote className="w-3 h-3" />
              {citation_count.toLocaleString()} citations
            </span>
          )}
        </div>
      </div>

      {/* TL;DR Section - Green highlighted box */}
      {tldr && (
        <div
          className="mx-5 mt-4 p-3 rounded-lg"
          style={{
            background: 'rgba(45, 90, 39, 0.08)',
            border: '1px solid rgba(45, 90, 39, 0.2)',
          }}
        >
          <div className="flex items-start gap-2">
            <span className="text-sm" style={{ color: '#2d5a27' }}>
              TL;DR
            </span>
          </div>
          <p
            className="text-sm mt-1 leading-relaxed"
            style={{ color: '#2d5a27' }}
          >
            {tldr}
          </p>
        </div>
      )}

      {/* Authors Section */}
      {authors && authors.length > 0 && (
        <div className="px-5 py-3">
          <div className="flex items-start gap-2">
            <Users className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: 'var(--color-ink-tertiary)' }} />
            <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
              {visibleAuthors.map((author, index) => (
                <span
                  key={index}
                  className="text-sm"
                  style={{ color: 'var(--color-ink-secondary)' }}
                >
                  {author}
                  {index < visibleAuthors.length - 1 && ','}
                </span>
              ))}
              {overflowCount > 0 && (
                <span
                  className="text-xs px-1.5 py-0.5 rounded cursor-default"
                  style={{
                    background: 'var(--color-overlay)',
                    color: 'var(--color-ink-tertiary)',
                  }}
                  title={authors.slice(maxVisibleAuthors).join(', ')}
                >
                  +{overflowCount} more
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Keywords Section - Sepia/amber tones */}
      {keywords && keywords.length > 0 && (
        <div className="px-5 py-3">
          <div className="flex flex-wrap gap-2">
            {keywords.map((keyword, index) => {
              const colorSet = KEYWORD_COLORS[index % KEYWORD_COLORS.length]
              return (
                <span
                  key={index}
                  className="text-xs px-2.5 py-1 rounded-full font-medium"
                  style={{
                    background: colorSet.bg,
                    color: colorSet.text,
                    border: `1px solid ${colorSet.border}`,
                  }}
                >
                  {keyword}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {/* Expandable Section */}
      {hasExpandableContent && (
        <div className="border-t" style={{ borderColor: 'var(--color-border-subtle)' }}>
          {/* Expand Toggle Button */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full px-5 py-2.5 flex items-center justify-between text-sm font-medium transition-colors"
            style={{
              color: 'var(--color-ink-tertiary)',
              background: isExpanded ? 'var(--color-overlay)' : 'transparent',
            }}
          >
            <span>Details</span>
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>

          {/* Expandable Content */}
          {isExpanded && (
            <div className="px-5 pb-4 space-y-4">
              {/* Abstract */}
              {abstract && (
                <div>
                  <h4
                    className="text-xs font-mono uppercase tracking-wider mb-2"
                    style={{ color: 'var(--color-ink-muted)' }}
                  >
                    Abstract
                  </h4>
                  <p
                    className="text-sm leading-relaxed"
                    style={{ color: 'var(--color-ink-secondary)' }}
                  >
                    {abstract}
                  </p>
                </div>
              )}

              {/* Contributions */}
              {contributions && contributions.length > 0 && (
                <div>
                  <h4
                    className="text-xs font-mono uppercase tracking-wider mb-2"
                    style={{ color: 'var(--color-ink-muted)' }}
                  >
                    Key Contributions
                  </h4>
                  <ul className="space-y-1.5">
                    {contributions.map((contribution, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 text-sm"
                        style={{ color: 'var(--color-ink-secondary)' }}
                      >
                        <span
                          className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                          style={{ background: 'var(--color-accent)' }}
                        />
                        {contribution}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Footer - DOI Link */}
      {displayDoi && (
        <div
          className="px-5 py-3 border-t flex items-center justify-between"
          style={{ borderColor: 'var(--color-border-subtle)', background: 'var(--color-overlay)' }}
        >
          <div className="flex items-center gap-2">
            <span
              className="font-mono text-xs px-2 py-1 rounded"
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-ink-secondary)',
              }}
            >
              DOI: {displayDoi}
            </span>
          </div>

          <a
            href={`https://doi.org/${displayDoi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-150 hover:translate-y-[-1px]"
            style={{
              color: 'white',
              background: 'var(--color-accent)',
            }}
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View Paper
          </a>
        </div>
      )}
    </div>
  )
}