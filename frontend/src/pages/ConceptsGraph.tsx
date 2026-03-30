// Knowledge Graph - Academic Style Force Graph with Papers
import { useEffect, useRef, useState, useCallback } from 'react'
import ForceGraph from 'force-graph'
import { forceManyBody, forceLink, forceCollide } from 'd3-force'
import { conceptsApi, graphApi, papersApi, exportApi, foldersApi } from '../lib/api'
import { Download, ChevronDown, Folder, Search, X, ArrowLeft } from 'lucide-react'
import DedupPanel from '../components/DedupPanel'
import FilterPanel from '../components/FilterPanel'
import { useTranslation } from '../i18n'

// Types
interface Concept {
  id: string
  text: string
  category: string | null | undefined
  paper_count: number
  parents?: Concept[]
  children?: Concept[]
  papers?: { doi: string; title: string }[]
}

interface Paper {
  doi: string
  title: string
  authors?: string[]
  keywords?: string[]
  contributions?: string[]
  abstract: string | null
  status: string
  s2_doi?: string
  venue?: string
  year?: number
  citation_count?: number
  tldr?: string
  s2_fields_of_study?: string[]
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
  authors?: string[]
  keywords?: string[]
  abstract?: string | null
  doi?: string
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number
  fy?: number
}

// Category colors - Academic Warm Palette
const CATEGORY_COLORS: Record<string, string> = {
  field: '#6b4423',        // sepia
  direction: '#b8860b',    // amber
  subdirection: '#9a6b3c', // copper
  task: '#4a6b8a',         // slate blue
  method: '#c2410c',       // terracotta
  technique: '#2d5a27',    // forest green
}

const PAPER_COLOR = '#4a6b8a'
const CENTER_COLOR = '#d4a012'

interface ResearchPoint {
  title: string
  hypothesis: string
  description: string
  discovery_method: 'gap_filling' | 'leaf_extension' | 'bottleneck' | 'transfer'
  rationale: string
  related_concepts: string[]
  difficulty: 'low' | 'medium' | 'high'
  difficulty_reason: string
  novelty: 'incremental' | 'moderate' | 'high'
  potential_impact: 'niche' | 'broad' | 'transformative'
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
  const { t } = useTranslation()
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
  const [activeFolder, setActiveFolder] = useState<string>('')
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

  // Filter panel state
  const [filterPanelOpen, setFilterPanelOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategories, setSelectedCategories] = useState<string[]>([
    'field', 'direction', 'subdirection', 'task', 'method', 'technique'
  ])
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(null)

