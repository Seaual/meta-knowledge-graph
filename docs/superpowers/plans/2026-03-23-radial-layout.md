# 概念页面放射状分层布局实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将概念页面从力导向布局改为放射状分层布局，支持层级筛选、点击钻取和悬停高亮。

**Architecture:** 使用 d3-hierarchy 构建树结构，自定义放射状布局算法将节点放置在同心环上。每个根概念占据一个扇区，子概念在扇区内向外展开。React Flow 继续负责渲染和交互。

**Tech Stack:** React, TypeScript, ReactFlow, d3-hierarchy, Tailwind CSS

---

## 文件结构

| 文件 | 责任 |
|------|------|
| `frontend/src/lib/radialLayout.ts` | 放射状布局算法，计算节点位置 |
| `frontend/src/components/LevelFilter.tsx` | 层级筛选器组件 |
| `frontend/src/components/Breadcrumb.tsx` | 面包屑导航组件 |
| `frontend/src/pages/Concepts.tsx` | 主页面，整合新布局和组件 |

## 保留的现有代码

以下现有代码元素在修改过程中保持不变：
- `ConceptNode`, `ConceptLabel`, `PaperNode`, `CenterConceptNode` - 自定义节点组件
- `NetworkEdge` - 自定义边组件
- `PaperDetailPanel` - 论文详情面板
- `Legend` - 图例组件
- `CATEGORY_CONFIG` - 分类颜色配置
- `nodeTypes`, `edgeTypes` - ReactFlow 节点/边类型注册

---

## Task 1: 创建放射状布局算法

**Files:**
- Create: `frontend/src/lib/radialLayout.ts`

- [ ] **Step 1: 创建 radialLayout.ts 文件，定义类型和布局函数**

