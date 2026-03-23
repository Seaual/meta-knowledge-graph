import { useCallback, useEffect, useState, useRef, useMemo } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  ReactFlowProvider,
  useReactFlow,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
  NodeProps,
  EdgeProps,
  getSmoothStepPath,
  SelectionMode,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Search, FileText, X, ArrowLeft, BookOpen } from 'lucide-react'
import { conceptsApi, graphApi, papersApi } from '../lib/api'
import {
  computeRadialLayout,
  buildParentMap,
  buildChildrenMap,
  filterByLevel,
  getNodePath,
  getDescendants,
  LEVEL_CONFIG,
  Category,
  ConceptNode as LayoutConceptNode,
} from '../lib/radialLayout'
import { LevelFilter, LevelRange } from '../components/LevelFilter'
import { Breadcrumb, BreadcrumbItem } from '../components/Breadcrumb'

// ============================================
// Types
// ============================================

interface Concept {
  id: string
  text: string
  category: string | null
  paper_count: number
  children?: Concept[]
  parents?: Concept[]
  papers?: { doi: string; title: string }[]
}

interface Paper {
  doi: string
  title: string
  abstract: string | null
  authors: string[]
  keywords?: string[]
  contributions?: string[]
  published_date: string | null
  pdf_path: string | null
  status: string
}

interface GraphNode {
  id: string
  label: string
  category: string
  paper_count: number
}

interface GraphEdge {
  source: string
  target: string
}

// ============================================
// Category Configuration
// ============================================

const CATEGORY_CONFIG = {
  field: { label: '领域', color: '#FF6B6B', bgColor: '#FEE2E2', textColor: '#991B1B' },
  direction: { label: '方向', color: '#4ECDC4', bgColor: '#CCFBF1', textColor: '#115E59' },
  subdirection: { label: '子方向', color: '#45B7D1', bgColor: '#E0F2FE', textColor: '#075985' },
  task: { label: '任务', color: '#96CEB4', bgColor: '#DCFCE7', textColor: '#166534' },
  method: { label: '方法', color: '#FFA726', bgColor: '#FFEDD5', textColor: '#9A3412' },
  technique: { label: '技术', color: '#FFD93D', bgColor: '#FEF9C3', textColor: '#854D0E' },
}

// ============================================
// Custom Node Components
// ============================================

