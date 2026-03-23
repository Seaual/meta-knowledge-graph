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
  Panel,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Search, FileText, X, ArrowLeft, BookOpen, GitBranch, Zap } from 'lucide-react'
import { conceptsApi, graphApi, papersApi } from '../lib/api'
import {
  computeRadialLayout,
  buildParentMap,
  buildChildrenMap,
  getNodePath,
  getDescendants,
  findRoots,
  getLevelStyle,
  Category,
  ConceptNode as LayoutConceptNode,
} from '../lib/radialLayout'
import { computeForceLayout } from '../lib/forceLayout'
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
// Sector Background Components
// ============================================

interface SectorBackgroundProps {
  centerX: number
  centerY: number
  roots: { id: string; category: string }[]
  maxRadius: number
}

function SectorBackgrounds({ centerX, centerY, roots, maxRadius }: SectorBackgroundProps) {
  if (roots.length === 0) return null

  const sectorAngle = (2 * Math.PI) / roots.length

  return (
    <g className="sector-backgrounds">
      {roots.map((root, index) => {
        const startAngle = index * sectorAngle
        const endAngle = (index + 1) * sectorAngle
        const color = CATEGORY_CONFIG[root.category as keyof typeof CATEGORY_CONFIG]?.color || '#94A3B8'

        const startOuter = {
          x: centerX + maxRadius * Math.cos(startAngle),
          y: centerY + maxRadius * Math.sin(startAngle),
        }
        const endOuter = {
          x: centerX + maxRadius * Math.cos(endAngle),
          y: centerY + maxRadius * Math.sin(endAngle),
        }

        const largeArc = sectorAngle > Math.PI ? 1 : 0

        const path = [
          `M ${centerX} ${centerY}`,
          `L ${startOuter.x} ${startOuter.y}`,
          `A ${maxRadius} ${maxRadius} 0 ${largeArc} 1 ${endOuter.x} ${endOuter.y}`,
          'Z',
        ].join(' ')

        return (
          <path
            key={root.id}
            d={path}
            fill={color}
            fillOpacity={0.08}
            stroke={color}
            strokeOpacity={0.2}
            strokeWidth={1}
            strokeDasharray="4 4"
          />
        )
      })}
    </g>
  )
}

function RadialRings({
  centerX,
  centerY,
  maxRadius,
  levels
}: {
  centerX: number
  centerY: number
  maxRadius: number
  levels: number
}) {
  const rings = []
  for (let i = 0; i <= levels; i++) {
    const radius = 60 * (i + 1)
    if (radius <= maxRadius) {
      rings.push(
        <circle
          key={i}
          cx={centerX}
          cy={centerY}
          r={radius}
          fill="none"
          stroke="#E2E8F0"
          strokeWidth={1}
          strokeDasharray={i === 0 ? "none" : "4 4"}
        />
      )
    }
  }
  return <g className="radial-rings">{rings}</g>
}

// ============================================
// Node Tooltip Component
// ============================================