  // Filter handlers
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query)
  }, [])

  const handleCategoryChange = useCallback((categories: string[]) => {
    setSelectedCategories(categories)
  }, [])

  const handleFocusNode = useCallback((nodeId: string) => {
    const node = graphNodes.find(n => n.id === nodeId)
    if (node && graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 1000)
      graphRef.current.zoom(2, 1000)
      setHighlightedNodeId(nodeId)
      setTimeout(() => setHighlightedNodeId(null), 2000)
    }
  }, [graphNodes])

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
        const graphRes = await graphApi.data(activeFolder)
        const nodesFromGraph = graphRes.data.nodes.map((n: { id: string; label: string; category?: string; paper_count?: number }) => ({
          id: n.id,
          text: n.label,
          category: n.category,
          paper_count: n.paper_count || 0,
        }))
        setConcepts(nodesFromGraph)
        setEdges(graphRes.data.edges)
        setLoading(false)
      } catch (err) {
        console.error('Failed to load:', err)
        setLoading(false)
      }
    }
    loadData()
    loadFolders()
  }, [activeFolder])

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

  // Handle concept click
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

  // Handle paper click
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
          title: 'Analysis Failed',
          hypothesis: '',
          description: 'Could not retrieve research points. Check LLM configuration.',
          discovery_method: 'gap_filling',
          rationale: String(err),
          related_concepts: [],
          difficulty: 'medium',
          difficulty_reason: 'Analysis failed',
          novelty: 'moderate',
          potential_impact: 'niche',
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
      alert('Export failed')
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
      alert('Export failed')
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
      alert('Export failed')
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
          // Category-based base sizes (decreasing by hierarchy level)
          const CATEGORY_SIZES: Record<string, number> = {
            field: 16,        // largest
            direction: 14,
            subdirection: 12,
            task: 10,
            method: 8,
            technique: 6,     // smallest
          }
          const baseSize = CATEGORY_SIZES[node.category || 'method'] || 7
          // Add small boost based on paper count
          size = baseSize + Math.sqrt(node.paperCount || 0) * 0.3
          color = CATEGORY_COLORS[node.category || 'method'] || '#8a7a6a'
        }

        // Calculate opacity based on search and category filter
        let opacity = 1
        if (searchQuery) {
          const matchesSearch = node.name.toLowerCase().includes(searchQuery.toLowerCase())
          opacity = matchesSearch ? 1 : 0.2
        } else if (node.category && !selectedCategories.includes(node.category)) {
          opacity = 0.15
        }

        if (highlightedNodeId === node.id) {
          opacity = 1
        }

        const x = node.x || 0
        const y = node.y || 0

        // Highlighted node glow effect - warm amber
        if (highlightedNodeId === node.id) {
          ctx.beginPath()
          ctx.arc(x, y, size + 8, 0, 2 * Math.PI)
          ctx.fillStyle = 'rgba(184, 134, 11, 0.4)'
          ctx.fill()
        }

        ctx.globalAlpha = opacity

        // Draw node
        ctx.beginPath()
        ctx.arc(x, y, size, 0, 2 * Math.PI)

        if (isPaper) {
          ctx.fillStyle = color + '40'
          ctx.fill()
          ctx.strokeStyle = color
          ctx.lineWidth = 2.5
          ctx.stroke()
          ctx.beginPath()
          ctx.arc(x, y, size * 0.35, 0, 2 * Math.PI)
          ctx.fillStyle = color
          ctx.fill()
        } else if (isCenter) {
          const gradient = ctx.createRadialGradient(x, y, 0, x, y, size)
          gradient.addColorStop(0, color + '60')
          gradient.addColorStop(1, color + '20')
          ctx.fillStyle = gradient
          ctx.fill()
          ctx.strokeStyle = color
          ctx.lineWidth = 3
          ctx.stroke()
          ctx.beginPath()
          ctx.arc(x, y, size * 0.5, 0, 2 * Math.PI)
          ctx.fillStyle = color
          ctx.fill()
        } else {
          ctx.fillStyle = color + '30'
          ctx.fill()
          ctx.strokeStyle = color
          ctx.lineWidth = 2 / globalScale
          ctx.stroke()
          ctx.beginPath()
          ctx.arc(x, y, size * 0.3, 0, 2 * Math.PI)
          ctx.fillStyle = color
          ctx.fill()
        }

        // Draw label when zoomed in
        if (globalScale > 0.5) {
          const fontSize = isCenter ? 14 : 11
          ctx.font = `${fontSize / globalScale}px 'Source Sans 3', sans-serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'top'
          ctx.fillStyle = '#2c1810'
          const label = node.name && node.name.length > 30 ? node.name.substring(0, 30) + '...' : (node.name || '')
          ctx.fillText(label, x, y + size + 4 / globalScale)
        }

        ctx.globalAlpha = 1
      })
      .linkColor((link: any) => {
        const source = link.source
        if (source.type === 'center') return PAPER_COLOR + '60'
        return '#d4c4b0'
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
      .linkDirectionalParticleColor(() => '#b8860b')
      .d3AlphaDecay(0.005)
      .d3VelocityDecay(0.4)
      .d3Force('charge', forceManyBody().strength((node: any) => {
        if (node.type === 'paper') return -forceStrength * 0.5
        if (node.type === 'center') return -forceStrength * 2
        const depthBonus = -(node.depth || 0) * 30
        return -forceStrength + depthBonus
      }))
      .d3Force('link', forceLink().id((d: any) => d.id).distance(60).strength(0.5))
      .d3Force('collision', forceCollide().radius((node: any) => {
        if (node.type === 'paper') return 12
        if (node.type === 'center') return 25
        // Category-based collision radius
        const CATEGORY_RADII: Record<string, number> = {
          field: 20,
          direction: 18,
          subdirection: 16,
          task: 14,
          method: 12,
          technique: 10,
        }
        return CATEGORY_RADII[node.category || 'method'] || 11
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
  }, [graphNodes, graphLinks, viewMode, handleConceptClick, handlePaperClick, forceStrength, searchQuery, selectedCategories, highlightedNodeId])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gradient-warm">
        <div className="loading-academic">
          Mapping your knowledge landscape...
        </div>
      </div>
    )
  }

  return (
    <div className="h-full relative bg-gradient-warm">
      {/* Graph Canvas */}
      <div ref={containerRef} className="w-full h-full" />

      {/* Top Bar */}
      <div className="absolute top-4 left-4 z-10">
        {viewMode === 'concept' && (
          <button
            onClick={handleBack}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            {t.concepts.backToAll}
          </button>
        )}
      </div>

      {/* Action Buttons - Academic Style */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        {/* Filter Button */}
        <button
          onClick={() => setFilterPanelOpen(!filterPanelOpen)}
          className={`btn-secondary flex items-center gap-2 ${filterPanelOpen ? 'border-sepia text-sepia' : ''}`}
        >
          <Search className="w-4 h-4" />
          {t.concepts.filter}
        </button>

        {/* Folder Selector */}
        <div className="relative">
          <button
            onClick={() => setShowFolderMenu(!showFolderMenu)}
            className="btn-secondary flex items-center gap-2"
          >
            <Folder className="w-4 h-4" />
            {activeFolder ? (folders.find(f => f.id === activeFolder)?.name || t.common.all) : t.common.all}
            <ChevronDown className="w-4 h-4" />
          </button>
          {showFolderMenu && (
            <div className="absolute right-0 mt-2 w-48 card-academic overflow-hidden z-20 animate-slide-down">
              <button
                onClick={() => { setActiveFolder(''); setShowFolderMenu(false) }}
                className={`w-full text-left px-4 py-3 font-body text-sm hover:bg-paper flex items-center gap-2 transition-colors ${activeFolder === '' ? 'bg-vellum text-sepia' : 'text-muted'}`}
              >
                <Folder className="w-4 w-4" />
                {t.common.all}
              </button>
              {folders.map(folder => (
                <button
                  key={folder.id}
                  onClick={() => { setActiveFolder(folder.id); setShowFolderMenu(false) }}
                  className={`w-full text-left px-4 py-3 font-body text-sm hover:bg-paper flex items-center gap-2 transition-colors ${activeFolder === folder.id ? 'bg-vellum text-sepia' : 'text-muted'}`}
                >
                  <Folder className="w-4 h-4" />
                  {folder.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Export Dropdown */}
        {viewMode === 'all' && (
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="btn-secondary flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              {t.concepts.export}
              <ChevronDown className="w-4 h-4" />
            </button>
            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-56 card-academic overflow-hidden z-20 animate-slide-down">
                <button
                  onClick={() => { handleExportHtml(); setShowExportMenu(false) }}
                  className="w-full px-4 py-3 text-left hover:bg-paper flex items-center gap-3 transition-colors"
                >
                  <span className="text-lg">🌐</span>
                  <div>
                    <div className="font-body font-medium text-sepia">{t.export.html}</div>
                    <div className="font-mono text-xs text-faint">{t.export.htmlDesc}</div>
                  </div>
                </button>
                <button
                  onClick={() => { handleExportCanvas(); setShowExportMenu(false) }}
                  className="w-full px-4 py-3 text-left hover:bg-paper flex items-center gap-3 transition-colors"
                >
                  <span className="text-lg">🎨</span>
                  <div>
                    <div className="font-body font-medium text-sepia">{t.export.canvas}</div>
                    <div className="font-mono text-xs text-faint">{t.export.canvasDesc}</div>
                  </div>
                </button>
                <button
                  onClick={() => { handleExportMarkdown(); setShowExportMenu(false) }}
                  className="w-full px-4 py-3 text-left hover:bg-paper flex items-center gap-3 transition-colors"
                >
                  <span className="text-lg">📝</span>
                  <div>
                    <div className="font-body font-medium text-sepia">{t.export.markdown}</div>
                    <div className="font-mono text-xs text-faint">{t.export.markdownDesc}</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        )}

        {viewMode === 'all' && (
          <button
            onClick={() => setDedupOpen(true)}
            className="btn-primary flex items-center gap-2"
          >
            🔄 {t.concepts.dedupScan}
          </button>
        )}
      </div>

      {/* Info Panel - Academic Style */}
      <div className="absolute bottom-16 left-4 card-academic p-4 z-10">
        <div className="font-mono text-xs text-muted uppercase tracking-wider mb-1">
          {viewMode === 'all' ? t.concepts.knowledgeGraph : t.concepts.conceptDetails}
        </div>
        <div className="font-display text-lg text-sepia font-medium">
          {viewMode === 'all' ? `${concepts.length} ${t.concepts.concepts}` : selectedConcept?.text}
        </div>
        <div className="font-body text-xs text-muted mt-1">
          {viewMode === 'all' ? t.concepts.clickToView : t.concepts.clickPaperToView}
        </div>

        {/* Force Strength Slider */}
        <div className="mt-3 pt-3 border-t border-academic">
          <div className="flex items-center justify-between mb-1">
            <span className="font-mono text-xs text-muted">{t.concepts.nodeRepulsion}</span>
            <span className="font-mono text-xs text-sepia font-medium">{forceStrength}</span>
          </div>
          <input
            type="range"
            min="50"
            max="400"
            value={forceStrength}
            onChange={(e) => setForceStrength(Number(e.target.value))}
            className="w-full h-1.5 bg-paper rounded-lg appearance-none cursor-pointer accent-sepia"
          />
          <div className="flex justify-between font-mono text-[10px] text-faint mt-1">
            <span>{t.concepts.compact}</span>
            <span>{t.concepts.spread}</span>
          </div>
        </div>
      </div>

      {/* Concept Action Panel */}
      {showConceptActions && selectedConcept && (
        <div className="absolute top-4 right-4 card-academic p-4 z-20 w-72 animate-slide-down">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="font-display font-medium text-sepia text-sm">{selectedConcept.text}</h3>
              <div className="flex items-center gap-2 mt-1">
                {selectedConcept.category && (
                  <span
                    className="badge-academic"
                    style={{
                      backgroundColor: CATEGORY_COLORS[selectedConcept.category] + '15',
                      color: CATEGORY_COLORS[selectedConcept.category],
                      borderColor: CATEGORY_COLORS[selectedConcept.category] + '30',
                    }}
                  >
                    {selectedConcept.category}
                  </span>
                )}
                <span className="font-mono text-xs text-muted">{selectedConcept.paper_count || 0} {t.concepts.paper}</span>
              </div>
            </div>
            <button
              onClick={() => { setShowConceptActions(false); setSelectedConcept(null) }}
              className="w-6 h-6 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-2">
            <button
              onClick={handleDiscoverResearchPoints}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              🔍 {t.concepts.discoverResearch}
            </button>
            {selectedConcept.papers && selectedConcept.papers.length > 0 && (
              <button
                onClick={handleViewPapers}
                className="btn-secondary w-full flex items-center justify-center gap-2"
              >
                📄 {t.concepts.viewPapers} ({selectedConcept.papers.length})
              </button>
            )}
          </div>
        </div>
      )}

      {/* Hover Tooltip */}
      {hoverNode && !showConceptActions && (
        <div className="absolute top-4 right-4 card-academic p-3 z-10 max-w-xs pointer-events-none animate-slide-down">
          <div className="font-display text-sepia text-sm">
            {hoverNode.name}
          </div>
          <div className="flex items-center gap-2 mt-1">
            {hoverNode.type === 'paper' ? (
              <span className="badge-academic" style={{ backgroundColor: '#4a6b8a15', color: '#4a6b8a', borderColor: '#4a6b8a30' }}>
                {t.concepts.paperNode}
              </span>
            ) : hoverNode.type === 'center' ? (
              <span className="badge-academic" style={{ backgroundColor: '#d4a01215', color: '#d4a012', borderColor: '#d4a01230' }}>
                {t.concepts.centerConcept}
              </span>
            ) : (
              <>
                <span
                  className="badge-academic"
                  style={{
                    backgroundColor: CATEGORY_COLORS[hoverNode.category || 'method'] + '15',
                    color: CATEGORY_COLORS[hoverNode.category || 'method'],
                    borderColor: CATEGORY_COLORS[hoverNode.category || 'method'] + '30',
                  }}
                >
                  {hoverNode.category}
                </span>
                <span className="font-mono text-xs text-muted">L{hoverNode.depth}</span>
              </>
            )}
          </div>
          {hoverNode.type === 'concept' && (
            <div className="font-body text-xs text-faint mt-1">{t.concepts.clickToView}</div>
          )}
          {hoverNode.type === 'paper' && (
            <div className="font-body text-xs text-faint mt-1">{t.concepts.clickPaperToView}</div>
          )}
        </div>
      )}

      {/* Paper Detail Panel */}
      {selectedPaper && (
        <div className="absolute bottom-20 right-4 w-96 card-academic z-20 max-h-[70vh] overflow-y-auto animate-slide-up">
          <div className="p-4 border-b border-academic sticky top-0 bg-vellum">
            <div className="flex items-start justify-between">
              <h3 className="font-display font-medium text-sepia text-sm leading-tight pr-2">
                {selectedPaper.title}
              </h3>
              <button
                onClick={() => setSelectedPaper(null)}
                className="w-6 h-6 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all flex-shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {/* DOI */}
            <div>
              <div className="font-mono text-xs text-muted uppercase tracking-wider mb-1">{t.concepts.paperDetail.doi}</div>
              {selectedPaper.s2_doi ? (
                <a
                  href={`https://doi.org/${selectedPaper.s2_doi}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-xs text-status-info hover:text-sepia hover:underline break-all"
                >
                  {selectedPaper.s2_doi}
                </a>
              ) : (
                <div className="font-mono text-xs text-muted break-all">{selectedPaper.doi}</div>
              )}
            </div>

            {/* Venue & Year */}
            {(selectedPaper.venue || selectedPaper.year) && (
              <div>
                <div className="font-mono text-xs text-muted uppercase tracking-wider mb-1">{t.concepts.paperDetail.venue}</div>
                <div className="font-body text-sm text-sepia">
                  {selectedPaper.venue}
                  {selectedPaper.year && <span className="text-muted">, {selectedPaper.year}</span>}
                </div>
              </div>
            )}

            {/* Citation Count */}
            {selectedPaper.citation_count !== undefined && (
              <div>
                <div className="font-mono text-xs text-muted uppercase tracking-wider mb-1">{t.concepts.paperDetail.citations}</div>
                <div className="font-display text-lg text-sepia">{selectedPaper.citation_count}</div>
              </div>
            )}

            {/* TLDR */}
            {selectedPaper.tldr && (
              <div>
                <div className="font-mono text-xs text-status-success uppercase tracking-wider mb-1">{t.concepts.paperDetail.tldr}</div>
                <div className="font-quote text-sm text-status-success italic bg-status-success/5 p-3 rounded-medium">
                  {selectedPaper.tldr}
                </div>
              </div>
            )}

            {/* Authors */}
            {selectedPaper.authors && selectedPaper.authors.length > 0 && (
              <div>
                <div className="font-mono text-xs text-muted uppercase tracking-wider mb-1">{t.concepts.paperDetail.authors}</div>
                <div className="font-body text-sm text-sepia">
                  {selectedPaper.authors.slice(0, 5).join(', ')}
                  {selectedPaper.authors.length > 5 && (
                    <span className="text-muted"> +{selectedPaper.authors.length - 5} {t.concepts.paperDetail.more}</span>
                  )}
                </div>
              </div>
            )}

            {/* Keywords */}
            {selectedPaper.keywords && selectedPaper.keywords.length > 0 && (
              <div>
                <div className="font-mono text-xs text-muted uppercase tracking-wider mb-2">{t.concepts.paperDetail.keywords}</div>
                <div className="flex flex-wrap gap-1">
                  {selectedPaper.keywords.map((kw, i) => (
                    <span
                      key={i}
                      className="badge-academic"
                      style={{ backgroundColor: '#f5f0e8', color: '#6b4423', borderColor: '#e8dfd0' }}
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Abstract */}
            {selectedPaper.abstract && (
              <div>
                <div className="font-mono text-xs text-muted uppercase tracking-wider mb-1">{t.concepts.paperDetail.abstract}</div>
                <div className="font-body text-sm text-sepia leading-relaxed">
                  {selectedPaper.abstract}
                </div>
              </div>
            )}

            {/* Contributions */}
            {selectedPaper.contributions && selectedPaper.contributions.length > 0 && (
              <div>
                <div className="font-mono text-xs text-muted uppercase tracking-wider mb-2">{t.concepts.paperDetail.keyContributions}</div>
                <ul className="font-body text-sm text-sepia space-y-1">
                  {selectedPaper.contributions.slice(0, 3).map((c, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-amber mt-1">•</span>
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
        <div className="absolute top-20 left-4 w-[480px] card-academic z-20 max-h-[75vh] overflow-y-auto animate-slide-up">
          <div className="p-4 border-b border-academic sticky top-0 bg-vellum">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-display font-medium text-sepia text-base">🔍 {t.concepts.researchPoints.title}</h3>
                <p className="font-body text-xs text-muted mt-1">
                  {t.concepts.researchPoints.basedOn} "{researchPoints?.concept_name || selectedConcept?.text}"
                </p>
              </div>
              <button
                onClick={() => setShowResearchPanel(false)}
                className="w-6 h-6 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {loadingResearchPoints ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <div className="loading-academic" style={{ minHeight: '100px' }}>
                    {t.concepts.researchPoints.analyzing}
                  </div>
                  <p className="font-body text-xs text-muted mt-1">{t.concepts.researchPoints.traversing}</p>
                </div>
              </div>
            ) : researchPoints ? (
              <>
                {/* Analysis Context Summary */}
                <div className="bg-paper rounded-large p-3">
                  <div className="font-mono text-xs text-sepia uppercase tracking-wider mb-2">{t.concepts.researchPoints.analysisContext}</div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <div className="font-display text-lg text-sepia font-medium">{researchPoints.analysis_context.ancestors.length}</div>
                      <div className="font-mono text-xs text-muted">{t.concepts.researchPoints.ancestors}</div>
                    </div>
                    <div>
                      <div className="font-display text-lg text-sepia font-medium">{researchPoints.analysis_context.descendants.length}</div>
                      <div className="font-mono text-xs text-muted">{t.concepts.researchPoints.descendants}</div>
                    </div>
                    <div>
                      <div className="font-display text-lg text-sepia font-medium">{researchPoints.analysis_context.edge_nodes.length}</div>
                      <div className="font-mono text-xs text-muted">{t.concepts.researchPoints.edgeNodes}</div>
                    </div>
                  </div>
                </div>

                {/* Research Points */}
                <div className="space-y-3">
                  {researchPoints.research_points.map((point, i) => (
                    <div
                      key={i}
                      className="border border-academic rounded-large p-3 hover:border-sepia hover:bg-vellum/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-display font-medium text-sepia text-sm">{point.title}</h4>
                        <div className="flex gap-1 flex-shrink-0">
                          <span
                            className="badge-academic"
                            style={{
                              backgroundColor: point.difficulty === 'low' ? '#2d5a2715' : point.difficulty === 'medium' ? '#b8860b15' : '#a33b3b15',
                              color: point.difficulty === 'low' ? '#2d5a27' : point.difficulty === 'medium' ? '#b8860b' : '#a33b3b',
                              borderColor: point.difficulty === 'low' ? '#2d5a2730' : point.difficulty === 'medium' ? '#b8860b30' : '#a33b3b30',
                            }}
                          >
                            {t.concepts.researchPoints.difficultyLabel[point.difficulty as 'low' | 'medium' | 'high']}
                          </span>
                          <span
                            className="badge-academic"
                            style={{
                              backgroundColor: point.novelty === 'high' ? '#c2410c15' : point.novelty === 'moderate' ? '#4a6b8a15' : '#a89a8a15',
                              color: point.novelty === 'high' ? '#c2410c' : point.novelty === 'moderate' ? '#4a6b8a' : '#a89a8a',
                              borderColor: point.novelty === 'high' ? '#c2410c30' : point.novelty === 'moderate' ? '#4a6b8a30' : '#a89a8a30',
                            }}
                          >
                            {t.concepts.researchPoints.noveltyLabel[point.novelty as 'high' | 'moderate' | 'incremental']}
                          </span>
                          <span
                            className="badge-academic"
                            style={{
                              backgroundColor: point.potential_impact === 'transformative' ? '#d4a01215' : point.potential_impact === 'broad' ? '#4a6b8a15' : '#a89a8a15',
                              color: point.potential_impact === 'transformative' ? '#d4a012' : point.potential_impact === 'broad' ? '#4a6b8a' : '#a89a8a',
                              borderColor: point.potential_impact === 'transformative' ? '#d4a01230' : point.potential_impact === 'broad' ? '#4a6b8a30' : '#a89a8a30',
                            }}
                          >
                            {t.concepts.researchPoints.impactLabel[point.potential_impact as 'transformative' | 'broad' | 'niche']}
                          </span>
                        </div>
                      </div>

                      {point.hypothesis && (
                        <div className="mt-2 p-2 bg-status-info/5 rounded-soft font-quote text-xs text-status-info italic">
                          💡 {point.hypothesis}
                        </div>
                      )}

                      <p className="font-body text-sm text-sepia mt-2 leading-relaxed">{point.description}</p>

                      <div className="mt-2">
                        <div className="font-mono text-xs text-faint mb-1">{t.concepts.researchPoints.discoveryMethod} · {t.concepts.researchPoints.researchValue}</div>
                        <p className="font-body text-xs text-muted">
                          {point.discovery_method === 'gap_filling' ? '🔍 ' + t.concepts.researchPoints.method.gap_filling :
                           point.discovery_method === 'leaf_extension' ? '🌱 ' + t.concepts.researchPoints.method.leaf_extension :
                           point.discovery_method === 'bottleneck' ? '🔥 ' + t.concepts.researchPoints.method.bottleneck :
                           point.discovery_method === 'transfer' ? '🔄 ' + t.concepts.researchPoints.method.transfer : ''} · {point.rationale}
                        </p>
                      </div>

                      {point.difficulty_reason && (
                        <div className="mt-1 font-mono text-xs text-faint">
                          {t.concepts.researchPoints.difficulty}: {point.difficulty_reason}
                        </div>
                      )}

                      {point.related_concepts && point.related_concepts.length > 0 && (
                        <div className="mt-2">
                          <div className="font-mono text-xs text-faint mb-1">{t.concepts.researchPoints.relatedConcepts}</div>
                          <div className="flex flex-wrap gap-1">
                            {point.related_concepts.slice(0, 5).map((c, j) => (
                              <span
                                key={j}
                                className="badge-academic"
                                style={{ backgroundColor: '#f5f0e8', color: '#6b4423', borderColor: '#e8dfd0' }}
                              >
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

      {/* Legend - Academic Style */}
      <div className="absolute bottom-16 right-4 card-academic p-4 z-10">
        <div className="font-mono text-xs text-sepia uppercase tracking-wider mb-2">{t.concepts.legend}</div>
        <div className="space-y-1.5">
          {/* Concept Categories */}
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS.field }} />
            <span className="font-body text-xs text-muted">{t.concepts.category.field}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS.direction }} />
            <span className="font-body text-xs text-muted">{t.concepts.category.direction}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS.subdirection }} />
            <span className="font-body text-xs text-muted">{t.concepts.category.subdirection}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS.task }} />
            <span className="font-body text-xs text-muted">{t.concepts.category.task}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS.method }} />
            <span className="font-body text-xs text-muted">{t.concepts.category.method}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS.technique }} />
            <span className="font-body text-xs text-muted">{t.concepts.category.technique}</span>
          </div>
          {/* Divider */}
          <div className="border-t border-academic my-1" />
          {/* Special Nodes */}
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: PAPER_COLOR }} />
            <span className="font-body text-xs text-muted">{t.concepts.paperNode}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CENTER_COLOR }} />
            <span className="font-body text-xs text-muted">{t.concepts.centerConcept}</span>
          </div>
        </div>
      </div>

      {/* Dedup Panel */}
      {dedupOpen && (
        <DedupPanel isOpen={dedupOpen} onClose={() => setDedupOpen(false)} />
      )}

      {/* Filter Panel */}
      {filterPanelOpen && (
        <FilterPanel
          searchQuery={searchQuery}
          selectedCategories={selectedCategories}
          graphNodes={graphNodes}
          onSearch={handleSearch}
          onCategoryChange={handleCategoryChange}
          onFocusNode={handleFocusNode}
          onClose={() => setFilterPanelOpen(false)}
        />
      )}
    </div>
  )
}