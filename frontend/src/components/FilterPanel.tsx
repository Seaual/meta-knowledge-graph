import { useState, useEffect, useRef } from 'react'
import { X, Search, RotateCcw } from 'lucide-react'

interface Concept {
  id: string
  text: string
  category: string | null | undefined
  paper_count: number
}

interface Props {
  concepts: Concept[]
  onClose: () => void
  onSearch: (query: string) => void
  onCategoryChange: (categories: string[]) => void
  onFocusNode: (nodeId: string) => void
}

const CATEGORIES = [
  { id: 'field', label: '领域', color: '#FF6B6B' },
  { id: 'direction', label: '方向', color: '#4ECDC4' },
  { id: 'subdirection', label: '子方向', color: '#45B7D1' },
  { id: 'task', label: '任务', color: '#96CEB4' },
  { id: 'method', label: '方法', color: '#FFA726' },
  { id: 'technique', label: '技术', color: '#FFD93D' },
]

export default function FilterPanel({
  concepts,
  onClose,
  onSearch,
  onCategoryChange,
  onFocusNode
}: Props) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Concept[]>([])
  const [showResults, setShowResults] = useState(false)
  const [selectedCategories, setSelectedCategories] = useState<string[]>(
    CATEGORIES.map(c => c.id)
  )
  const [conceptCounts, setConceptCounts] = useState<Record<string, number>>({})
  const searchInputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  // 计算每个 category 的概念数量
  useEffect(() => {
    const counts: Record<string, number> = {}
    concepts.forEach(c => {
      if (c.category) {
        counts[c.category] = (counts[c.category] || 0) + 1
      }
    })
    setConceptCounts(counts)
  }, [concepts])

  // 搜索逻辑
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      onSearch('')
      return
    }

    const query = searchQuery.toLowerCase()
    const results = concepts
      .filter(c => c.text.toLowerCase().includes(query))
      .slice(0, 10)

    setSearchResults(results)
    onSearch(searchQuery)
  }, [searchQuery, concepts, onSearch])

  // Category 变化通知
  useEffect(() => {
    onCategoryChange(selectedCategories)
  }, [selectedCategories, onCategoryChange])

  // 聚焦搜索框
  useEffect(() => {
    searchInputRef.current?.focus()
  }, [])

  const toggleCategory = (categoryId: string) => {
    setSelectedCategories(prev =>
      prev.includes(categoryId)
        ? prev.filter(c => c !== categoryId)
        : [...prev, categoryId]
    )
  }

  const handleReset = () => {
    setSearchQuery('')
    setSearchResults([])
    setSelectedCategories(CATEGORIES.map(c => c.id))
  }

  const handleResultClick = (concept: Concept) => {
    setShowResults(false)
    onFocusNode(concept.id)
  }

  return (
    <div className="absolute top-4 right-4 z-20 w-72 bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-brand-gradient border-b border-brand">
        <h3 className="font-semibold text-brand-700">筛选</h3>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-gray-100">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onFocus={() => setShowResults(true)}
            placeholder="搜索概念..."
            className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
        </div>

        {/* Search Results */}
        {showResults && searchResults.length > 0 && (
          <div
            ref={resultsRef}
            className="absolute left-4 right-4 mt-2 bg-white border border-gray-200 rounded-xl shadow-lg max-h-64 overflow-y-auto z-30"
          >
            {searchResults.map(concept => {
              const category = CATEGORIES.find(c => c.id === concept.category)
              return (
                <button
                  key={concept.id}
                  onClick={() => handleResultClick(concept)}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center justify-between border-b border-gray-100 last:border-b-0"
                >
                  <span className="text-sm text-gray-700">{concept.text}</span>
                  {category && (
                    <span
                      className="text-xs px-2 py-0.5 rounded-full text-white"
                      style={{ backgroundColor: category.color }}
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
        <div className="text-xs font-medium text-gray-500 mb-3">Category 过滤</div>
        <div className="space-y-2">
          {CATEGORIES.map(category => (
            <label
              key={category.id}
              className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition-colors"
            >
              <input
                type="checkbox"
                checked={selectedCategories.includes(category.id)}
                onChange={() => toggleCategory(category.id)}
                className="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: category.color }}
              />
              <span className="text-sm text-gray-700 flex-1">{category.label}</span>
              <span className="text-xs text-gray-400">
                {conceptCounts[category.id] || 0}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Reset Button */}
      <div className="px-4 pb-4">
        <button
          onClick={handleReset}
          className="w-full py-2.5 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded-xl transition-colors flex items-center justify-center gap-2"
        >
          <RotateCcw className="h-4 w-4" />
          重置全部
        </button>
      </div>
    </div>
  )
}