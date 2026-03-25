// Knowledge Graph - Obsidian-style Canvas Force Graph with Papers
import { useEffect, useRef, useState, useCallback } from 'react'
import ForceGraph from 'force-graph'
import { forceManyBody, forceLink, forceCollide } from 'd3-force'
import { conceptsApi, graphApi, papersApi, exportApi, foldersApi } from '../lib/api'
import { Download, ChevronDown, Folder } from 'lucide-react'
import DedupPanel from '../components/DedupPanel'

// Types
interface Concept {
  id: string
  text: string
  category: string | null
  paper_count: number
  parents?: Concept[]
  children?: Concept[]
  papers?: { doi: string; title: string }[]
}

interface Paper {
  doi: string
  title: string
  authors: string[]
  keywords: string[]
  contributions: string[]
  abstract: string | null
  status: string
}

interface GraphEdge {
  source: string
  target: string
}

// Node types
type NodeType = 'concept' | 'paper' | 'center'

interface GraphNode {
  id: string
  name: string
  type: NodeType
  category?: string
  paperCount?: number
  depth?: number
  // Paper specific
  authors?: string[]
  keywords?: string[]
  abstract?: string | null
  doi?: string
  // Runtime properties added by force-graph
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number
  fy?: number
}

// Category colors
const CATEGORY_COLORS: Record<string, string> = {
  field: '#FF6B6B',
  direction: '#4ECDC4',
  subdirection: '#45B7D1',
  task: '#96CEB4',
  method: '#FFA726',
  technique: '#FFD93D',
}

const PAPER_COLOR = '#3B82F6'
const CENTER_COLOR = '#8B5CF6'

interface ResearchPoint {
  title: string
  description: string
  rationale: string
  related_concepts: string[]
  difficulty: 'easy' | 'medium' | 'hard' | 'unknown'
  potential_impact: 'low' | 'medium' | 'high' | 'unknown'
}

interface ResearchPointsResponse {
  concept_id: string
  concept_name: string
  research_points: ResearchPoint[]
  analysis_context: {
    concept: { id: string; name: string; category?: string }
    ancestors: { id: string; name: string; category?: string }[]
    descendants: { id: string; name: string; category?: string; depth?: number }[]
    edge_nodes: { id: string; name: string; category?: string }[]
    related_papers: { title: string; keywords?: string[] }[]
  }
}