```typescript
// frontend/src/lib/radialLayout.ts
import { Node, Edge } from 'reactflow'

// 层级配置
export const LEVEL_CONFIG = {
  field: { level: 0, radius: 80, nodeSize: 18, opacity: 1.0 },
  direction: { level: 1, radius: 140, nodeSize: 14, opacity: 0.95 },
  subdirection: { level: 2, radius: 200, nodeSize: 11, opacity: 0.85 },
  task: { level: 3, radius: 260, nodeSize: 9, opacity: 0.75 },
  method: { level: 4, radius: 320, nodeSize: 7, opacity: 0.65 },
  technique: { level: 5, radius: 380, nodeSize: 5, opacity: 0.55 },
} as const

export type Category = keyof typeof LEVEL_CONFIG

export interface RadialLayoutConfig {
  centerX: number
  centerY: number
  ringSpacing: number // 环之间的间距
  minSectorAngle: number // 最小扇区角度（弧度）
}

export interface ConceptNode {
  id: string
  text: string
  category: Category
  paper_count: number
  parentId?: string | null
  children?: ConceptNode[]
}

const DEFAULT_CONFIG: RadialLayoutConfig = {
  centerX: 600,
  centerY: 400,
  ringSpacing: 60,
  minSectorAngle: Math.PI / 36, // 5度
}

/**
 * 查找根概念（没有父节点的概念）
 */
export function findRoots(
  concepts: ConceptNode[],
  edges: { source: string; target: string }[]
): ConceptNode[] {
  const childIds = new Set(edges.map(e => e.target))
  return concepts.filter(c => !childIds.has(c.id))
}

/**
 * 构建父子关系映射
 */
export function buildParentMap(
  edges: { source: string; target: string }[]
): Map<string, string> {
  const map = new Map<string, string>()
  edges.forEach(e => map.set(e.target, e.source))
  return map
}

/**
 * 构建子节点映射
 */
export function buildChildrenMap(
  edges: { source: string; target: string }[]
): Map<string, string[]> {
  const map = new Map<string, string[]>()
  edges.forEach(e => {
    const children = map.get(e.source) || []
    children.push(e.target)
    map.set(e.source, children)
  })
  return map
}

/**
 * 计算概念深度
 */
export function computeDepth(
  conceptId: string,
  parentMap: Map<string, string>,
  cache: Map<string, number> = new Map()
): number {
  if (cache.has(conceptId)) return cache.get(conceptId)!

  const parentId = parentMap.get(conceptId)
  if (!parentId) {
    cache.set(conceptId, 0)
    return 0
  }

  const depth = 1 + computeDepth(parentId, parentMap, cache)
  cache.set(conceptId, depth)
  return depth
}

/**
 * 放射状布局主函数
 */
export function computeRadialLayout(
  concepts: ConceptNode[],
  edges: { source: string; target: string }[],
  config: Partial<RadialLayoutConfig> = {}
): Map<string, { x: number; y: number; angle: number; level: number }> {
  const cfg = { ...DEFAULT_CONFIG, ...config }
  const positions = new Map<string, { x: number; y: number; angle: number; level: number }>()

  const parentMap = buildParentMap(edges)
  const childrenMap = buildChildrenMap(edges)
  const depthCache = new Map<string, number>()

  // 计算每个概念的深度
  concepts.forEach(c => {
    computeDepth(c.id, parentMap, depthCache)
  })

  // 找到根概念
  const roots = findRoots(concepts, edges)

  if (roots.length === 0) {
    // 没有根概念，使用力导向布局的回退
    concepts.forEach((c, i) => {
      const angle = (2 * Math.PI * i) / concepts.length
      const level = depthCache.get(c.id) || 0
      const radius = cfg.ringSpacing * (level + 1)
      positions.set(c.id, {
        x: cfg.centerX + radius * Math.cos(angle),
        y: cfg.centerY + radius * Math.sin(angle),
        angle,
        level,
      })
    })
    return positions
  }

  // 计算每个根的扇区角度范围
  const sectorAngle = (2 * Math.PI) / roots.length

  // 递归布局每个根的子树
  roots.forEach((root, rootIndex) => {
    const sectorStart = rootIndex * sectorAngle
    const sectorEnd = (rootIndex + 1) * sectorAngle
    const sectorMid = (sectorStart + sectorEnd) / 2

    layoutSubtree(
      root.id,
      cfg.centerX,
      cfg.centerY,
      sectorStart,
      sectorEnd,
      0,
      positions,
      childrenMap,
      depthCache,
      cfg
    )
  })

  return positions
}

/**
 * 递归布局子树
 */
function layoutSubtree(
  nodeId: string,
  centerX: number,
  centerY: number,
  sectorStart: number,
  sectorEnd: number,
  depth: number,
  positions: Map<string, { x: number; y: number; angle: number; level: number }>,
  childrenMap: Map<string, string[]>,
  depthCache: Map<string, number>,
  config: RadialLayoutConfig
): void {
  const radius = config.ringSpacing * (depth + 1)
  const midAngle = (sectorStart + sectorEnd) / 2

  // 计算位置
  positions.set(nodeId, {
    x: centerX + radius * Math.cos(midAngle),
    y: centerY + radius * Math.sin(midAngle),
    angle: midAngle,
    level: depth,
  })

  // 布局子节点
  const children = childrenMap.get(nodeId) || []
  if (children.length === 0) return

  // 计算子节点扇区
  const childSectorAngle = (sectorEnd - sectorStart) / children.length

  children.forEach((childId, index) => {
    const childSectorStart = sectorStart + index * childSectorAngle
    const childSectorEnd = childSectorStart + childSectorAngle

    layoutSubtree(
      childId,
      centerX,
      centerY,
      childSectorStart,
      childSectorEnd,
      depth + 1,
      positions,
      childrenMap,
      depthCache,
      config
    )
  })
}

/**
 * 根据层级过滤节点
 */
export function filterByLevel(
  positions: Map<string, { x: number; y: number; angle: number; level: number }>,
  minLevel: number,
  maxLevel: number
): Set<string> {
  const visible = new Set<string>()
  positions.forEach((pos, id) => {
    if (pos.level >= minLevel && pos.level <= maxLevel) {
      visible.add(id)
    }
  })
  return visible
}

/**
 * 获取节点的完整路径（从根到该节点）
 */
export function getNodePath(
  nodeId: string,
  parentMap: Map<string, string>
): string[] {
  const path: string[] = [nodeId]
  let current = nodeId

  while (parentMap.has(current)) {
    const parentId = parentMap.get(current)!
    path.unshift(parentId)
    current = parentId
  }

  return path
}

/**
 * 获取节点的所有后代
 */
export function getDescendants(
  nodeId: string,
  childrenMap: Map<string, string[]>
): string[] {
  const descendants: string[] = []
  const stack = [nodeId]

  while (stack.length > 0) {
    const current = stack.pop()!
    const children = childrenMap.get(current) || []
    children.forEach(child => {
      descendants.push(child)
      stack.push(child)
    })
  }

  return descendants
}

/**
 * 计算扇区背景路径
 */
export function computeSectorPath(
  centerX: number,
  centerY: number,
  startAngle: number,
  endAngle: number,
  innerRadius: number,
  outerRadius: number
): string {
  const startOuter = {
    x: centerX + outerRadius * Math.cos(startAngle),
    y: centerY + outerRadius * Math.sin(startAngle),
  }
  const endOuter = {
    x: centerX + outerRadius * Math.cos(endAngle),
    y: centerY + outerRadius * Math.sin(endAngle),
  }
  const startInner = {
    x: centerX + innerRadius * Math.cos(startAngle),
    y: centerY + innerRadius * Math.sin(startAngle),
  }
  const endInner = {
    x: centerX + innerRadius * Math.cos(endAngle),
    y: centerY + innerRadius * Math.sin(endAngle),
  }

  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0

  return [
    `M ${startInner.x} ${startInner.y}`,
    `L ${startOuter.x} ${startOuter.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${endOuter.x} ${endOuter.y}`,
    `L ${endInner.x} ${endInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${startInner.x} ${startInner.y}`,
    'Z',
  ].join(' ')
}
```

- [ ] **Step 2: 验证文件创建成功**

Run: `ls -la frontend/src/lib/radialLayout.ts`
Expected: 文件存在

- [ ] **Step 3: 提交**

```bash
git add frontend/src/lib/radialLayout.ts
git commit -m "feat: add radial layout algorithm for concept hierarchy"
```

---

## Task 2: 创建层级筛选器组件

**Files:**
- Create: `frontend/src/components/LevelFilter.tsx`

- [ ] **Step 1: 创建 LevelFilter.tsx 组件**

```typescript
// frontend/src/components/LevelFilter.tsx
import React from 'react'
import { Layers } from 'lucide-react'

export interface LevelRange {
  min: number
  max: number
}

interface LevelFilterProps {
  value: LevelRange
  onChange: (range: LevelRange) => void
  maxLevel?: number
}

const LEVEL_LABELS = [
  { level: 0, label: 'L0 领域', short: '领域' },
  { level: 1, label: 'L1 方向', short: '方向' },
  { level: 2, label: 'L2 子方向', short: '子方向' },
  { level: 3, label: 'L3 任务', short: '任务' },
  { level: 4, label: 'L4 方法', short: '方法' },
  { level: 5, label: 'L5 技术', short: '技术' },
]

const PRESETS = [
  { label: '概览', min: 0, max: 2 },
  { label: '标准', min: 0, max: 4 },
  { label: '全部', min: 0, max: 5 },
]

export function LevelFilter({ value, onChange, maxLevel = 5 }: LevelFilterProps) {
  const handlePresetClick = (preset: typeof PRESETS[0]) => {
    onChange({ min: preset.min, max: Math.min(preset.max, maxLevel) })
  }

  const handleMinChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newMin = parseInt(e.target.value, 10)
    const newMax = Math.max(value.max, newMin)
    onChange({ min: newMin, max: newMax })
  }

  const handleMaxChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newMax = parseInt(e.target.value, 10)
    const newMin = Math.min(value.min, newMax)
    onChange({ min: newMin, max: newMax })
  }

  return (
    <div className="bg-white/90 backdrop-blur rounded-xl shadow-lg p-3 z-10">
      <div className="flex items-center gap-2 mb-3">
        <Layers className="w-4 h-4 text-gray-500" />
        <span className="text-xs font-semibold text-gray-600">层级筛选</span>
      </div>

      {/* 快捷按钮 */}
      <div className="flex gap-1 mb-3">
        {PRESETS.map((preset) => (
          <button
            key={preset.label}
            onClick={() => handlePresetClick(preset)}
            className={`px-2 py-1 text-xs rounded-lg transition-colors ${
              value.min === preset.min && value.max === Math.min(preset.max, maxLevel)
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* 范围选择 */}
      <div className="flex items-center gap-2">
        <select
          value={value.min}
          onChange={handleMinChange}
          className="text-xs px-2 py-1 rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {LEVEL_LABELS.slice(0, maxLevel + 1).map((item) => (
            <option key={item.level} value={item.level}>
              {item.short}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">至</span>
        <select
          value={value.max}
          onChange={handleMaxChange}
          className="text-xs px-2 py-1 rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {LEVEL_LABELS.slice(0, maxLevel + 1).map((item) => (
            <option key={item.level} value={item.level}>
              {item.short}
            </option>
          ))}
        </select>
      </div>

      {/* 当前范围显示 */}
      <div className="mt-2 text-xs text-gray-500 text-center">
        显示 {LEVEL_LABELS[value.min].short} ~ {LEVEL_LABELS[value.max].short}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 验证文件创建成功**