function NodeTooltip({ node, position }: { node: Node | null; position: { x: number; y: number } }) {
  if (!node) return null

  const config = CATEGORY_CONFIG[node.data?.category as keyof typeof CATEGORY_CONFIG]

  return (
    <div
      className="absolute z-50 pointer-events-none"
      style={{
        left: position.x + 20,
        top: position.y - 10,
        transform: 'translateY(-50%)',
      }}
    >
      <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl max-w-xs">
        <div className="font-semibold mb-1">{node.data?.label}</div>
        <div className="flex items-center gap-2 text-gray-300">
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: config?.color || '#94A3B8' }}
          />
          <span>{config?.label || '概念'}</span>
          <span className="text-gray-500">|</span>
          <span>{node.data?.paperCount || 0} 篇论文</span>
        </div>
      </div>
      {/* Arrow */}
      <div
        className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 w-0 h-0"
        style={{
          borderTop: '6px solid transparent',
          borderBottom: '6px solid transparent',
          borderRight: '6px solid #111827',
        }}
      />
    </div>
  )
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

  // Layout mode: radial or force
  const [layoutMode, setLayoutMode] = useState<'radial' | 'force'>('force')

  // Tooltip state
  const [tooltipNode, setTooltipNode] = useState<Node | null>(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })

  // New state: level filter
  const [levelRange, setLevelRange] = useState<LevelRange>({ min: 0, max: 6 })

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

  // 计算根概念列表用于扇区背景
  const rootConcepts = useMemo(() => {
    if (!layoutData || !allGraphData) return []
    const roots = findRoots(layoutData.conceptNodes, allGraphData.edges)
    return roots.map(r => ({ id: r.id, category: r.category }))
  }, [layoutData, allGraphData])

  useEffect(() => {
    loadGraph()
  }, [])

  const loadGraph = async () => {
    try {
      const [conceptsRes, graphRes] = await Promise.all([
        conceptsApi.list(),
        graphApi.data(),
      ])

      console.log('Loaded concepts:', conceptsRes.data.length)
      console.log('Loaded graph nodes:', graphRes.data.nodes.length)
      console.log('Loaded graph edges:', graphRes.data.edges.length)

      setAllConcepts(conceptsRes.data)
      setAllGraphData(graphRes.data)
    } catch (err) {
      console.error('Failed to load graph:', err)
      setLoading(false)
    }
  }

  // Render layout based on mode
  useEffect(() => {
    if (!layoutData || !allGraphData) {
      console.log('renderLayout: missing data', { layoutData: !!layoutData, allGraphData: !!allGraphData })
      return
    }

    const { conceptNodes, childrenMap } = layoutData
    console.log('renderLayout: conceptNodes=', conceptNodes.length, 'edges=', allGraphData.edges.length, 'mode=', layoutMode)

    // Determine layout scope
    let targetNodes = conceptNodes
    let targetEdges = allGraphData.edges

    if (focusedNodeId) {
      const descendants = getDescendants(focusedNodeId, childrenMap)
      const visibleIds = new Set([focusedNodeId, ...descendants])
      targetNodes = conceptNodes.filter(n => visibleIds.has(n.id))
      targetEdges = allGraphData.edges.filter(
        e => visibleIds.has(e.source) && visibleIds.has(e.target)
      )
    }

    const width = containerRef.current?.clientWidth || 1200
    const height = containerRef.current?.clientHeight || 800

    // Helper to create React Flow nodes - filters by level using the levels map
    const createFlowNodes = (positions: Map<string, { x: number; y: number }>, levels: Map<string, number>) => {
      // Filter nodes by level range using the levels map
      const visibleIds = new Set<string>()
      levels.forEach((level, id) => {
        if (level >= levelRange.min && level <= levelRange.max) {
          visibleIds.add(id)
        }
      })

      return targetNodes
        .filter(n => visibleIds.has(n.id))
        .map(concept => {
          const pos = positions.get(concept.id)!
          const level = levels.get(concept.id) || 0
          const levelStyle = getLevelStyle(level)

          return {
            id: concept.id,
            type: 'concept',
            position: { x: pos.x, y: pos.y },
            data: {
              label: concept.text,
              category: concept.category,
              paperCount: concept.paper_count,
              level,
              nodeSize: levelStyle.nodeSize,
              opacity: levelStyle.opacity,
              dimmed: false,
            },
          }
        })
    }

    // Helper to create edges - only includes edges between visible nodes
    const createFlowEdges = (visibleNodeIds: Set<string>) => {
      return targetEdges
        .filter(e => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target))
        .map((edge, index) => ({
          id: `e-${index}`,
          source: edge.source,
          target: edge.target,
          type: 'network',
          data: { highlighted: false, dimmed: false },
        }))
    }

    if (layoutMode === 'radial') {
      // Radial layout
      const positions = computeRadialLayout(targetNodes, targetEdges, {
        centerX: width / 2,
        centerY: height / 2,
        ringSpacing: 60,
      })

      // Get levels from positions
      const levels = new Map<string, number>()
      positions.forEach((pos, id) => levels.set(id, pos.level))

      const flowNodes = createFlowNodes(positions, levels)
      const visibleIds = new Set(flowNodes.map(n => n.id))
      const flowEdges = createFlowEdges(visibleIds)

      setNodes(flowNodes)
      setEdges(flowEdges)
      setViewMode('radial')
      setSelectedPaper(null)
      setLoading(false)

      setTimeout(() => fitView({ padding: 0.2 }), 100)
    } else {
      // Force layout
      const forceNodes: any[] = targetNodes.map(n => ({ id: n.id }))
      const forceEdges = targetEdges.map(e => ({ source: e.source, target: e.target }))

      computeForceLayout(forceNodes, forceEdges, {
        width,
        height,
        nodeStrength: -200,
        linkDistance: 100,
        collideRadius: 30,
      }).then(positions => {
        // Compute depth for each node
        const parentMap = buildParentMap(targetEdges)
        const depthCache = new Map<string, number>()
        targetNodes.forEach(n => {
          let depth = 0
          let current = n.id
          while (parentMap.has(current)) {
            depth++
            current = parentMap.get(current)!
          }
          depthCache.set(n.id, depth)
        })

        const flowNodes = createFlowNodes(positions, depthCache)
        const visibleIds = new Set(flowNodes.map(n => n.id))
        const flowEdges = createFlowEdges(visibleIds)

        setNodes(flowNodes)
        setEdges(flowEdges)
        setViewMode('radial')
        setSelectedPaper(null)
        setLoading(false)

        setTimeout(() => fitView({ padding: 0.2 }), 100)
      })
    }
  }, [levelRange, layoutData, allGraphData, focusedNodeId, fitView, layoutMode])

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

          // Trigger drill-down by setting focused node
          setFocusedNodeId(node.id)
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
    [viewMode, allConcepts, layoutData, setNodes, setEdges]
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
    (event: React.MouseEvent, node: Node) => {
      if (viewMode !== 'radial') return

      // Show tooltip
      const bounds = containerRef.current?.getBoundingClientRect()
      if (bounds) {
        setTooltipPosition({
          x: event.clientX - bounds.left,
          y: event.clientY - bounds.top,
        })
      }
      setTooltipNode(node)

      // Highlight related nodes
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
    setTooltipNode(null) // Hide tooltip

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

  const onNodeMouseMove = useCallback((event: React.MouseEvent) => {
    const bounds = containerRef.current?.getBoundingClientRect()
    if (bounds) {
      setTooltipPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      })
    }
  }, [])

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
  }, [])

  const handleBreadcrumbClick = useCallback(
    (id: string, index: number) => {
      setDrillPath(prev => prev.slice(0, index + 1))
      setFocusedNodeId(id)
    },
    []
  )

  const handleHomeClick = useCallback(() => {
    setDrillPath([])
    setFocusedNodeId(null)
  }, [])

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
        onNodeMouseMove={onNodeMouseMove}
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
        {/* 背景层：扇区和同心环 */}
        {viewMode === 'radial' && !focusedNodeId && layoutMode === 'radial' && (
          <svg
            className="absolute inset-0 pointer-events-none"
            style={{ width: '100%', height: '100%', zIndex: 0 }}
          >
            <SectorBackgrounds
              centerX={containerRef.current?.clientWidth ? containerRef.current.clientWidth / 2 : 600}
              centerY={containerRef.current?.clientHeight ? containerRef.current.clientHeight / 2 : 400}
              roots={rootConcepts}
              maxRadius={400}
            />
            <RadialRings
              centerX={containerRef.current?.clientWidth ? containerRef.current.clientWidth / 2 : 600}
              centerY={containerRef.current?.clientHeight ? containerRef.current.clientHeight / 2 : 400}
              maxRadius={400}
              levels={5}
            />
          </svg>
        )}
        <Background color="#E2E8F0" gap={30} />
        <Controls showInteractive={false} className="!bg-white !shadow-lg !rounded-xl !border-0" />

        {/* Layout Toggle Button */}
        <Panel position="top-right" className="!m-2">
          <div className="bg-white/90 backdrop-blur rounded-xl shadow-lg p-1 flex gap-1">
            <button
              onClick={() => setLayoutMode('force')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                layoutMode === 'force'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Zap className="w-4 h-4" />
              力导向
            </button>
            <button
              onClick={() => setLayoutMode('radial')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                layoutMode === 'radial'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <GitBranch className="w-4 h-4" />
              放射状
            </button>
          </div>
        </Panel>
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

      {/* Node Tooltip */}
      <NodeTooltip node={tooltipNode} position={tooltipPosition} />

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