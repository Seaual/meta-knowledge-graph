import { useEffect, useState } from 'react'
import { Search, ChevronRight, ChevronDown, FileText } from 'lucide-react'
import { conceptsApi } from '../lib/api'

interface Concept {
  id: string
  text: string
  category: string | null
  paper_count: number
  children?: Concept[]
  papers?: { doi: string; title: string }[]
}

export default function Concepts() {
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [tree, setTree] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Concept[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [selectedConcept, setSelectedConcept] = useState<Concept | null>(null)

  useEffect(() => {
    conceptsApi.tree().then(res => {
      setTree(res.data)
      setLoading(false)
    })
  }, [])

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }
    const res = await conceptsApi.search(searchQuery)
    setSearchResults(res.data)
  }

  const toggleExpand = (id: string) => {
    const newExpanded = new Set(expanded)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpanded(newExpanded)
  }

  const selectConcept = async (id: string) => {
    try {
      const res = await conceptsApi.get(id)
      setSelectedConcept(res.data)
    } catch (err) {
      console.error(err)
    }
  }

  const getCategoryIcon = (category: string | null) => {
    const icons: Record<string, string> = {
      field: '🌍',
      direction: '📚',
      method: '⚙️',
      technique: '🔧',
      detail: '📁',
    }
    return icons[category || 'method'] || '📄'
  }

  const renderTreeNode = (node: Concept, depth = 0) => {
    const hasChildren = node.children && node.children.length > 0
    const isExpanded = expanded.has(node.id)

    return (
      <div key={node.id} className="select-none">
        <div
          className={`flex items-center py-1 px-2 rounded hover:bg-gray-100 cursor-pointer ${
            selectedConcept?.id === node.id ? 'bg-blue-50' : ''
          }`}
          style={{ paddingLeft: depth * 20 + 8 }}
          onClick={() => selectConcept(node.id)}
        >
          {hasChildren && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                toggleExpand(node.id)
              }}
              className="mr-1"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-500" />
              )}
            </button>
          )}
          {!hasChildren && <span className="w-5" />}
          <span className="mr-2">{getCategoryIcon(node.category)}</span>
          <span className="flex-1">{node.text}</span>
          <span className="text-sm text-gray-500">({node.paper_count})</span>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {node.children!.map(child => renderTreeNode(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return <div className="text-center py-12">加载中...</div>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">概念浏览</h1>

      {/* Search */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="搜索概念..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          搜索
        </button>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">搜索结果</h2>
          <div className="space-y-2">
            {searchResults.map(concept => (
              <div
                key={concept.id}
                className="flex items-center p-2 rounded hover:bg-gray-50 cursor-pointer"
                onClick={() => selectConcept(concept.id)}
              >
                <span className="mr-2">{getCategoryIcon(concept.category)}</span>
                <span className="flex-1">{concept.text}</span>
                <span className="text-sm text-gray-500">({concept.paper_count})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tree View */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-4">概念树</h2>
          <div className="max-h-[600px] overflow-y-auto">
            {tree && renderTreeNode(tree)}
          </div>
        </div>

        {/* Detail View */}
        <div className="bg-white rounded-lg shadow p-4">
          {selectedConcept ? (
            <div>
              <h2 className="font-semibold text-lg flex items-center">
                <span className="mr-2">{getCategoryIcon(selectedConcept.category)}</span>
                {selectedConcept.text}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                类别: {selectedConcept.category || '-'}
              </p>
              <p className="text-sm text-gray-500">
                论文数: {selectedConcept.paper_count}
              </p>

              {/* Papers */}
              {selectedConcept.papers && selectedConcept.papers.length > 0 && (
                <div className="mt-4">
                  <h3 className="font-medium text-sm text-gray-700 mb-2">关联论文</h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {selectedConcept.papers.map(paper => (
                      <div
                        key={paper.doi}
                        className="flex items-start p-2 bg-gray-50 rounded text-sm"
                      >
                        <FileText className="h-4 w-4 mr-2 mt-0.5 text-gray-400 flex-shrink-0" />
                        <span className="line-clamp-2">{paper.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Children */}
              {selectedConcept.children && selectedConcept.children.length > 0 && (
                <div className="mt-4">
                  <h3 className="font-medium text-sm text-gray-700 mb-2">子概念</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedConcept.children.map(child => (
                      <span
                        key={child.id}
                        className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm cursor-pointer hover:bg-blue-200"
                        onClick={() => selectConcept(child.id)}
                      >
                        {child.text}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center text-gray-500 py-8">
              点击左侧概念查看详情
            </div>
          )}
        </div>
      </div>
    </div>
  )
}