function ConceptNode({ data, selected }: NodeProps) {
  const config = CATEGORY_CONFIG[data.category as keyof typeof CATEGORY_CONFIG] || CATEGORY_CONFIG.method
  // Use nodeSize from data (set by radial layout) or calculate from paper count
  const baseSize = data.nodeSize || 10
  const size = baseSize + Math.sqrt(data.paperCount || 0) * 2

  return (
    <div
      className={`
        relative rounded-full shadow-lg transition-all duration-300 cursor-pointer
        ${selected ? 'ring-4 ring-offset-2 scale-110' : 'hover:scale-105'}
        ${data.dimmed ? 'opacity-20' : 'opacity-100'}
      `}
      style={{
        width: size,
        height: size,
        backgroundColor: config.bgColor,
        borderColor: config.color,
        borderWidth: '3px',
        borderStyle: 'solid',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2 !h-2 !bg-transparent"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2 !h-2 !bg-transparent"
      />
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-transparent" />
      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-transparent" />

      {/* Center dot */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{
          width: size * 0.4,
          height: size * 0.4,
          backgroundColor: config.color,
        }}
      />

      {/* Selection ring */}
      {selected && (
        <div
          className="absolute -inset-1 rounded-full animate-pulse"
          style={{ border: `3px solid ${config.color}`, opacity: 0.5 }}
        />
      )}
    </div>
  )
}

function ConceptLabel({ node }: { node: Node }) {
  const label = node.data.label

  return (
    <div
      className="absolute top-full left-1/2 -translate-x-1/2 mt-1 whitespace-nowrap"
      style={{
        fontSize: '11px',
        fontWeight: 500,
        color: node.data.dimmed ? '#9CA3AF' : '#374151',
        textShadow: '0 1px 2px white',
      }}
    >
      {label}
    </div>
  )
}

function PaperNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        relative w-[140px] rounded-full shadow-lg transition-all duration-200 cursor-pointer
        ${selected ? 'ring-4 ring-offset-2 ring-blue-400 scale-110' : 'hover:scale-105'}
        bg-white border-3 border-blue-400
        ${data.dimmed ? 'opacity-20' : 'opacity-100'}
      `}
      style={{ borderWidth: '3px' }}
    >
      <div className="p-2 text-center">
        <BookOpen className="w-4 h-4 mx-auto mb-0.5 text-blue-500" />
        <p className="text-xs font-medium text-gray-700 line-clamp-2 leading-tight">
          {data.label}
        </p>
      </div>
    </div>
  )
}

function CenterConceptNode({ data, selected }: NodeProps) {
  const config = CATEGORY_CONFIG[data.category as keyof typeof CATEGORY_CONFIG] || CATEGORY_CONFIG.method
  const size = 120 + Math.sqrt(data.paperCount || 0) * 8

  return (
    <div
      className={`
        relative rounded-2xl shadow-2xl transition-all duration-300
        ${selected ? 'ring-4 ring-offset-2 scale-110' : ''}
      `}
      style={{
        width: size,
        backgroundColor: config.color,
        color: '#fff',
      }}
    >
      <div className="p-4 text-center">
        <div className="text-xs font-medium opacity-80 mb-1">{config.label}</div>
        <h3 className="font-bold text-base">{data.label}</h3>
        <div className="mt-2 text-sm opacity-80">{data.paperCount} 篇论文</div>
      </div>
    </div>
  )
}

const nodeTypes = { concept: ConceptNode, paper: PaperNode, centerConcept: CenterConceptNode }

// ============================================
// Animated Edge Component
// ============================================

function NetworkEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  style = {},
  data,
}: EdgeProps) {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    borderRadius: 8,
  })

  const isHighlighted = data?.highlighted

  return (
    <path
      id={id}
      className="react-flow__edge-path"
      d={edgePath}
      style={{
        ...style,
        stroke: isHighlighted ? '#3B82F6' : '#CBD5E1',
        strokeWidth: isHighlighted ? 3 : 1.5,
        opacity: data?.dimmed ? 0.1 : 0.6,
        transition: 'stroke 0.2s, stroke-width 0.2s, opacity 0.2s',
      }}
    />
  )
}

const edgeTypes = { animated: NetworkEdge, network: NetworkEdge }

// ============================================
// Paper Detail Panel
// ============================================

function PaperDetailPanel({
  paper,
  onClose,
}: {
  paper: Paper | null
  onClose: () => void
}) {
  if (!paper) return null

  return (
    <div className="absolute top-4 right-4 w-96 bg-white rounded-2xl shadow-2xl z-20 overflow-hidden max-h-[calc(100vh-120px)] flex flex-col">
      <div className="p-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white flex-shrink-0">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="w-4 h-4" />
              <span className="text-xs opacity-80">论文详情</span>
            </div>
            <h3 className="font-bold text-base leading-tight">{paper.title || '未命名论文'}</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-white/20 transition-colors flex-shrink-0">
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="overflow-y-auto flex-1 p-4 space-y-4">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 mb-1">DOI</h4>
          {paper.doi.startsWith('http') ? (
            <a href={paper.doi} target="_blank" rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline font-mono bg-gray-50 px-2 py-1 rounded block truncate">
              {paper.doi}
            </a>
          ) : (
            <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline font-mono bg-gray-50 px-2 py-1 rounded block truncate">
              {paper.doi}
            </a>
          )}
        </div>

        {paper.authors && paper.authors.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 mb-1">作者</h4>
            <p className="text-sm text-gray-700">{paper.authors.join(', ')}</p>
          </div>
        )}

        {paper.keywords && paper.keywords.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 mb-2">关键词</h4>
            <div className="flex flex-wrap gap-1.5">
              {paper.keywords.map((kw, i) => (
                <span key={i} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full">{kw}</span>
              ))}
            </div>
          </div>
        )}

        {paper.abstract && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 mb-1">摘要</h4>
            <p className="text-sm text-gray-700 leading-relaxed">{paper.abstract}</p>
          </div>
        )}

        {paper.contributions && paper.contributions.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 mb-2">创新点</h4>
            <ul className="space-y-1.5">
              {paper.contributions.map((c, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="text-green-500 mt-0.5">•</span>
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================
// Legend Component
// ============================================

function Legend() {
  return (
    <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur rounded-xl shadow-lg p-3 z-10">
      <div className="text-xs font-semibold text-gray-600 mb-2">层级图例</div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {Object.entries(CATEGORY_CONFIG).map(([key, config]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: config.color }} />
            <span className="text-xs text-gray-600">{config.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ============================================
// Main Graph Component
// ============================================

function GraphCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [selectedConcept, setSelectedConcept] = useState<Concept | null>(null)
  const [conceptPapers, setConceptPapers] = useState<{ doi: string; title: string }[]>([])
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
  const [viewMode, setViewMode] = useState<'radial' | 'detail'>('radial')
  const [currentConcept, setCurrentConcept] = useState<Concept | null>(null)

  // New state: level filter
  const [levelRange, setLevelRange] = useState<LevelRange>({ min: 0, max: 5 })

  // New state: drill-down path
  const [drillPath, setDrillPath] = useState<BreadcrumbItem[]>([])
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null)

  const { fitView } = useReactFlow()
  const containerRef = useRef<HTMLDivElement>(null)

  // Store all concepts
  const [allConcepts, setAllConcepts] = useState<Concept[]>([])
  const [allGraphData, setAllGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null)

  // Memoized layout data
  const layoutData = useMemo(() => {
    if (!allConcepts.length || !allGraphData) return null

    const conceptNodes: LayoutConceptNode[] = allConcepts.map(c => ({
      id: c.id,
      text: c.text,
      category: c.category as Category,
      paper_count: c.paper_count,
    }))

    const parentMap = buildParentMap(allGraphData.edges)
    const childrenMap = buildChildrenMap(allGraphData.edges)

    return { conceptNodes, parentMap, childrenMap }
  }, [allConcepts, allGraphData])

  useEffect(() => {
    loadGraph()
  }, [])

  const loadGraph = async () => {
    try {
      const [conceptsRes, graphRes] = await Promise.all([
        conceptsApi.list(),
        graphApi.data(),
      ])

      setAllConcepts(conceptsRes.data)
      setAllGraphData(graphRes.data)
      setLoading(false)
    } catch (err) {
      console.error('Failed to load graph:', err)
      setLoading(false)
    }
  }

  const renderRadialView = useCallback(
    (focusId?: string | null) => {
      if (!layoutData || !allGraphData) return

      const { conceptNodes, childrenMap } = layoutData

      // Determine layout scope
      let targetNodes = conceptNodes
      let targetEdges = allGraphData.edges

      if (focusId) {
        // Drill-down mode: only show this node's subtree
        const descendants = getDescendants(focusId, childrenMap)
        const visibleIds = new Set([focusId, ...descendants])
        targetNodes = conceptNodes.filter(n => visibleIds.has(n.id))
        targetEdges = allGraphData.edges.filter(
          e => visibleIds.has(e.source) && visibleIds.has(e.target)
        )
      }

      // Compute layout
      const width = containerRef.current?.clientWidth || 1200
      const height = containerRef.current?.clientHeight || 800
      const positions = computeRadialLayout(targetNodes, targetEdges, {
        centerX: width / 2,
        centerY: height / 2,
        ringSpacing: 60,
      })

      // Filter by level range
      const visibleIds = filterByLevel(positions, levelRange.min, levelRange.max)

      // Create React Flow nodes
      const flowNodes: Node[] = targetNodes
        .filter(n => visibleIds.has(n.id))
        .map(concept => {
          const pos = positions.get(concept.id)!
          const levelCfg = LEVEL_CONFIG[concept.category] || LEVEL_CONFIG.method

          return {
            id: concept.id,
            type: 'concept',
            position: { x: pos.x, y: pos.y },
            data: {
              label: concept.text,
              category: concept.category,
              paperCount: concept.paper_count,
              level: pos.level,
              nodeSize: levelCfg.nodeSize,
              opacity: levelCfg.opacity,
              dimmed: false,
            },
          }
        })

      // Create React Flow edges
      const flowEdges: Edge[] = targetEdges
        .filter(e => visibleIds.has(e.source) && visibleIds.has(e.target))
        .map((edge, index) => ({
          id: `e-${index}`,
          source: edge.source,
          target: edge.target,
          type: 'network',
          data: { highlighted: false, dimmed: false },
        }))

      setNodes(flowNodes)
      setEdges(flowEdges)
      setViewMode('radial')
      setSelectedPaper(null)
      setFocusedNodeId(focusId || null)

      setTimeout(() => fitView({ padding: 0.2 }), 100)
    },
    [layoutData, allGraphData, levelRange, fitView, setNodes, setEdges]
  )

  // Re-render when level range changes
  useEffect(() => {
    if (layoutData && allGraphData) {
      renderRadialView(focusedNodeId)
    }
  }, [levelRange, layoutData, allGraphData, focusedNodeId, renderRadialView])

  const onNodeClick = useCallback(
    async (_event: React.MouseEvent, node: Node) => {
      if (viewMode === 'radial' && node.type === 'concept') {
        // Update drill path
        const concept = allConcepts.find(c => c.id === node.id)
        if (concept) {
          setDrillPath(prev => {
            const existingIndex = prev.findIndex(item => item.id === node.id)
            if (existingIndex >= 0) {
              return prev.slice(0, existingIndex + 1)
            }
            return [...prev, {
              id: concept.id,
              text: concept.text,
              category: concept.category || 'method',
            }]
          })

          renderRadialView(node.id)
        }

        // Highlight related nodes
        if (layoutData) {
          const { parentMap, childrenMap } = layoutData
          const path = getNodePath(node.id, parentMap)
          const descendants = getDescendants(node.id, childrenMap)
          const highlightedIds = new Set([...path, ...descendants])

          setNodes(nds =>
            nds.map(n => ({
              ...n,
              data: { ...n.data, dimmed: !highlightedIds.has(n.id) },
            }))
          )
          setEdges(eds =>
            eds.map(e => ({
              ...e,
              data: {
                ...e.data,
                highlighted: highlightedIds.has(e.source) && highlightedIds.has(e.target),
                dimmed: !(highlightedIds.has(e.source) && highlightedIds.has(e.target)),
              },
            }))
          )
        }

        // Show concept details
        try {
          const res = await conceptsApi.get(node.id)
          setSelectedConcept(res.data)
          setConceptPapers(res.data.papers || [])
        } catch (err) {
          console.error('Failed to fetch concept details:', err)
        }
      } else if (viewMode === 'detail' && node.type === 'paper') {
        try {
          const res = await papersApi.get(node.data.doi)
          setSelectedPaper(res.data)
        } catch (err) {
          console.error('Failed to fetch paper details:', err)
        }
      }
    },
    [viewMode, allConcepts, layoutData, renderRadialView, setNodes, setEdges]
  )

  const onNodeDoubleClick = useCallback(
    async (_event: React.MouseEvent, node: Node) => {
      if (viewMode === 'radial' && node.type === 'concept' && node.data.paperCount > 0) {
        const concept = allConcepts.find((c) => c.id === node.id)
        if (concept) {
          const res = await conceptsApi.get(concept.id)
          const fullConcept = res.data
          const papers = fullConcept.papers || []

          setCurrentConcept(fullConcept)

          const centerNode: Node = {
            id: 'center',
            type: 'centerConcept',
            position: { x: 0, y: 0 },
            data: {
              label: fullConcept.text,
              category: fullConcept.category,
              paperCount: fullConcept.paper_count,
            },
          }

          const paperNodes: Node[] = papers.map((paper: { doi: string; title: string }, i: number) => {
            const angle = (2 * Math.PI * i) / papers.length - Math.PI / 2
            const radius = 200
            return {
              id: paper.doi,
              type: 'paper',
              position: {
                x: 400 + radius * Math.cos(angle) - 70,
                y: 350 + radius * Math.sin(angle) - 40,
              },
              data: {
                label: paper.title.length > 25 ? paper.title.substring(0, 25) + '...' : paper.title,
                doi: paper.doi,
              },
            }
          })

          const paperEdges: Edge[] = papers.map((paper: { doi: string }) => ({
            id: `edge-${paper.doi}`,
            source: 'center',
            target: paper.doi,
            type: 'network',
            data: { highlighted: false, dimmed: false },
          }))

          setNodes([centerNode, ...paperNodes])
          setEdges(paperEdges)
          setViewMode('detail')
          setSelectedPaper(null)

          setTimeout(() => fitView({ padding: 0.3 }), 100)
        }
      }
    },
    [viewMode, allConcepts, setNodes, setEdges, fitView]
  )

  const onNodeMouseEnter = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (viewMode !== 'radial') return

      if (layoutData) {
        const { childrenMap } = layoutData
        const path = getNodePath(node.id, layoutData.parentMap)
        const descendants = getDescendants(node.id, childrenMap)
        const highlightedIds = new Set([...path, ...descendants])

        setNodes(nds =>
          nds.map(n => ({
            ...n,
            data: { ...n.data, dimmed: !highlightedIds.has(n.id) && selectedConcept === null },
          }))
        )
      }
    },
    [viewMode, layoutData, selectedConcept, setNodes]
  )

  const onNodeMouseLeave = useCallback(() => {
    if (!selectedConcept) {
      setNodes(nds =>
        nds.map(n => ({
          ...n,
          data: { ...n.data, dimmed: false },
        }))
      )
      setEdges(eds =>
        eds.map(e => ({
          ...e,
          data: { ...e.data, highlighted: false, dimmed: false },
        }))
      )
    }
  }, [selectedConcept, setNodes, setEdges])

  const onPaneClick = useCallback(() => {
    if (viewMode === 'radial') {
      setSelectedConcept(null)
      setNodes(nds =>
        nds.map(n => ({
          ...n,
          data: { ...n.data, dimmed: false },
        }))
      )
      setEdges(eds =>
        eds.map(e => ({
          ...e,
          data: { ...e.data, highlighted: false, dimmed: false },
        }))
      )
    } else {
      setSelectedPaper(null)
    }
  }, [viewMode, setNodes, setEdges])

  const handleBack = useCallback(() => {
    setDrillPath([])
    setFocusedNodeId(null)
    setSelectedConcept(null)
    renderRadialView(null)
  }, [renderRadialView])

  const handleBreadcrumbClick = useCallback(
    (id: string, index: number) => {
      setDrillPath(prev => prev.slice(0, index + 1))
      renderRadialView(id)
    },
    [renderRadialView]
  )

  const handleHomeClick = useCallback(() => {
    setDrillPath([])
    setFocusedNodeId(null)
    renderRadialView(null)
  }, [renderRadialView])

  const handleLevelChange = useCallback((range: LevelRange) => {
    setLevelRange(range)
  }, [])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto" />
          <p className="mt-4 text-gray-500 font-medium">加载知识图谱...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full relative bg-gradient-to-br from-slate-50 to-slate-100" ref={containerRef}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseLeave={onNodeMouseLeave}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        selectionMode={SelectionMode.Partial}
        onlyRenderVisibleElements
      >
        <Background color="#E2E8F0" gap={30} />
        <Controls showInteractive={false} className="!bg-white !shadow-lg !rounded-xl !border-0" />
        <MiniMap
          nodeColor={(node) => {
            if (node.type === 'paper') return '#3B82F6'
            const config = CATEGORY_CONFIG[node.data?.category as keyof typeof CATEGORY_CONFIG]
            return config?.color || '#94A3B8'
          }}
          maskColor="rgba(0, 0, 0, 0.05)"
          position="bottom-right"
          style={{ background: '#fff', borderRadius: 12 }}
          pannable
          zoomable
        />
      </ReactFlow>

      {/* Node Labels - rendered separately for better performance */}
      {viewMode === 'radial' &&
        nodes.map((node) => (
          <div
            key={node.id}
            className="pointer-events-none absolute z-5"
            style={{
              left: node.position.x,
              top: node.position.y,
              transform: 'translate(-50%, 50px)',
            }}
          >
            <ConceptLabel node={node} />
          </div>
        ))}

      {/* Legend */}
      <Legend />

      {/* Breadcrumb Navigation */}
      {viewMode === 'radial' && (
        <div className="absolute top-4 left-4 z-10">
          <Breadcrumb
            items={drillPath}
            onItemClick={handleBreadcrumbClick}
            onHomeClick={handleHomeClick}
          />
        </div>
      )}

      {/* Level Filter */}
      {viewMode === 'radial' && (
        <div className="absolute top-4 right-4 z-10">
          <LevelFilter value={levelRange} onChange={handleLevelChange} />
        </div>
      )}

      {/* Concept Detail Panel */}
      {viewMode === 'radial' && selectedConcept && (
        <div className="absolute top-20 right-4 w-80 bg-white rounded-2xl shadow-2xl z-20 overflow-hidden">
          <div
            className="p-4"
            style={{
              backgroundColor:
                CATEGORY_CONFIG[selectedConcept.category as keyof typeof CATEGORY_CONFIG]?.bgColor || '#FEE2E2',
            }}
          >
            <div className="flex items-start justify-between">
              <div>
                <span
                  className="text-xs font-medium px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor:
                      CATEGORY_CONFIG[selectedConcept.category as keyof typeof CATEGORY_CONFIG]?.color || '#FF6B6B',
                    color: '#fff',
                  }}
                >
                  {CATEGORY_CONFIG[selectedConcept.category as keyof typeof CATEGORY_CONFIG]?.label || '概念'}
                </span>
                <h3
                  className="text-lg font-bold mt-2"
                  style={{
                    color:
                      CATEGORY_CONFIG[selectedConcept.category as keyof typeof CATEGORY_CONFIG]?.textColor || '#991B1B',
                  }}
                >
                  {selectedConcept.text}
                </h3>
                <p
                  className="text-sm mt-1 opacity-70"
                  style={{
                    color:
                      CATEGORY_CONFIG[selectedConcept.category as keyof typeof CATEGORY_CONFIG]?.textColor || '#991B1B',
                  }}
                >
                  {selectedConcept.paper_count} 篇关联论文
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedConcept(null)
                  onPaneClick()
                }}
                className="p-1 rounded-lg hover:bg-white/50 transition-colors"
              >
                <X
                  className="w-5 h-5"
                  style={{
                    color:
                      CATEGORY_CONFIG[selectedConcept.category as keyof typeof CATEGORY_CONFIG]?.textColor || '#991B1B',
                  }}
                />
              </button>
            </div>
          </div>

          <div className="max-h-80 overflow-y-auto p-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-3">关联论文</h4>
            {conceptPapers.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">暂无论文</p>
            ) : (
              <div className="space-y-2">
                {conceptPapers.map((paper) => (
                  <div
                    key={paper.doi}
                    className="flex items-start gap-2 p-2 rounded-lg bg-gray-50 hover:bg-gray-100 cursor-pointer transition-colors"
                  >
                    <FileText className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-gray-700 line-clamp-2">{paper.title}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Paper Detail Panel */}
      {viewMode === 'detail' && selectedPaper && (
        <PaperDetailPanel paper={selectedPaper} onClose={() => setSelectedPaper(null)} />
      )}

      {/* Toolbar */}
      <div className="absolute bottom-4 right-4 flex gap-2 z-10">
        {viewMode === 'detail' && (
          <button
            onClick={handleBack}
            className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl shadow-lg hover:bg-gray-50 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">返回概览</span>
          </button>
        )}
      </div>

      {/* Radial View Info */}
      {viewMode === 'radial' && (
        <div className="absolute bottom-20 left-4 z-10 bg-white/90 backdrop-blur rounded-xl shadow-lg p-3">
          <div className="text-xs text-gray-500 mb-1">知识图谱</div>
          <div className="font-bold text-gray-900">{nodes.length} 个概念</div>
          <div className="text-xs text-gray-500 mt-1">点击钻取 · 双击查看论文</div>
        </div>
      )}

      {/* Detail View Info */}
      {viewMode === 'detail' && currentConcept && (
        <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur rounded-xl shadow-lg p-3">
          <div className="text-xs text-gray-500 mb-1">当前概念</div>
          <div className="font-bold text-gray-900">{currentConcept.text}</div>
          <div className="text-xs text-gray-500 mt-1">点击论文圆圈查看详情</div>
        </div>
      )}

      {/* Empty State */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-30">
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-700">暂无概念</h3>
            <p className="text-sm text-gray-500 mt-1">上传论文并处理后，概念将显示在这里</p>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================
// Export with Provider
// ============================================

export default function Concepts() {
  return (
    <ReactFlowProvider>
      <div style={{ height: 'calc(100vh - 65px)' }}>
        <GraphCanvas />
      </div>
    </ReactFlowProvider>
  )
}