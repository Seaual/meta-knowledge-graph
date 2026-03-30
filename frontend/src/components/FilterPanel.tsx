import { useState, useEffect, useRef } from 'react'
import { X, Search, RotateCcw } from 'lucide-react'
import { useTranslation } from '../i18n'

interface GraphNode {
  id: string
  name: string
  type: string
  category?: string
}

interface Props {
  searchQuery: string
  selectedCategories: string[]
  graphNodes: GraphNode[]
  onClose: () => void
  onSearch: (query: string) => void
  onCategoryChange: (categories: string[]) => void
  onFocusNode: (nodeId: string) => void
}

export default function FilterPanel({
  searchQuery,
  selectedCategories,
  graphNodes,
  onClose,
  onSearch,
  onCategoryChange,
  onFocusNode
}: Props) {
  const { t } = useTranslation()

  // Category colors - Academic Warm Palette
  const CATEGORIES = [
    { id: 'field', label: t.concepts.category.field, color: '#6b4423' },
    { id: 'direction', label: t.concepts.category.direction, color: '#b8860b' },
    { id: 'subdirection', label: t.concepts.category.subdirection, color: '#9a6b3c' },
    { id: 'task', label: t.concepts.category.task, color: '#4a6b8a' },
    { id: 'method', label: t.concepts.category.method, color: '#c2410c' },
    { id: 'technique', label: t.concepts.category.technique, color: '#2d5a27' },
  ]

  const [localQuery, setLocalQuery] = useState(searchQuery)
  const [searchResults, setSearchResults] = useState<GraphNode[]>([])
  const [showResults, setShowResults] = useState(false)
  const [localCategories, setLocalCategories] = useState<string[]>(selectedCategories)
  const [nodeCounts, setNodeCounts] = useState<Record<string, number>>({})
  const searchInputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  // Compute category counts
  useEffect(() => {
    const counts: Record<string, number> = {}
    graphNodes.forEach(node => {
      if (node.category) {
        counts[node.category] = (counts[node.category] || 0) + 1
      }
    })
    setNodeCounts(counts)
  }, [graphNodes])

  // Search logic
  useEffect(() => {
    if (!localQuery.trim()) {
      setSearchResults([])
      return
    }

    const query = localQuery.toLowerCase()
    const results = graphNodes
      .filter(node => node.name?.toLowerCase().includes(query))
      .slice(0, 10)

    setSearchResults(results)
  }, [localQuery, graphNodes])

  // Sync local categories with prop
  useEffect(() => {
    setLocalCategories(selectedCategories)
  }, [selectedCategories])

  // Focus search input on mount
  useEffect(() => {
    searchInputRef.current?.focus()
  }, [])

  const handleQueryChange = (query: string) => {
    setLocalQuery(query)
    onSearch(query)
  }

  const toggleCategory = (categoryId: string) => {
    const newCategories = localCategories.includes(categoryId)
      ? localCategories.filter(c => c !== categoryId)
      : [...localCategories, categoryId]
    setLocalCategories(newCategories)
    onCategoryChange(newCategories)
  }

  const handleReset = () => {
    setLocalQuery('')
    setSearchResults([])
    onSearch('')
    const allCategories = CATEGORIES.map(c => c.id)
    setLocalCategories(allCategories)
    onCategoryChange(allCategories)
  }

  const handleResultClick = (node: GraphNode) => {
    setShowResults(false)
    onFocusNode(node.id)
  }

  return (
    <div className="absolute top-4 right-4 z-20 w-72 card-academic overflow-hidden animate-slide-down">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-academic bg-vellum">
        <h3 className="font-display font-medium text-sepia">{t.concepts.filterPanel.title}</h3>
        <button
          onClick={onClose}
          className="w-6 h-6 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-academic relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input
            ref={searchInputRef}
            type="text"
            value={localQuery}
            onChange={e => handleQueryChange(e.target.value)}
            onFocus={() => setShowResults(true)}
            placeholder={t.concepts.filterPanel.searchPlaceholder}
            className="input-academic w-full pl-10 pr-4"
          />
        </div>

        {/* Search Results */}
        {showResults && searchResults.length > 0 && (
          <div
            ref={resultsRef}
            className="absolute left-4 right-4 mt-2 bg-vellum border border-academic rounded-large shadow-elevated max-h-64 overflow-y-auto z-30"
          >
            {searchResults.map(node => {
              const category = CATEGORIES.find(c => c.id === node.category)
              return (
                <button
                  key={node.id}
                  onClick={() => handleResultClick(node)}
                  className="w-full px-4 py-3 text-left hover:bg-paper flex items-center justify-between border-b border-academic last:border-b-0 transition-colors"
                >
                  <span className="font-body text-sm text-sepia">{node.name}</span>
                  {category && (
                    <span
                      className="badge-academic text-xs"
                      style={{
                        backgroundColor: category.color + '15',
                        color: category.color,
                        borderColor: category.color + '30',
                      }}
                    >
                      {category.label}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Category Filters */}
      <div className="p-4">
        <div className="font-mono text-xs text-muted uppercase tracking-wider mb-3">{t.concepts.filterPanel.categoryFilter}</div>
        <div className="space-y-1">
          {CATEGORIES.map(category => (
            <label
              key={category.id}
              className="flex items-center gap-3 cursor-pointer hover:bg-paper p-2 rounded-medium transition-colors"
            >
              <input
                type="checkbox"
                checked={localCategories.includes(category.id)}
                onChange={() => toggleCategory(category.id)}
                className="w-4 h-4 rounded border-academic accent-sepia"
              />
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: category.color }}
              />
              <span className="font-body text-sm text-sepia flex-1">{category.label}</span>
              <span className="font-mono text-xs text-faint">
                {nodeCounts[category.id] || 0}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Reset Button */}
      <div className="px-4 pb-4">
        <button
          onClick={handleReset}
          className="btn-ghost w-full flex items-center justify-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          {t.concepts.filterPanel.resetAll}
        </button>
      </div>
    </div>
  )
}