Run: `ls -la frontend/src/components/LevelFilter.tsx`
Expected: 文件存在

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/LevelFilter.tsx
git commit -m "feat: add level filter component for radial layout"
```

---

## Task 3: 创建面包屑导航组件

**Files:**
- Create: `frontend/src/components/Breadcrumb.tsx`

- [ ] **Step 1: 创建 Breadcrumb.tsx 组件**

```typescript
// frontend/src/components/Breadcrumb.tsx
import React from 'react'
import { ChevronRight, Home } from 'lucide-react'

export interface BreadcrumbItem {
  id: string
  text: string
  category: string
}

interface BreadcrumbProps {
  items: BreadcrumbItem[]
  onItemClick: (id: string, index: number) => void
  onHomeClick: () => void
}

const CATEGORY_COLORS: Record<string, string> = {
  field: '#FF6B6B',
  direction: '#4ECDC4',
  subdirection: '#45B7D1',
  task: '#96CEB4',
  method: '#FFA726',
  technique: '#FFD93D',
}

export function Breadcrumb({ items, onItemClick, onHomeClick }: BreadcrumbProps) {
  return (
    <div className="flex items-center gap-1 bg-white/90 backdrop-blur rounded-xl shadow-lg px-3 py-2 z-10">
      {/* 首页按钮 */}
      <button
        onClick={onHomeClick}
        className="flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-gray-100 transition-colors text-gray-600 hover:text-gray-900"
        title="返回总览"
      >
        <Home className="w-4 h-4" />
        <span className="text-xs font-medium">总览</span>
      </button>

      {/* 面包屑项 */}
      {items.map((item, index) => (
        <React.Fragment key={item.id}>
          <ChevronRight className="w-4 h-4 text-gray-400" />
          <button
            onClick={() => onItemClick(item.id, index)}
            className={`px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
              index === items.length - 1
                ? 'bg-gray-100 text-gray-900'
                : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
            }`}
            style={{
              borderLeft: index === items.length - 1 ? `3px solid ${CATEGORY_COLORS[item.category] || '#94A3B8'}` : 'none',
            }}
          >
            {item.text}
          </button>
        </React.Fragment>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: 验证文件创建成功**

Run: `ls -la frontend/src/components/Breadcrumb.tsx`
Expected: 文件存在

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/Breadcrumb.tsx
git commit -m "feat: add breadcrumb navigation component for drill-down"
```

---

## Task 4: 重构 Concepts.tsx 使用放射状布局

**Files:**
- Modify: `frontend/src/pages/Concepts.tsx`

- [ ] **Step 1: 更新 imports 和类型定义**

在文件顶部添加新的 imports：

```typescript
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
import { Search, FileText, X, Maximize2, ArrowLeft, BookOpen, RefreshCw } from 'lucide-react'
import { conceptsApi, graphApi, papersApi } from '../lib/api'
import {
  computeRadialLayout,
  findRoots,
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
```

- [ ] **Step 2: 更新 GraphCanvas 组件状态**

在 `GraphCanvas` 函数内，更新状态定义：

```typescript
function GraphCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [selectedConcept, setSelectedConcept] = useState<Concept | null>(null)
  const [conceptPapers, setConceptPapers] = useState<{ doi: string; title: string }[]>([])
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
  const [viewMode, setViewMode] = useState<'radial' | 'detail'>('radial')
  const [currentConcept, setCurrentConcept] = useState<Concept | null>(null)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)

  // 新增状态：层级筛选
  const [levelRange, setLevelRange] = useState<LevelRange>({ min: 0, max: 5 })

  // 新增状态：钻取路径
  const [drillPath, setDrillPath] = useState<BreadcrumbItem[]>([])
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null)

  const { fitView } = useReactFlow()
  const containerRef = useRef<HTMLDivElement>(null)

  // Store all concepts and graph data
  const [allConcepts, setAllConcepts] = useState<Concept[]>([])
  const [allGraphData, setAllGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null)

  // 新增：布局相关数据的 memo 化
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
```

- [ ] **Step 3: 创建渲染放射状视图的函数**

在 `loadGraph` 函数后添加：

```typescript
  const renderRadialView = useCallback(
    (focusId?: string | null) => {
      if (!layoutData || !allGraphData) return

      const { conceptNodes, parentMap, childrenMap } = layoutData

      // 确定布局范围
      let targetNodes = conceptNodes
      let targetEdges = allGraphData.edges

      if (focusId) {
        // 钻取模式：只显示该节点的子树
        const descendants = getDescendants(focusId, childrenMap)
        const visibleIds = new Set([focusId, ...descendants])
        targetNodes = conceptNodes.filter(n => visibleIds.has(n.id))
        targetEdges = allGraphData.edges.filter(
          e => visibleIds.has(e.source) && visibleIds.has(e.target)
        )
      }

      // 计算布局
      const width = containerRef.current?.clientWidth || 1200
      const height = containerRef.current?.clientHeight || 800
      const positions = computeRadialLayout(targetNodes, targetEdges, {
        centerX: width / 2,
        centerY: height / 2,
        ringSpacing: 60,
      })

      // 根据层级筛选过滤
      const visibleIds = filterByLevel(positions, levelRange.min, levelRange.max)

      // 创建 React Flow 节点
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

      // 创建 React Flow 边
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
    [layoutData, allGraphData, levelRange, fitView]
  )

  // 当层级范围变化时重新渲染
  useEffect(() => {
    if (layoutData && allGraphData) {
      renderRadialView(focusedNodeId)
    }
  }, [levelRange, layoutData, allGraphData, focusedNodeId, renderRadialView])
```

- [ ] **Step 4: 更新 loadGraph 函数**

修改 `loadGraph` 函数：

```typescript
  const loadGraph = async () => {
    try {
      const [conceptsRes, graphRes] = await Promise.all([
        conceptsApi.list(),
        graphApi.data(),
      ])

      const concepts: Concept[] = conceptsRes.data
      const graphData = graphRes.data

      setAllConcepts(concepts)
      setAllGraphData(graphData)
      setLoading(false)
    } catch (err) {
      console.error('Failed to load graph:', err)
      setLoading(false)
    }
  }
```

- [ ] **Step 5: 更新点击和悬停交互**

更新 `onNodeClick` 处理钻取：

```typescript
  const onNodeClick = useCallback(
    async (_event: React.MouseEvent, node: Node) => {
      if (viewMode === 'radial' && node.type === 'concept') {
        // 更新钻取路径
        const concept = allConcepts.find(c => c.id === node.id)
        if (concept) {
          setDrillPath(prev => {
            // 如果点击的是路径中的某个节点，截断到该节点
            const existingIndex = prev.findIndex(item => item.id === node.id)
            if (existingIndex >= 0) {
              return prev.slice(0, existingIndex + 1)
            }
            // 否则追加
            return [...prev, {
              id: concept.id,
              text: concept.text,
              category: concept.category || 'method',
            }]
          })

          // 钻取到该节点
          renderRadialView(node.id)
        }

        // 高亮相关节点
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

        // 显示概念详情
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
```

- [ ] **Step 6: 更新悬停交互和点击事件处理**

更新 `onNodeMouseEnter`、`onNodeMouseLeave` 和 `onPaneClick`：

```typescript
  const onNodeMouseEnter = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (viewMode !== 'radial') return
      setHoveredNode(node.id)

      if (layoutData) {
        const { parentMap, childrenMap } = layoutData
        const path = getNodePath(node.id, parentMap)
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
    setHoveredNode(null)
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

  // 保留现有的双击进入论文详情视图
  const onNodeDoubleClick = useCallback(
    async (_event: React.MouseEvent, node: Node) => {
      if (viewMode === 'radial' && node.type === 'concept' && node.data.paperCount > 0) {
        const concept = allConcepts.find((c) => c.id === node.id)
        if (concept) {
          // 进入论文详情视图
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
```

- [ ] **Step 7: 添加面包屑和筛选器处理函数**

```typescript
  const handleBreadcrumbClick = useCallback(
    (id: string, index: number) => {
      // 截断路径
      setDrillPath(prev => prev.slice(0, index + 1))
      // 渲染该节点的子树
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
```

- [ ] **Step 8: 更新 JSX 渲染**

更新 return 语句中的 JSX，添加面包屑和层级筛选器：

```typescript
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

      {/* Node Labels */}
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

      {/* 面包屑导航 */}
      {drillPath.length > 0 && (
        <div className="absolute top-4 left-4 z-10">
          <Breadcrumb
            items={drillPath}
            onItemClick={handleBreadcrumbClick}
            onHomeClick={handleHomeClick}
          />
        </div>
      )}

      {/* 层级筛选器 */}
      {viewMode === 'radial' && (
        <div className="absolute top-4 right-4 z-10">
          <LevelFilter value={levelRange} onChange={handleLevelChange} />
        </div>
      )}

      {/* Legend */}
      <Legend />

      {/* Concept Detail Panel - 移到左侧 */}
      {viewMode === 'radial' && selectedConcept && (
        <div className="absolute top-20 left-4 w-80 bg-white rounded-2xl shadow-2xl z-20 overflow-hidden max-h-[calc(100vh-200px)]">
          {/* ... 保持现有的详情面板内容 ... */}
        </div>
      )}

      {/* Paper Detail Panel */}
      {viewMode === 'detail' && selectedPaper && (
        <PaperDetailPanel paper={selectedPaper} onClose={() => setSelectedPaper(null)} />
      )}

      {/* Info Panel */}
      {viewMode === 'radial' && drillPath.length === 0 && (
        <div className="absolute bottom-4 left-4 z-10 bg-white/90 backdrop-blur rounded-xl shadow-lg p-3">
          <div className="text-xs text-gray-500 mb-1">知识图谱</div>
          <div className="font-bold text-gray-900">{nodes.length} 个概念</div>
          <div className="text-xs text-gray-500 mt-1">点击节点钻取查看子树</div>
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
```

- [ ] **Step 9: 验证前端编译通过**

Run: `cd frontend && npm run build`
Expected: 编译成功，无错误

- [ ] **Step 10: 提交**

```bash
git add frontend/src/pages/Concepts.tsx
git commit -m "feat: integrate radial layout with level filter and breadcrumb"
```

---

## Task 5: 添加同心环背景和扇区背景

**Files:**
- Modify: `frontend/src/pages/Concepts.tsx`

- [ ] **Step 1: 创建同心环和扇区背景组件**

在 Concepts.tsx 中添加：

```typescript
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

        // 扇区路径
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
```

- [ ] **Step 2: 计算 roots 数据用于扇区背景**

在 `renderRadialView` 函数前添加：

```typescript
  // 计算根概念列表用于扇区背景
  const rootConcepts = useMemo(() => {
    if (!layoutData || !allGraphData) return []
    const roots = findRoots(layoutData.conceptNodes, allGraphData.edges)
    return roots.map(r => ({ id: r.id, category: r.category }))
  }, [layoutData, allGraphData])
```

- [ ] **Step 3: 在 ReactFlow 中添加背景 SVG**

更新 JSX，在 `<ReactFlow>` 内部添加：

```typescript
<ReactFlow ...>
  {/* 背景层：扇区和同心环 */}
  {viewMode === 'radial' && !focusedNodeId && (
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
  {/* ... 其他组件 ... */}
</ReactFlow>
```

- [ ] **Step 4: 验证编译**

Run: `cd frontend && npm run build`
Expected: 编译成功

- [ ] **Step 5: 提交**

```bash
git add frontend/src/pages/Concepts.tsx
git commit -m "feat: add concentric rings and sector backgrounds for radial layout"
```

---

## Task 6: 添加节点 Tooltip

**Files:**
- Modify: `frontend/src/pages/Concepts.tsx`

- [ ] **Step 1: 创建 Tooltip 组件**

在 Concepts.tsx 中添加：

```typescript
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
```

- [ ] **Step 2: 添加 tooltip 状态和位置追踪**

在 `GraphCanvas` 组件中添加状态：

```typescript
  const [tooltipNode, setTooltipNode] = useState<Node | null>(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })
```

- [ ] **Step 3: 更新 onNodeMouseEnter 显示 tooltip**

修改 `onNodeMouseEnter`：

```typescript
  const onNodeMouseEnter = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (viewMode !== 'radial') return
      setHoveredNode(node.id)

      // 显示 tooltip
      const bounds = containerRef.current?.getBoundingClientRect()
      if (bounds) {
        setTooltipPosition({
          x: event.clientX - bounds.left,
          y: event.clientY - bounds.top,
        })
      }
      setTooltipNode(node)

      // 高亮逻辑保持不变...
    },
    [viewMode, layoutData, selectedConcept, setNodes]
  )
```

- [ ] **Step 4: 更新 onNodeMouseLeave 隐藏 tooltip**

修改 `onNodeMouseLeave`：

```typescript
  const onNodeMouseLeave = useCallback(() => {
    setHoveredNode(null)
    setTooltipNode(null) // 隐藏 tooltip

    // 其余逻辑保持不变...
  }, [selectedConcept, setNodes, setEdges])
```

- [ ] **Step 5: 添加鼠标移动追踪更新 tooltip 位置**

添加 `onNodeMouseMove` 处理：

```typescript
  const onNodeMouseMove = useCallback((event: React.MouseEvent) => {
    const bounds = containerRef.current?.getBoundingClientRect()
    if (bounds) {
      setTooltipPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      })
    }
  }, [])
```

- [ ] **Step 6: 在 JSX 中渲染 Tooltip**

在 return 的 JSX 中添加：

```typescript
      {/* Node Tooltip */}
      <NodeTooltip node={tooltipNode} position={tooltipPosition} />

      {/* Legend */}
      <Legend />
```

- [ ] **Step 7: 在 ReactFlow 中添加 onNodeMouseMove**

更新 `<ReactFlow>` 属性：

```typescript
<ReactFlow
  ...
  onNodeMouseMove={onNodeMouseMove}
>
```

- [ ] **Step 8: 验证编译**

Run: `cd frontend && npm run build`
Expected: 编译成功

- [ ] **Step 9: 提交**

```bash
git add frontend/src/pages/Concepts.tsx
git commit -m "feat: add node tooltip showing name, level, and paper count"
```

---

## Task 7: 删除旧的力导向布局代码

**Files:**
- Modify: `frontend/src/pages/Concepts.tsx`

- [ ] **Step 1: 删除 applyForceLayout 和相关类型**

从 Concepts.tsx 中删除：

```typescript
// 删除这些代码
interface D3Node { ... }
interface D3Link { ... }
function applyForceLayout(...) { ... }
function calculateDegrees(...) { ... }
```

- [ ] **Step 2: 删除 d3-force import**

删除：
```typescript
import * as d3 from 'd3-force'
```

- [ ] **Step 3: 验证编译**

Run: `cd frontend && npm run build`
Expected: 编译成功

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/Concepts.tsx
git commit -m "refactor: remove old force-directed layout code"
```

---

## Task 8: 最终验证

- [ ] **Step 1: 完整构建**

Run: `cd frontend && npm run build`
Expected: 构建成功

- [ ] **Step 2: 启动开发服务器测试**

Run: `cd frontend && npm run dev`
Expected: 服务器启动成功，访问 http://localhost:5173 概念页面正常显示

- [ ] **Step 3: 手动测试功能**

1. 打开概念页面
2. 验证放射状布局显示
3. 测试层级筛选器切换
4. 测试点击节点钻取
5. 测试面包屑导航返回
6. 测试悬停高亮
7. 测试概念详情面板

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "feat: complete radial layout implementation with all interactions"
```

---

## 验收清单

- [ ] 放射状布局正确显示 6 层概念层级
- [ ] 同心环背景可见
- [ ] 层级筛选器可正常过滤显示范围
- [ ] 点击节点可钻取进入子树视图
- [ ] 面包屑导航显示当前路径，点击可返回
- [ ] 悬停高亮正确显示路径
- [ ] 概念详情面板正常工作
- [ ] 缩放、平移、小地图正常
- [ ] 性能：100+ 节点时无明显卡顿