export default function ConceptsGraph() {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)

  const [loading, setLoading] = useState(true)
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [edges, setEdges] = useState<GraphEdge[]>([])

  // View state
  const [viewMode, setViewMode] = useState<'all' | 'concept'>('all')
  const [selectedConcept, setSelectedConcept] = useState<Concept | null>(null)
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null)
  const [showConceptActions, setShowConceptActions] = useState(false)

  // Dedup panel state
  const [dedupOpen, setDedupOpen] = useState(false)

  // Export menu state
  const [showExportMenu, setShowExportMenu] = useState(false)

  // Folder state
  const [folders, setFolders] = useState<{ id: string; name: string }[]>([])
  const [activeFolder, setActiveFolder] = useState('default')
  const [showFolderMenu, setShowFolderMenu] = useState(false)

  // Research points state
  const [researchPoints, setResearchPoints] = useState<ResearchPointsResponse | null>(null)
  const [loadingResearchPoints, setLoadingResearchPoints] = useState(false)
  const [showResearchPanel, setShowResearchPanel] = useState(false)

  // Force settings
  const [forceStrength, setForceStrength] = useState(150)

  // Graph data
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([])
  const [graphLinks, setGraphLinks] = useState<{ source: string; target: string }[]>([])

  // Load folders
  const loadFolders = () => {
    foldersApi.list().then(res => {
      setFolders(res.data)
    })
  }

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        const [conceptsRes, graphRes] = await Promise.all([
          conceptsApi.list(),
          graphApi.data(),
        ])
        setConcepts(conceptsRes.data)
        setEdges(graphRes.data.edges)
        setLoading(false)
      } catch (err) {
        console.error('Failed to load:', err)
        setLoading(false)
      }
    }
    loadData()
    loadFolders()
  }, [])

  // Compute depth for each node
  const getNodeDepth = useCallback((nodeId: string, parentMap: Map<string, string>): number => {
    const visited = new Set<string>()
    let depth = 0
    let current = nodeId
    while (parentMap.has(current) && !visited.has(current)) {
      visited.add(current)
      depth++
      current = parentMap.get(current)!
    }
    return depth
  }, [])

  // Build initial graph data
  useEffect(() => {
    if (loading || concepts.length === 0) return

    const parentMap = new Map<string, string>()
    edges.forEach(e => parentMap.set(e.target, e.source))

    const nodes: GraphNode[] = concepts.map(c => ({
      id: c.id,
      name: c.text,
      type: 'concept' as NodeType,
      category: c.category || 'method',
      paperCount: c.paper_count,
      depth: getNodeDepth(c.id, parentMap),
    }))

    const links = edges.map(e => ({
      source: e.source,
      target: e.target,
    }))

    setGraphNodes(nodes)
    setGraphLinks(links)
    setViewMode('all')
  }, [loading, concepts, edges, getNodeDepth])

  // Handle concept click - show action panel
  const handleConceptClick = useCallback(async (node: GraphNode) => {
    if (node.type !== 'concept') return

    try {
      const res = await conceptsApi.get(node.id)
      setSelectedConcept(res.data)
      setShowConceptActions(true)
      setShowResearchPanel(false)
    } catch (err) {
      console.error('Failed to get concept:', err)
    }
  }, [])

  // Enter paper view
  const handleViewPapers = useCallback(async () => {
    if (!selectedConcept) return

    const papers = selectedConcept.papers || []
    if (papers.length === 0) return

    setShowConceptActions(false)

    // Build new graph with concept at center and papers around
    const centerNode: GraphNode = {
      id: `center-${selectedConcept.id}`,
      name: selectedConcept.text,
      type: 'center',
      category: selectedConcept.category ?? undefined,
      paperCount: selectedConcept.paper_count,
    }

    const paperNodes: GraphNode[] = papers.map((p: { doi: string; title: string }) => ({
      id: `paper-${p.doi}`,
      name: p.title,
      type: 'paper' as NodeType,
      doi: p.doi,
    }))

    const paperLinks = papers.map((p: { doi: string }) => ({
      source: centerNode.id,
      target: `paper-${p.doi}`,
    }))

    setGraphNodes([centerNode, ...paperNodes])
    setGraphLinks(paperLinks)
    setViewMode('concept')
  }, [selectedConcept])

  // Handle paper click - show details
  const handlePaperClick = useCallback(async (node: GraphNode) => {
    if (node.type !== 'paper' || !node.doi) return

    try {
      const res = await papersApi.get(node.doi)
      setSelectedPaper(res.data)
    } catch (err) {
      console.error('Failed to get paper:', err)
    }
  }, [])

  // Discover research points
  const handleDiscoverResearchPoints = useCallback(async () => {
    if (!selectedConcept) return

    setShowConceptActions(false)
    setLoadingResearchPoints(true)
    setShowResearchPanel(true)
    setResearchPoints(null)

    try {
      const res = await conceptsApi.researchPoints(selectedConcept.id)
      setResearchPoints(res.data)
    } catch (err) {
      console.error('Failed to get research points:', err)
      setResearchPoints({
        concept_id: selectedConcept.id,
        concept_name: selectedConcept.text,
        research_points: [{
          title: '分析失败',
          description: '无法获取研究点，请检查LLM配置或稍后重试',
          rationale: String(err),
          related_concepts: [],
          difficulty: 'unknown',
          potential_impact: 'unknown',
        }],
        analysis_context: {
          concept: { id: selectedConcept.id, name: selectedConcept.text },
          ancestors: [],
          descendants: [],
          edge_nodes: [],
          related_papers: [],
        },
      })
    } finally {
      setLoadingResearchPoints(false)
    }
  }, [selectedConcept])

  const handleExportMarkdown = useCallback(async () => {
    try {
      const res = await exportApi.download()
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `knowledge-graph-${new Date().toISOString().split('T')[0]}.md`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
      alert('导出失败')
    }
  }, [])

  const handleExportCanvas = useCallback(async () => {
    try {
      const res = await exportApi.downloadCanvas()
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `knowledge-graph-${new Date().toISOString().split('T')[0]}.canvas`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Canvas export failed:', err)
      alert('导出失败')
    }
  }, [])

  const handleExportHtml = useCallback(async () => {
    try {
      const res = await exportApi.downloadHtml()
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `knowledge-graph-${new Date().toISOString().split('T')[0]}.html`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('HTML export failed:', err)
      alert('导出失败')
    }
  }, [])

  // Back to all concepts
  const handleBack = useCallback(() => {
    const parentMap = new Map<string, string>()
    edges.forEach(e => parentMap.set(e.target, e.source))

    const nodes: GraphNode[] = concepts.map(c => ({
      id: c.id,
      name: c.text,
      type: 'concept' as NodeType,
      category: c.category || 'method',
      paperCount: c.paper_count,
      depth: getNodeDepth(c.id, parentMap),
    }))

    const links = edges.map(e => ({
      source: e.source,
      target: e.target,
    }))

    setGraphNodes(nodes)
    setGraphLinks(links)
    setViewMode('all')
    setSelectedConcept(null)
    setSelectedPaper(null)
    setResearchPoints(null)
    setShowResearchPanel(false)
    setShowConceptActions(false)
  }, [concepts, edges, getNodeDepth])

  // Initialize/update graph
  useEffect(() => {
    if (!containerRef.current || graphNodes.length === 0) return

    // Cleanup previous graph
    if (graphRef.current) {
      graphRef.current._destructor()
    }

    const graph = new ForceGraph(containerRef.current!)
      .graphData({ nodes: graphNodes, links: graphLinks })
      .nodeId('id')
      .nodeLabel('name')
      .nodeVal((node: any) => {
        if (node.type === 'center') return 3
        if (node.type === 'paper') return 1.5
        return 1 + Math.sqrt(node.paperCount || 0) * 0.3
      })
      .nodeCanvasObject((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const isPaper = node.type === 'paper'
        const isCenter = node.type === 'center'

        let size: number
        let color: string

        if (isCenter) {
          size = 20
          color = CENTER_COLOR
        } else if (isPaper) {
          size = 8
          color = PAPER_COLOR
        } else {
          size = 6 + (6 - Math.min(node.depth || 3, 5)) + Math.sqrt(node.paperCount || 0) * 0.5
          color = CATEGORY_COLORS[node.category || 'method'] || '#94A3B8'
        }

        const x = node.x || 0
        const y = node.y || 0

        // Draw outer circle
        ctx.beginPath()
        ctx.arc(x, y, size, 0, 2 * Math.PI)

        if (isPaper) {
          // Paper: solid blue circle with document icon effect
          ctx.fillStyle = color + '40'
          ctx.fill()
          ctx.strokeStyle = color
          ctx.lineWidth = 2.5
          ctx.stroke()

          // Inner dot
          ctx.beginPath()
          ctx.arc(x, y, size * 0.35, 0, 2 * Math.PI)
          ctx.fillStyle = color
          ctx.fill()
        } else if (isCenter) {
          // Center concept: larger with gradient
          const gradient = ctx.createRadialGradient(x, y, 0, x, y, size)
          gradient.addColorStop(0, color + '60')
          gradient.addColorStop(1, color + '20')
          ctx.fillStyle = gradient
          ctx.fill()
          ctx.strokeStyle = color
          ctx.lineWidth = 3
          ctx.stroke()

          // Inner circle
          ctx.beginPath()
          ctx.arc(x, y, size * 0.5, 0, 2 * Math.PI)
          ctx.fillStyle = color
          ctx.fill()
        } else {
          // Regular concept
          ctx.fillStyle = color + '30'
          ctx.fill()
          ctx.strokeStyle = color
          ctx.lineWidth = 2 / globalScale
          ctx.stroke()

          // Inner dot
          ctx.beginPath()
          ctx.arc(x, y, size * 0.3, 0, 2 * Math.PI)
          ctx.fillStyle = color
          ctx.fill()
        }

        // Draw label when zoomed in
        if (globalScale > 0.5) {
          const fontSize = isCenter ? 14 : 11
          ctx.font = `${fontSize / globalScale}px Inter, sans-serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'top'
          ctx.fillStyle = '#374151'
          const label = node.name && node.name.length > 30 ? node.name.substring(0, 30) + '...' : (node.name || '')
          ctx.fillText(label, x, y + size + 4 / globalScale)
        }
      })
      .linkColor((link: any) => {
        const source = link.source
        if (source.type === 'center') return PAPER_COLOR + '60'
        return '#CBD5E1'
      })
      .linkWidth((link: any) => {
        const source = link.source
        return source.type === 'center' ? 2 : 1
      })
      .linkDirectionalParticles((link: any) => {
        const source = link.source
        return source.type === 'center' ? 3 : 2
      })
      .linkDirectionalParticleWidth(2)
      .linkDirectionalParticleColor(() => '#3B82F6')
      .d3AlphaDecay(0.005)
      .d3VelocityDecay(0.4)
      .d3Force('charge', forceManyBody().strength((node: any) => {
        // 斥力按层级递增：层级越深（depth越大），斥力越大
        if (node.type === 'paper') return -forceStrength * 0.5
        if (node.type === 'center') return -forceStrength * 2
        const depthBonus = -(node.depth || 0) * 30
        return -forceStrength + depthBonus
      }))
      .d3Force('link', forceLink().id((d: any) => d.id).distance(60).strength(0.5))
      .d3Force('collision', forceCollide().radius((node: any) => {
        if (node.type === 'paper') return 15
        if (node.type === 'center') return 30
        return 20 + (node.depth || 0) * 3
      }))
      .onNodeClick((node: any) => {
        if (!node) return
        setHoverNode(null)
        if (node.type === 'concept') {
          if (viewMode === 'all') {
            handleConceptClick(node)
          }
        } else if (node.type === 'paper') {
          handlePaperClick(node)
        }
      })
      .onNodeHover((node: any) => {
        setHoverNode(node)
        if (containerRef.current) {
          containerRef.current.style.cursor = node ? 'pointer' : 'default'
        }
      })
      .cooldownTicks(100)
      .onEngineStop(() => graph.zoomToFit(400, 100))

    graphRef.current = graph

    return () => {
      if (graphRef.current) {
        graphRef.current._destructor()
      }
    }
  }, [graphNodes, graphLinks, viewMode, handleConceptClick, handlePaperClick, forceStrength])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto" />
          <p className="mt-4 text-gray-500">加载知识图谱...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full relative">
      {/* Graph Canvas */}
      <div ref={containerRef} className="w-full h-full" />

      {/* Top Bar */}
      <div className="absolute top-4 left-4 z-10">
        {viewMode === 'concept' && (
          <button
            onClick={handleBack}
            className="flex items-center gap-2 px-4 py-2 bg-white/90 backdrop-blur rounded-xl shadow-lg text-sm font-medium text-gray-700 hover:bg-white transition-colors"
          >
            ← 返回全部概念
          </button>
        )}
      </div>

      {/* Action Buttons */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        {/* Folder Selector */}
        <div className="relative">
          <button
            onClick={() => setShowFolderMenu(!showFolderMenu)}
            className="flex items-center gap-2 px-4 py-2 bg-white/90 backdrop-blur rounded-xl shadow-lg text-sm font-medium text-gray-700 hover:bg-white transition-colors"
          >
            <Folder className="h-4 w-4" />
            {folders.find(f => f.id === activeFolder)?.name || '默认'}
            <ChevronDown className="h-4 w-4" />
          </button>
          {showFolderMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden z-20">
              {folders.map(folder => (
                <button
                  key={folder.id}
                  onClick={() => {
                    setActiveFolder(folder.id)
                    setShowFolderMenu(false)
                  }}
                  className={`w-full text-left px-4 py-2.5 text-sm hover:bg-blue-50 flex items-center gap-2 ${
                    activeFolder === folder.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                  }`}
                >
                  <Folder className="h-4 w-4" />
                  {folder.name}
                </button>
              ))}
            </div>
          )}
        </div>
        {/* Export Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            className="flex items-center gap-2 px-4 py-2 bg-white/90 backdrop-blur rounded-xl shadow-lg text-sm font-medium text-gray-700 hover:bg-white transition-colors"
          >
            <Download className="h-4 w-4" />
            导出
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showExportMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden z-20">
              <button
                onClick={() => { handleExportHtml(); setShowExportMenu(false); }}
                className="w-full px-4 py-3 text-left text-sm text-gray-700 hover:bg-blue-50 flex items-center gap-3"
              >
                <span className="text-lg">🌐</span>
                <div>
                  <div className="font-medium">HTML 页面</div>
                  <div className="text-xs text-gray-400">交互式物理渲染</div>
                </div>
              </button>
              <button
                onClick={() => { handleExportCanvas(); setShowExportMenu(false); }}
                className="w-full px-4 py-3 text-left text-sm text-gray-700 hover:bg-purple-50 flex items-center gap-3"
              >
                <span className="text-lg">🎨</span>
                <div>
                  <div className="font-medium">Canvas 格式</div>
                  <div className="text-xs text-gray-400">带颜色和布局</div>
                </div>
              </button>
              <button
                onClick={() => { handleExportMarkdown(); setShowExportMenu(false); }}
                className="w-full px-4 py-3 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3"
              >
                <span className="text-lg">📝</span>
                <div>
                  <div className="font-medium">Markdown 格式</div>
                  <div className="text-xs text-gray-400">纯文本双链</div>
                </div>
              </button>
            </div>
          )}
        </div>
        <button
          onClick={() => setDedupOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-white/90 backdrop-blur rounded-xl shadow-lg text-sm font-medium text-gray-700 hover:bg-white transition-colors"
        >
          🔄 去重扫描
        </button>
      </div>

      {/* Info Panel */}
      <div className="absolute bottom-16 left-4 bg-white/90 backdrop-blur rounded-xl shadow-lg p-3 z-10">
        <div className="text-xs text-gray-500">
          {viewMode === 'all' ? '知识图谱' : '概念详情'}
        </div>
        <div className="font-bold text-gray-900">
          {viewMode === 'all' ? `${concepts.length} 个概念` : selectedConcept?.text}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {viewMode === 'all'
            ? '点击概念查看操作'
            : '点击论文查看详情'
          }
        </div>
        {/* Force Strength Slider */}
        <div className="mt-3 pt-3 border-t border-gray-200">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500">节点斥力</span>
            <span className="text-xs font-medium text-gray-700">{forceStrength}</span>
          </div>
          <input
            type="range"
            min="50"
            max="400"
            value={forceStrength}
            onChange={(e) => setForceStrength(Number(e.target.value))}
            className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />
          <div className="flex justify-between text-[10px] text-gray-400 mt-1">
            <span>紧凑</span>
            <span>分散</span>
          </div>
        </div>
      </div>

      {/* Concept Action Panel - 点击概念后显示 */}
      {showConceptActions && selectedConcept && (
        <div className="absolute top-4 right-4 bg-white rounded-xl shadow-xl border border-gray-100 p-4 z-20 w-72">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="font-bold text-gray-900 text-sm">{selectedConcept.text}</h3>
              <div className="flex items-center gap-2 mt-1">
                {selectedConcept.category && (
                  <span
                    className="px-2 py-0.5 rounded text-xs font-medium"
                    style={{
                      backgroundColor: CATEGORY_COLORS[selectedConcept.category] + '20',
                      color: CATEGORY_COLORS[selectedConcept.category],
                    }}
                  >
                    {selectedConcept.category}
                  </span>
                )}
                <span className="text-xs text-gray-500">{selectedConcept.paper_count || 0} 篇论文</span>
              </div>
            </div>
            <button
              onClick={() => {
                setShowConceptActions(false)
                setSelectedConcept(null)
              }}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
          <div className="space-y-2">
            <button
              onClick={handleDiscoverResearchPoints}
              className="w-full px-4 py-2.5 bg-gradient-to-r from-purple-500 to-blue-500 text-white text-sm font-medium rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all flex items-center justify-center gap-2"
            >
              🔍 发现研究点
            </button>
            {selectedConcept.papers && selectedConcept.papers.length > 0 && (
              <button
                onClick={handleViewPapers}
                className="w-full px-4 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-all flex items-center justify-center gap-2"
              >
                📄 查看相关论文 ({selectedConcept.papers.length})
              </button>
            )}
          </div>
        </div>
      )}

      {/* Hover Tooltip - 简单显示 */}
      {hoverNode && !showConceptActions && (
        <div className="absolute top-4 right-4 bg-white/90 backdrop-blur rounded-xl shadow-lg p-3 z-10 max-w-xs pointer-events-none">
          <div className="font-semibold text-gray-900 text-sm">
            {hoverNode.name}
          </div>
          <div className="flex items-center gap-2 mt-1">
            {hoverNode.type === 'paper' ? (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-600">
                论文
              </span>
            ) : hoverNode.type === 'center' ? (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-600">
                中心概念
              </span>
            ) : (
              <>
                <span
                  className="px-2 py-0.5 rounded text-xs font-medium"
                  style={{
                    backgroundColor: CATEGORY_COLORS[hoverNode.category || 'method'] + '20',
                    color: CATEGORY_COLORS[hoverNode.category || 'method'],
                  }}
                >
                  {hoverNode.category}
                </span>
                <span className="text-xs text-gray-500">L{hoverNode.depth}</span>
              </>
            )}
          </div>
          {hoverNode.type === 'concept' && (
            <div className="text-xs text-gray-400 mt-1">点击查看操作</div>
          )}
          {hoverNode.type === 'paper' && (
            <div className="text-xs text-gray-400 mt-1">点击查看详情</div>
          )}
        </div>
      )}

      {/* Paper Detail Panel */}
      {selectedPaper && (
        <div className="absolute bottom-20 right-4 w-96 bg-white rounded-xl shadow-xl border border-gray-100 z-20 max-h-[70vh] overflow-y-auto">
          <div className="p-4 border-b border-gray-100 sticky top-0 bg-white">
            <div className="flex items-start justify-between">
              <h3 className="font-bold text-gray-900 text-sm leading-tight pr-2">
                {selectedPaper.title}
              </h3>
              <button
                onClick={() => setSelectedPaper(null)}
                className="text-gray-400 hover:text-gray-600 flex-shrink-0"
              >
                ✕
              </button>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {/* DOI */}
            <div>
              <div className="text-xs font-semibold text-gray-400 mb-1">DOI</div>
              <div className="text-xs text-blue-500 break-all">{selectedPaper.doi}</div>
            </div>

            {/* Authors */}
            {selectedPaper.authors && selectedPaper.authors.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-gray-400 mb-1">作者</div>
                <div className="text-sm text-gray-700">
                  {selectedPaper.authors.slice(0, 5).join(', ')}
                  {selectedPaper.authors.length > 5 && (
                    <span className="text-gray-400"> +{selectedPaper.authors.length - 5} 人</span>
                  )}
                </div>
              </div>
            )}

            {/* Keywords */}
            {selectedPaper.keywords && selectedPaper.keywords.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-gray-400 mb-2">关键词</div>
                <div className="flex flex-wrap gap-1">
                  {selectedPaper.keywords.map((kw, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Abstract / Chinese Summary */}
            {selectedPaper.abstract && (
              <div>
                <div className="text-xs font-semibold text-gray-400 mb-1">摘要</div>
                <div className="text-sm text-gray-600 leading-relaxed">
                  {selectedPaper.abstract}
                </div>
              </div>
            )}

            {/* Contributions */}
            {selectedPaper.contributions && selectedPaper.contributions.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-gray-400 mb-2">主要贡献</div>
                <ul className="text-sm text-gray-600 space-y-1">
                  {selectedPaper.contributions.slice(0, 3).map((c, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-blue-500 mt-1">•</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Research Points Panel */}
      {showResearchPanel && (
        <div className="absolute top-20 left-4 w-[480px] bg-white rounded-xl shadow-xl border border-gray-100 z-20 max-h-[75vh] overflow-y-auto">
          <div className="p-4 border-b border-gray-100 sticky top-0 bg-white">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-bold text-gray-900 text-base">🔍 研究点发现</h3>
                <p className="text-xs text-gray-500 mt-1">
                  基于「{researchPoints?.concept_name || selectedConcept?.text}」的分析
                </p>
              </div>
              <button
                onClick={() => setShowResearchPanel(false)}
                className="text-gray-400 hover:text-gray-600 flex-shrink-0"
              >
                ✕
              </button>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {loadingResearchPoints ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-purple-500 border-t-transparent mx-auto" />
                  <p className="mt-3 text-sm text-gray-500">正在分析知识图谱...</p>
                  <p className="text-xs text-gray-400 mt-1">追溯上游节点，遍历边缘节点</p>
                </div>
              </div>
            ) : researchPoints ? (
              <>
                {/* Analysis Context Summary */}
                <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-3">
                  <div className="text-xs font-semibold text-gray-500 mb-2">分析上下文</div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <div className="text-lg font-bold text-purple-600">{researchPoints.analysis_context.ancestors.length}</div>
                      <div className="text-xs text-gray-500">上游节点</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-blue-600">{researchPoints.analysis_context.descendants.length}</div>
                      <div className="text-xs text-gray-500">下游节点</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-green-600">{researchPoints.analysis_context.edge_nodes.length}</div>
                      <div className="text-xs text-gray-500">边缘节点</div>
                    </div>
                  </div>
                </div>

                {/* Research Points */}
                <div className="space-y-3">
                  {researchPoints.research_points.map((point, i) => (
                    <div key={i} className="border border-gray-100 rounded-lg p-3 hover:border-purple-200 hover:bg-purple-50/30 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-semibold text-gray-900 text-sm">{point.title}</h4>
                        <div className="flex gap-1 flex-shrink-0">
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                            point.difficulty === 'easy' ? 'bg-green-100 text-green-600' :
                            point.difficulty === 'medium' ? 'bg-yellow-100 text-yellow-600' :
                            point.difficulty === 'hard' ? 'bg-red-100 text-red-600' :
                            'bg-gray-100 text-gray-500'
                          }`}>
                            {point.difficulty === 'easy' ? '易' :
                             point.difficulty === 'medium' ? '中' :
                             point.difficulty === 'hard' ? '难' : '?'}
                          </span>
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                            point.potential_impact === 'high' ? 'bg-purple-100 text-purple-600' :
                            point.potential_impact === 'medium' ? 'bg-blue-100 text-blue-600' :
                            point.potential_impact === 'low' ? 'bg-gray-100 text-gray-500' :
                            'bg-gray-100 text-gray-500'
                          }`}>
                            {point.potential_impact === 'high' ? '高影响' :
                             point.potential_impact === 'medium' ? '中影响' :
                             point.potential_impact === 'low' ? '低影响' : '?'}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mt-2 leading-relaxed">{point.description}</p>
                      <div className="mt-2">
                        <div className="text-xs text-gray-400 mb-1">研究价值</div>
                        <p className="text-xs text-gray-500">{point.rationale}</p>
                      </div>
                      {point.related_concepts && point.related_concepts.length > 0 && (
                        <div className="mt-2">
                          <div className="text-xs text-gray-400 mb-1">相关概念</div>
                          <div className="flex flex-wrap gap-1">
                            {point.related_concepts.slice(0, 5).map((c, j) => (
                              <span key={j} className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">
                                {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-16 right-4 bg-white/90 backdrop-blur rounded-xl shadow-lg p-3 z-10">
        <div className="text-xs font-semibold text-gray-500 mb-2">图例</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS.field }} />
            <span className="text-xs text-gray-600">概念节点</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: PAPER_COLOR }} />
            <span className="text-xs text-gray-600">论文节点</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CENTER_COLOR }} />
            <span className="text-xs text-gray-600">中心概念</span>
          </div>
        </div>
      </div>

      {/* Dedup Panel */}
      <DedupPanel isOpen={dedupOpen} onClose={() => setDedupOpen(false)} />
    </div>
  )
}